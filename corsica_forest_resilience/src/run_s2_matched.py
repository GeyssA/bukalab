"""
Extraction Sentinel-2 L2A (NDVI, NDMI) pour les cellules matchées.

Stratégie (efficace) :
  - mosaïques estivales médianes Corse à 100 m (Planetary Computer + stackstac)
  - échantillonnage aux centroïdes des cellules matchées
  - reprise auto via CSV

Puis métriques de trajectoire + tests appariés PNR vs contrôle.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import planetary_computer
import pystac_client
import stackstac
import xarray as xr

from . import ROOT, load_config, setup_logger, write_metadata
from .matching import compare_outcomes, mahalanobis_match
from .timeseries import compute_trajectory_metrics

log = setup_logger()

BBOX = [8.53, 41.33, 9.57, 43.03]  # Corse WGS84
YEARS = list(range(2017, 2026))
SUMMER = (6, 8)


def _catalog():
    return pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )


def matched_centroids() -> gpd.GeoDataFrame:
    cfg = load_config()
    pairs = pd.read_csv(ROOT / cfg["paths"]["tables"] / "matched_pairs.csv")
    grid = gpd.read_file(ROOT / cfg["paths"]["processed"] / "forest_grid_1km.gpkg")
    cells = sorted(set(pairs["treat_cell"]).union(set(pairs["ctrl_cell"])))
    g = grid.loc[grid["cell_id"].isin(cells)].copy()
    cents = g.geometry.centroid
    g = g.set_geometry(cents)
    g4326 = g.to_crs(4326)
    out = g.copy()
    out["lon"] = g4326.geometry.x.values
    out["lat"] = g4326.geometry.y.values
    # garder aussi en 2154 pour stackstac
    out["x2154"] = cents.x.values
    out["y2154"] = cents.y.values
    log.info("Cellules matchées uniques: %d", len(out))
    return out


def seasonal_median_indices(year: int, res: int = 200, max_items: int = 50) -> xr.Dataset:
    """Médiane estivale NDVI/NDMI sur la Corse (avec retries lecture COG)."""
    import rasterio

    catalog = _catalog()
    start = f"{year}-{SUMMER[0]:02d}-01"
    end = f"{year}-{SUMMER[1]:02d}-28"
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=BBOX,
        datetime=f"{start}/{end}",
    )
    items = [
        it
        for it in search.items()
        if (it.properties.get("eo:cloud_cover") or 100) < 50
    ]
    items = sorted(items, key=lambda it: it.properties.get("eo:cloud_cover", 100))[:max_items]
    log.info("%d : %d scènes S2 retenues", year, len(items))
    if len(items) == 0:
        raise RuntimeError(f"Aucune scène S2 pour {year}")

    bounds = (1150000, 6050000, 1245000, 6205000)
    gdal_env = stackstac.DEFAULT_GDAL_ENV.updated(
        always=dict(
            GDAL_HTTP_MAX_RETRY="8",
            GDAL_HTTP_RETRY_DELAY="5",
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
        )
    )
    last_err = None
    for attempt in range(1, 4):
        try:
            cube = stackstac.stack(
                items,
                assets=["B04", "B08", "B11", "SCL"],
                epsg=2154,
                resolution=res,
                bounds=bounds,
                chunksize=1024,
                rescale=False,
                dtype="float64",
                fill_value=np.nan,
                errors_as_nodata=(Exception,),
                gdal_env=gdal_env,
            )
            scl = cube.sel(band="SCL")
            clear = (scl == 4) | (scl == 5) | (scl == 7)
            b04 = cube.sel(band="B04").where(clear)
            b08 = cube.sel(band="B08").where(clear)
            b11 = cube.sel(band="B11").where(clear)
            ndvi = (b08 - b04) / (b08 + b04 + 1e-6)
            ndmi = (b08 - b11) / (b08 + b11 + 1e-6)
            ndvi_m = ndvi.median(dim="time", skipna=True).compute()
            ndmi_m = ndmi.median(dim="time", skipna=True).compute()
            return xr.Dataset({"NDVI": ndvi_m, "NDMI": ndmi_m})
        except Exception as e:
            last_err = e
            log.warning("Tentative %d échouée (%s) — retry", attempt, e)
            # réduire le nombre de scènes
            items = items[: max(20, len(items) // 2)]
            time.sleep(10 * attempt)
    raise RuntimeError(f"Échec mosaïque {year}: {last_err}")


def sample_points(ds: xr.Dataset, pts: gpd.GeoDataFrame) -> pd.DataFrame:
    """Nearest-neighbour sampling sur grille 2154."""
    xs = xr.DataArray(pts["x2154"].values, dims="point")
    ys = xr.DataArray(pts["y2154"].values, dims="point")
    # stackstac utilise souvent x,y
    if "x" in ds.coords and "y" in ds.coords:
        sampled = ds.sel(x=xs, y=ys, method="nearest")
    else:
        # parfois longitude/latitude
        raise RuntimeError(f"Coords inattendues: {list(ds.coords)}")
    return pd.DataFrame(
        {
            "cell_id": pts["cell_id"].values,
            "NDVI": sampled["NDVI"].values,
            "NDMI": sampled["NDMI"].values,
        }
    )


def extract_all(resume: bool = True) -> Path:
    cfg = load_config()
    out_csv = ROOT / cfg["paths"]["processed"] / "s2_summer_matched_cells.csv"
    pts = matched_centroids()
    rows = []
    done_years = set()
    if resume and out_csv.exists():
        prev = pd.read_csv(out_csv)
        rows = prev.to_dict("records")
        done_years = set(prev["year"].unique())
        log.info("Reprise: années déjà faites %s", sorted(done_years))

    for year in YEARS:
        if year in done_years:
            continue
        t0 = time.time()
        try:
            ds = seasonal_median_indices(year, res=200)
            samp = sample_points(ds, pts)
            samp["year"] = year
            samp["season"] = "summer"
            rows.extend(samp.to_dict("records"))
            pd.DataFrame(rows).to_csv(out_csv, index=False)
            log.info("OK %d (%.0fs) → %s", year, time.time() - t0, out_csv.name)
        except Exception as e:
            log.exception("Échec année %d: %s", year, e)
            # sauvegarde partielle
            if rows:
                pd.DataFrame(rows).to_csv(out_csv, index=False)
            raise
    write_metadata(
        out_csv.with_suffix(".meta.json"),
        {
            "collection": "sentinel-2-l2a",
            "provider": "Microsoft Planetary Computer",
            "season": "summer JJA",
            "resolution_m": 100,
            "scl_clear": [4, 5, 7],
            "years": YEARS,
            "n_cells": len(pts),
        },
    )
    return out_csv


def analyze(ts_csv: Path) -> dict:
    cfg = load_config()
    ts = pd.read_csv(ts_csv)
    # nettoyage
    ts = ts.dropna(subset=["NDVI", "NDMI"])
    ts = ts.loc[(ts["NDVI"] > -0.2) & (ts["NDVI"] < 1.0)]
    metrics = compute_trajectory_metrics(ts)
    metrics_path = ROOT / cfg["paths"]["processed"] / "trajectory_metrics.csv"
    metrics.to_csv(metrics_path, index=False)

    pairs = pd.read_csv(ROOT / cfg["paths"]["tables"] / "matched_pairs.csv")
    grid = gpd.read_file(ROOT / cfg["paths"]["processed"] / "forest_grid_1km.gpkg")
    results = compare_outcomes(metrics, pairs, grid)
    results_path = ROOT / cfg["paths"]["tables"] / "matched_outcome_tests.csv"

    # résumé texte
    summary = {
        "n_ts_rows": len(ts),
        "n_cells_with_metrics": metrics["cell_id"].nunique(),
        "n_pairs_tests": int(results["n_pairs"].max()) if len(results) else 0,
        "results_table": str(results_path),
    }
    if len(results):
        summary["key_rows"] = results.to_dict("records")
    (ROOT / cfg["paths"]["tables"] / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def make_result_figures(ts_csv: Path) -> list[Path]:
    """Figures 3, 4, 10 style publication pour les résultats S2."""
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    from .figures import _save, _panel_label, C_PNR, C_OUT, C_COAST

    cfg = load_config()
    ts = pd.read_csv(ts_csv)
    pairs = pd.read_csv(ROOT / cfg["paths"]["tables"] / "matched_pairs.csv")
    treat = set(pairs["treat_cell"])
    ctrl = set(pairs["ctrl_cell"])
    ts = ts.copy()
    ts["group"] = np.where(ts["cell_id"].isin(treat), "PNR", np.where(ts["cell_id"].isin(ctrl), "hors PNR", "other"))
    ts = ts.loc[ts["group"] != "other"]

    paths = []
    # Fig séries
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for ax, var in zip(axes, ["NDVI", "NDMI"]):
        for group, color in [("PNR", C_PNR), ("hors PNR", C_OUT)]:
            sub = ts.loc[ts["group"] == group]
            g = sub.groupby("year")[var].agg(["mean", "sem"])
            ax.plot(g.index, g["mean"], color=color, lw=2, marker="o", ms=4, label=group)
            ax.fill_between(
                g.index,
                g["mean"] - 1.96 * g["sem"],
                g["mean"] + 1.96 * g["sem"],
                color=color,
                alpha=0.18,
            )
        ax.set_xlabel("Année")
        ax.set_ylabel(f"{var} estival (médiane saisonnière)")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(fontsize=8)
    _panel_label(axes[0], "a")
    _panel_label(axes[1], "b")
    fig.suptitle(
        "Trajectoires estivales Sentinel-2 — cellules matchées",
        color=C_COAST,
        fontsize=12,
    )
    fig.text(
        0.5,
        0.01,
        "Moyenne ± IC95% (SEM×1,96) sur paires matchées · S2 L2A Planetary Computer · médiane JJA 100 m",
        ha="center",
        fontsize=7,
        color="0.35",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    paths.append(_save(fig, "fig03_timeseries_matched"))

    # Fig anomalies / tendances
    metrics = pd.read_csv(ROOT / cfg["paths"]["processed"] / "trajectory_metrics.csv")
    m = metrics.copy()
    m["group"] = np.where(m["cell_id"].isin(treat), "PNR", np.where(m["cell_id"].isin(ctrl), "hors PNR", "other"))
    m = m.loc[m["group"] != "other"]

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for ax, var in zip(axes, ["NDVI", "NDMI"]):
        sub = m.loc[m["variable"] == var]
        data = [
            sub.loc[sub["group"] == "hors PNR", "trend_slope"].dropna(),
            sub.loc[sub["group"] == "PNR", "trend_slope"].dropna(),
        ]
        parts = ax.violinplot(data, positions=[0, 1], showmedians=True, showextrema=False)
        for i, pc in enumerate(parts["bodies"]):
            pc.set_facecolor([C_OUT, C_PNR][i])
            pc.set_alpha(0.85)
        parts["cmedians"].set_color(C_COAST)
        ax.axhline(0, color="0.5", lw=0.7, ls="--")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Hors PNR", "PNR"])
        ax.set_ylabel(f"Pente {var} (an⁻¹)")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    _panel_label(axes[0], "a")
    _panel_label(axes[1], "b")
    fig.suptitle("Distribution des tendances estivales (cellules matchées)", color=C_COAST, fontsize=12)
    fig.tight_layout()
    paths.append(_save(fig, "fig05_trends_distribution"))

    # Fig synthèse tests
    res_path = ROOT / cfg["paths"]["tables"] / "matched_outcome_tests.csv"
    if res_path.exists():
        res = pd.read_csv(res_path)
        fig, ax = plt.subplots(figsize=(9.5, 4.5))
        # focus outcomes clés
        focus = res.loc[res["outcome"].isin(["trend_slope", "mean_level", "cv", "anomaly_mean"])].copy()
        if len(focus):
            focus["label"] = focus["variable"] + " · " + focus["outcome"].str.replace("_", " ")
            focus = focus.reset_index(drop=True)
            y = np.arange(len(focus))
            ax.axvline(0, color=C_COAST, lw=0.8)
            ax.errorbar(
                focus["mean_diff_pnr_minus_ctrl"],
                y,
                xerr=[
                    focus["mean_diff_pnr_minus_ctrl"] - focus["ci95_low"],
                    focus["ci95_high"] - focus["mean_diff_pnr_minus_ctrl"],
                ],
                fmt="o",
                color=C_PNR,
                ecolor="0.55",
                elinewidth=1,
                capsize=3,
                ms=6,
            )
            ax.set_yticks(y)
            ax.set_yticklabels(focus["label"], fontsize=8)
            ax.set_xlabel("Différence appariée (PNR − contrôle) · IC95% bootstrap")
            ax.set_title("Résultats après matching — ne pas interpréter comme effet causal du PNR", color=C_COAST)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            fig.text(
                0.5,
                0.01,
                "Estimation sur paires matchées · IC95% bootstrap · design observationnel",
                ha="center",
                fontsize=7,
                color="0.35",
            )
            fig.tight_layout(rect=[0, 0.05, 1, 1])
            paths.append(_save(fig, "fig10_matched_effects"))
    return paths


if __name__ == "__main__":
    csv = extract_all(resume=True)
    summary = analyze(csv)
    print(json.dumps(summary, indent=2, ensure_ascii=False)[:2000])
    make_result_figures(csv)
    print("DONE")
