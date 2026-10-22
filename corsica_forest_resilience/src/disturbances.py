"""Perturbations : incendies + chutes NDVI. Validation croisée si données EFFIS disponibles."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd

from . import ROOT, load_config, setup_logger, write_metadata

log = setup_logger()


def load_effis_if_any() -> gpd.GeoDataFrame | None:
    cfg = load_config()
    fire_dir = ROOT / cfg["paths"]["raw"] / "fire"
    for p in list(fire_dir.glob("*.gpkg")) + list(fire_dir.glob("*.geojson")) + list(fire_dir.glob("*.shp")):
        g = gpd.read_file(p)
        log.info("Incendies chargés: %s (%d)", p.name, len(g))
        return g.to_crs(cfg["project"]["crs_analysis"])
    log.warning(
        "Aucun périmètre EFFIS local. Déposer un GeoJSON/SHP dans data/raw/fire/ "
        "(demande : https://forest-fire.emergency.copernicus.eu/apps/data.request.form/)"
    )
    return None


def flag_burned_cells(grid: gpd.GeoDataFrame, fires: gpd.GeoDataFrame | None) -> gpd.GeoDataFrame:
    out = grid.copy()
    if fires is None or fires.empty:
        out["burned_ever_2017_2025"] = 0
        out["burn_source"] = "none"
        return out
    burned = gpd.sjoin(out, fires[["geometry"]], how="left", predicate="intersects")
    flag = burned.groupby(burned.index)["index_right"].apply(lambda s: int(s.notna().any()))
    out["burned_ever_2017_2025"] = flag.reindex(out.index).fillna(0).astype(int)
    out["burn_source"] = "effis_or_local"
    return out


def detect_ndvi_disturbances(ts: pd.DataFrame, z_thresh: float = -2.0) -> pd.DataFrame:
    """
    Perturbation proxy : été où NDVI < moyenne_cell - 2*SD (sur la série cellulaire).
    Ce n'est PAS un inventaire d'incendies — proxy spectral à valider.
    """
    summer = ts.loc[ts["season"] == "summer"].copy()
    rows = []
    for cell, g in summer.groupby("cell_id"):
        g = g.sort_values("year")
        y = g["NDVI"].astype(float).values
        if np.sum(np.isfinite(y)) < 5:
            continue
        mu, sd = np.nanmean(y), np.nanstd(y) + 1e-6
        z = (y - mu) / sd
        for year, zi, yi in zip(g["year"].values, z, y):
            if zi <= z_thresh:
                rows.append(
                    {
                        "cell_id": cell,
                        "year": int(year),
                        "NDVI": float(yi),
                        "z_score": float(zi),
                        "type": "spectral_drop",
                    }
                )
    return pd.DataFrame(rows)


def recovery_curves(ts: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Alignement événement = année 0."""
    summer = ts.loc[ts["season"] == "summer"].set_index(["cell_id", "year"])["NDVI"]
    rows = []
    for _, ev in events.iterrows():
        cell, y0 = ev["cell_id"], int(ev["year"])
        for dy in range(-2, 6):
            y = y0 + dy
            if (cell, y) in summer.index:
                rows.append(
                    {
                        "cell_id": cell,
                        "event_year": y0,
                        "rel_year": dy,
                        "NDVI": float(summer.loc[(cell, y)]),
                        "in_pnr": ev.get("in_pnr", np.nan),
                    }
                )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    cfg = load_config()
    fires = load_effis_if_any()
    grid_path = ROOT / cfg["paths"]["processed"] / "forest_grid_1km.gpkg"
    if grid_path.exists():
        grid = gpd.read_file(grid_path)
        grid = flag_burned_cells(grid, fires)
        grid.to_file(grid_path, driver="GPKG", layer="cells")
    write_metadata(
        ROOT / cfg["paths"]["processed"] / "disturbances.meta.json",
        {
            "effis_present": fires is not None,
            "spectral_proxy": "NDVI summer z<=-2",
            "limitation": "Spectral drops ≠ confirmed fires without EFFIS overlay",
        },
    )
