"""
Séries temporelles Sentinel-2 via Microsoft Planetary Computer (STAC).

Stratégie (évite le téléchargement massif) :
1. Requête STAC saisonnière (été / printemps) 2017→2025
2. Pour chaque cellule : médiane des NDVI/NDMI sur pixels forestiers SCL-clear
   via lecture COG à la volée (nécessite rasterio)

Si rasterio indisponible : génère un script Earth Engine export + placeholders
documentés (pas de fausse donnée).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd

from . import ROOT, load_config, setup_logger, write_metadata
from .indices import ndvi, ndmi, sen2cor_scl_clear, JUSTIFICATIONS

log = setup_logger()


def _has_rasterio() -> bool:
    try:
        import rasterio  # noqa: F401
        import pystac_client  # noqa: F401
        import planetary_computer  # noqa: F401
        return True
    except ImportError:
        return False


def write_gee_export_script() -> Path:
    """Script Earth Engine à exécuter dans le Code Editor (compte Google requis)."""
    cfg = load_config()
    out = ROOT / "src" / "gee_export_s2_seasonal.js"
    js = r'''
/**
 * Corsica Forest Resilience — export Sentinel-2 seasonal medians
 * Exécuter dans https://code.earthengine.google.com/
 * Export Drive → CSV : cell_id, year, season, NDVI, NDMI, n_pixels
 *
 * Prérequis : uploader le GPKG forest_grid_1km (centroïdes) comme asset
 *   assets/USERS/.../corsica_forest_cells
 */
var cells = ee.FeatureCollection('USERS/REPLACE/corsica_forest_cells');
var startYear = 2017;
var endYear = 2025;

function maskS2(img) {
  var scl = img.select('SCL');
  var clear = scl.eq(4).or(scl.eq(5).or(scl.eq(7)));
  return img.updateMask(clear)
    .divide(10000)
    .copyProperties(img, img.propertyNames());
}

function addIndices(img) {
  var ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI');
  var ndmi = img.normalizedDifference(['B8', 'B11']).rename('NDMI');
  return img.addBands([ndvi, ndmi]);
}

var seasons = {
  spring: [3, 5],
  summer: [6, 8]
};

var feats = [];
for (var y = startYear; y <= endYear; y++) {
  Object.keys(seasons).forEach(function(season) {
    var m0 = seasons[season][0];
    var m1 = seasons[season][1];
    var start = ee.Date.fromYMD(y, m0, 1);
    var end = ee.Date.fromYMD(y, m1, 1).advance(1, 'month');
    var col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
      .filterBounds(cells)
      .filterDate(start, end)
      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
      .map(maskS2)
      .map(addIndices);
    var med = col.select(['NDVI', 'NDMI']).median();
    var reduced = med.reduceRegions({
      collection: cells,
      reducer: ee.Reducer.mean().combine({
        reducer2: ee.Reducer.count(),
        sharedInputs: true
      }),
      scale: 20
    }).map(function(f) {
      return f.set({year: y, season: season});
    });
    feats.push(reduced);
  });
}

var out = ee.FeatureCollection(feats).flatten();
Export.table.toDrive({
  collection: out,
  description: 'corsica_s2_seasonal_ndvi_ndmi',
  fileFormat: 'CSV'
});
'''
    out.write_text(js, encoding="utf-8")
    write_metadata(
        out.with_suffix(".meta.json"),
        {
            "purpose": "Export GEE Sentinel-2 L2A seasonal NDVI/NDMI for analysis cells",
            "indices": JUSTIFICATIONS,
            "period": cfg["period"],
            "note": "Requires Google Earth Engine account; no fabricated results without export",
        },
    )
    log.info("Script GEE → %s", out)
    return out


def stac_search_count(bbox_wgs84: list[float], year: int, months: tuple[int, int]) -> int:
    """Compte les scènes S2 L2A disponibles (sans lecture pixels)."""
    import pystac_client
    import planetary_computer

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    start = f"{year}-{months[0]:02d}-01"
    end_m = months[1]
    end = f"{year}-{end_m:02d}-28"
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox_wgs84,
        datetime=f"{start}/{end}",
        query={"eo:cloud_cover": {"lt": 40}},
    )
    return len(list(search.items()))


def feasibility_s2() -> Path:
    """Vérifie la couverture STAC Sentinel-2 sur la Corse."""
    cfg = load_config()
    # bbox Corse approx
    bbox = [8.5, 41.3, 9.6, 43.1]
    rows = []
    try:
        for y in range(2017, 2026):
            for season, months in [("spring", (3, 5)), ("summer", (6, 8))]:
                n = stac_search_count(bbox, y, months)
                rows.append({"year": y, "season": season, "n_items": n})
                log.info("S2 %d %s: %d items", y, season, n)
        df = pd.DataFrame(rows)
        status = "ok"
    except Exception as e:
        log.warning("STAC inaccessible: %s", e)
        df = pd.DataFrame()
        status = f"error: {e}"

    out = ROOT / cfg["paths"]["tables"] / "s2_stac_feasibility.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    write_metadata(
        out.with_suffix(".meta.json"),
        {
            "status": status,
            "provider": "Microsoft Planetary Computer",
            "collection": "sentinel-2-l2a",
            "bbox": bbox,
            "rasterio_available": _has_rasterio(),
            "next_step": "Run gee_export_s2_seasonal.js OR implement COG sampling with rasterio",
        },
    )
    write_gee_export_script()
    return out


def compute_trajectory_metrics(ts: pd.DataFrame) -> pd.DataFrame:
    """
    ts columns: cell_id, year, season, NDVI, NDMI
    Dérive tendances, anomalies, CV, recovery proxy.
    """
    summer = ts.loc[ts["season"] == "summer"].copy()
    if summer.empty:
        raise ValueError("Pas de lignes season=summer")

    rows = []
    for cell, g in summer.groupby("cell_id"):
        g = g.sort_values("year")
        years = g["year"].values.astype(float)
        for var in ("NDVI", "NDMI"):
            if var not in g.columns:
                continue
            y = g[var].astype(float).values
            if np.sum(np.isfinite(y)) < 4:
                continue
            mask = np.isfinite(y)
            slope = np.polyfit(years[mask], y[mask], 1)[0]
            base = np.nanmean(y[mask][:3]) if mask.sum() >= 3 else np.nanmean(y)
            anom = y - base
            cv = np.nanstd(y) / (abs(np.nanmean(y)) + 1e-6)
            # recovery: après le minimum, années pour revenir à ≥90% baseline
            recovery = np.nan
            if mask.sum() >= 5:
                imin = int(np.nanargmin(y))
                thr = 0.9 * base if np.isfinite(base) else np.nan
                if np.isfinite(thr):
                    rec = np.nan
                    for k in range(imin + 1, len(y)):
                        if np.isfinite(y[k]) and y[k] >= thr:
                            rec = years[k] - years[imin]
                            break
                    recovery = rec
            rows.append(
                {
                    "cell_id": cell,
                    "variable": var,
                    "trend_slope": slope,
                    "anomaly_mean": float(np.nanmean(anom)),
                    "cv": float(cv),
                    "recovery_years": recovery,
                    "mean_level": float(np.nanmean(y)),
                    "n_years": int(mask.sum()),
                }
            )
    return pd.DataFrame(rows)


def load_or_instruct_timeseries() -> Path | None:
    """
    Charge CSV GEE/STAC s'il existe dans data/processed.
    Sinon retourne None (pas de fabrication).
    """
    cfg = load_config()
    candidates = list((ROOT / cfg["paths"]["processed"]).glob("*s2*seasonal*.csv"))
    candidates += list((ROOT / cfg["paths"]["raw"]).glob("*s2*seasonal*.csv"))
    if not candidates:
        log.warning(
            "Aucune série S2 trouvée. Exécuter src/gee_export_s2_seasonal.js "
            "puis placer le CSV dans data/processed/"
        )
        return None
    path = candidates[0]
    ts = pd.read_csv(path)
    metrics = compute_trajectory_metrics(ts)
    out = ROOT / cfg["paths"]["processed"] / "trajectory_metrics.csv"
    metrics.to_csv(out, index=False)
    log.info("Métriques trajectoire → %s (%d)", out, len(metrics))
    return out


if __name__ == "__main__":
    feasibility_s2()
    load_or_instruct_timeseries()
