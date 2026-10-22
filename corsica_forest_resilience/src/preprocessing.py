"""
Prétraitement spatial : grille forestière, covariables topo/climat, PNR/hors-PNR.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
from shapely.ops import unary_union

from . import ROOT, load_config, setup_logger, write_metadata
from .download import extract_pnr_corse, load_bd_foret, filter_forest_polygons, download_region_outline

log = setup_logger()


def build_forest_grid(forest: gpd.GeoDataFrame, grid_size_m: int | None = None) -> gpd.GeoDataFrame:
    cfg = load_config()
    gs = grid_size_m or cfg["analysis_unit"]["grid_size_m"]
    min_frac = cfg["analysis_unit"]["min_forest_fraction"]

    xmin, ymin, xmax, ymax = forest.total_bounds
    cols = np.arange(xmin, xmax + gs, gs)
    rows = np.arange(ymin, ymax + gs, gs)
    cells = []
    for i, x0 in enumerate(cols[:-1]):
        for j, y0 in enumerate(rows[:-1]):
            cells.append({"i": i, "j": j, "geometry": box(x0, y0, x0 + gs, y0 + gs)})
    grid = gpd.GeoDataFrame(cells, crs=forest.crs)
    log.info("Grille brute: %d cellules (%d m)", len(grid), gs)

    # Fraction forestière
    forest_u = forest[["geometry"]].copy()
    forest_u["fid"] = 1
    # sjoin + area ratio
    inter = gpd.overlay(grid, forest_u, how="intersection", keep_geom_type=False)
    if inter.empty:
        raise RuntimeError("Aucune intersection forêt × grille")
    inter["area_f"] = inter.geometry.area
    area_by = inter.groupby(inter.index // 1)  # fallback
    # Better: carry cell id
    grid = grid.reset_index(drop=True)
    grid["cell_id"] = [f"C{i:05d}" for i in range(len(grid))]
    inter = gpd.overlay(
        grid[["cell_id", "geometry"]],
        forest.assign(_f=1)[["_f", "geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    inter["area_f"] = inter.geometry.area
    forest_area = inter.groupby("cell_id", as_index=False)["area_f"].sum()
    grid = grid.merge(forest_area, on="cell_id", how="left")
    grid["area_f"] = grid["area_f"].fillna(0)
    grid["forest_fraction"] = grid["area_f"] / (gs * gs)
    grid = grid.loc[grid["forest_fraction"] >= min_frac].copy()
    log.info("Cellules forestières (≥%.0f%%): %d", 100 * min_frac, len(grid))

    # type forestier dominant (mode des polygones intersectés)
    if "forest_type_group" in forest.columns:
        typed = gpd.overlay(
            grid[["cell_id", "geometry"]],
            forest[["forest_type_group", "geometry"]],
            how="intersection",
            keep_geom_type=False,
        )
        typed["a"] = typed.geometry.area
        dom = (
            typed.groupby(["cell_id", "forest_type_group"])["a"]
            .sum()
            .reset_index()
            .sort_values("a", ascending=False)
            .drop_duplicates("cell_id")
        )
        grid = grid.merge(dom[["cell_id", "forest_type_group"]], on="cell_id", how="left")
    else:
        grid["forest_type_group"] = "unknown"

    grid["centroid"] = grid.geometry.centroid
    return grid


def assign_pnr(grid: gpd.GeoDataFrame, pnr: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    pnr_u = unary_union(pnr.geometry)
    cents = grid.copy()
    cents = cents.set_geometry("centroid")
    grid = grid.copy()
    grid["in_pnr"] = cents.within(pnr_u).astype(int)
    log.info("PNR=%d | hors-PNR=%d", grid["in_pnr"].sum(), (1 - grid["in_pnr"]).sum())
    return grid


def add_topography_opentopodata(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Altitude via Open-Meteo elevation API (batch) — proxy DEM sans rasterio.
    Pente/exposition : approximation par différences d'altitude voisines sur grille.
    Limite : résolution ~1 km (celle de la grille), pas du MNT 30 m.
    """
    import requests
    import time

    cfg = load_config()
    # centroïdes en WGS84 depuis géométries projetées (évite warning geographic CRS)
    cents = grid.geometry.centroid
    g4326 = gpd.GeoDataFrame(geometry=cents, crs=grid.crs).to_crs(4326)
    lats = g4326.geometry.y.values
    lons = g4326.geometry.x.values
    elev = np.full(len(grid), np.nan)
    batch = 50  # plus petit = moins d'erreurs API
    for i in range(0, len(grid), batch):
        sl = slice(i, i + batch)
        params = {
            "latitude": ",".join(f"{x:.5f}" for x in lats[sl]),
            "longitude": ",".join(f"{x:.5f}" for x in lons[sl]),
        }
        for attempt in range(5):
            try:
                r = requests.get(
                    "https://api.open-meteo.com/v1/elevation",
                    params=params,
                    timeout=60,
                )
                data = r.json()
                if "elevation" not in data:
                    raise KeyError(str(data)[:200])
                elev[sl] = data["elevation"]
                break
            except Exception as e:
                time.sleep(3 * (attempt + 1))
                if attempt == 4:
                    log.warning("Elevation batch %d failed: %s", i, e)
        time.sleep(0.5)
        if i % 500 == 0:
            log.info("Elevation %d/%d", i, len(grid))

    out = grid.copy()
    out["elevation_m"] = elev
    # impute NaN elevation by nearest valid neighbour on grid indices
    if np.isnan(elev).any():
        valid = out.dropna(subset=["elevation_m"])
        if len(valid):
            from scipy.spatial import cKDTree

            tree = cKDTree(
                np.column_stack([valid.geometry.centroid.x, valid.geometry.centroid.y])
            )
            miss = out["elevation_m"].isna()
            xy = np.column_stack(
                [out.loc[miss].geometry.centroid.x, out.loc[miss].geometry.centroid.y]
            )
            _, jj = tree.query(xy, k=1)
            out.loc[miss, "elevation_m"] = valid.iloc[jj]["elevation_m"].values

    pivot = out.set_index(["i", "j"])["elevation_m"]
    slopes = []
    aspects = []
    gs = cfg["analysis_unit"]["grid_size_m"]
    for _, row in out.iterrows():
        e0 = row["elevation_m"]
        e_e = pivot.get((row["i"] + 1, row["j"]), e0)
        e_n = pivot.get((row["i"], row["j"] + 1), e0)
        if pd.isna(e0) or pd.isna(e_e) or pd.isna(e_n):
            slopes.append(np.nan)
            aspects.append(np.nan)
            continue
        dzdx = (e_e - e0) / gs
        dzdy = (e_n - e0) / gs
        slope = np.degrees(np.arctan(np.sqrt(dzdx**2 + dzdy**2)))
        aspect = (np.degrees(np.arctan2(dzdy, -dzdx)) + 360) % 360
        slopes.append(slope)
        aspects.append(aspect)
    out["slope_deg"] = slopes
    out["aspect_deg"] = aspects
    out["aspect_sin"] = np.sin(np.radians(out["aspect_deg"]))
    out["aspect_cos"] = np.cos(np.radians(out["aspect_deg"]))
    return out


def add_climate_and_elevation_grid(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Une seule grille Open-Meteo Archive (~0.2°) :
    - summer_temp_mean, annual_precip
    - elevation (champ renvoyé par l'API archive)
    Puis nearest neighbour vers les cellules 1 km.
    Pente/aspect approximées sur la grille fine via gradients NN.
    """
    import requests
    import time
    from scipy.spatial import cKDTree

    cfg = load_config()
    cache = ROOT / cfg["paths"]["processed"] / "climate_elev_grid_corse.csv"
    g4326 = grid.to_crs(4326)
    minx, miny, maxx, maxy = g4326.total_bounds
    step = 0.2
    lats = np.arange(miny, maxy + step, step)
    lons = np.arange(minx, maxx + step, step)
    pts = [(round(float(lat), 4), round(float(lon), 4)) for lat in lats for lon in lons]

    if cache.exists():
        clim = pd.read_csv(cache)
        log.info("Cache climat/alti: %s (%d pts)", cache, len(clim))
        done = set(zip(clim["lat"].round(4), clim["lon"].round(4)))
    else:
        clim = pd.DataFrame(columns=["lat", "lon", "summer_temp_mean", "annual_precip", "elevation_m"])
        done = set()

    restants = [p for p in pts if p not in done]
    log.info("Climat/alti: %d points (restants %d)", len(pts), len(restants))
    records = clim.to_dict("records") if len(clim) else []

    for i, (lat, lon) in enumerate(restants):
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": "2017-01-01",
            "end_date": "2025-12-31",
            "daily": "temperature_2m_mean,precipitation_sum",
            "timezone": "Europe/Paris",
        }
        ok = False
        for attempt in range(6):
            try:
                r = requests.get(
                    "https://archive-api.open-meteo.com/v1/archive",
                    params=params,
                    timeout=90,
                )
                d = r.json()
                if "daily" not in d:
                    msg = str(d)
                    if "Hourly" in msg or "limit" in msg.lower():
                        time.sleep(3700)
                        continue
                    raise ValueError(msg)
                df = pd.DataFrame(d["daily"])
                df["time"] = pd.to_datetime(df["time"])
                summer = df.loc[df["time"].dt.month.isin([6, 7, 8]), "temperature_2m_mean"]
                annual_p = df["precipitation_sum"].sum() / max(1, df["time"].dt.year.nunique())
                records.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "summer_temp_mean": float(summer.mean()),
                        "annual_precip": float(annual_p),
                        "elevation_m": float(d.get("elevation", np.nan)),
                    }
                )
                ok = True
                break
            except Exception as e:
                wait = 70 if "limit" in str(e).lower() else 8 * (attempt + 1)
                log.warning("retry %s: %s (sleep %ss)", (lat, lon), e, wait)
                time.sleep(wait)
        if not ok:
            log.warning("FAIL point %s,%s", lat, lon)
        if (i + 1) % 5 == 0 or i == len(restants) - 1:
            pd.DataFrame(records).to_csv(cache, index=False)
            log.info("Climat/alti %d/%d sauvé", i + 1, len(restants))
        time.sleep(2.0)

    clim = pd.DataFrame(records).dropna(subset=["summer_temp_mean", "elevation_m"])
    tree = cKDTree(np.column_stack([clim["lon"], clim["lat"]]))
    cents = gpd.GeoSeries(grid.geometry.centroid, crs=grid.crs).to_crs(4326)
    _, jj = tree.query(np.column_stack([cents.x.values, cents.y.values]), k=1)
    out = grid.copy()
    out["summer_temp_mean"] = clim.iloc[jj]["summer_temp_mean"].values
    out["annual_precip"] = clim.iloc[jj]["annual_precip"].values
    out["elevation_m"] = clim.iloc[jj]["elevation_m"].values

    # pente/aspect via voisins grille 1 km
    pivot = out.set_index(["i", "j"])["elevation_m"]
    gs = cfg["analysis_unit"]["grid_size_m"]
    slopes, aspects = [], []
    for _, row in out.iterrows():
        e0 = row["elevation_m"]
        e_e = pivot.get((row["i"] + 1, row["j"]), e0)
        e_n = pivot.get((row["i"], row["j"] + 1), e0)
        dzdx = (e_e - e0) / gs
        dzdy = (e_n - e0) / gs
        slopes.append(float(np.degrees(np.arctan(np.sqrt(dzdx**2 + dzdy**2)))))
        aspects.append(float((np.degrees(np.arctan2(dzdy, -dzdx)) + 360) % 360))
    out["slope_deg"] = slopes
    out["aspect_deg"] = aspects
    out["aspect_sin"] = np.sin(np.radians(out["aspect_deg"]))
    out["aspect_cos"] = np.cos(np.radians(out["aspect_deg"]))
    return out


def add_coast_distance(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    region = gpd.read_file(download_region_outline()).to_crs(grid.crs)
    boundary = region.union_all().boundary
    out = grid.copy()
    out["dist_coast_km"] = out.geometry.centroid.distance(boundary) / 1000.0
    return out


def build_analysis_table() -> Path:
    cfg = load_config()
    processed = ROOT / cfg["paths"]["processed"]
    checkpoint = processed / "forest_grid_1km_base.gpkg"

    if checkpoint.exists():
        log.info("Reprise depuis checkpoint %s", checkpoint)
        grid = gpd.read_file(checkpoint)
    else:
        pnr_path = extract_pnr_corse()
        pnr = gpd.read_file(pnr_path)
        forest = filter_forest_polygons(load_bd_foret())
        region = gpd.read_file(download_region_outline()).to_crs(forest.crs)
        forest = gpd.clip(forest, region)

        grid = build_forest_grid(forest)
        grid = assign_pnr(grid, pnr)
        grid.drop(columns=["centroid"], errors="ignore").to_file(
            checkpoint, driver="GPKG", layer="cells"
        )
        log.info("Checkpoint base → %s", checkpoint)

    if "centroid" not in grid.columns:
        grid["centroid"] = grid.geometry.centroid

    need_climate = (
        "summer_temp_mean" not in grid.columns
        or "elevation_m" not in grid.columns
        or grid["elevation_m"].isna().all()
    )
    if need_climate:
        log.info("Climat + altitude (grille Open-Meteo Archive)…")
        grid = add_climate_and_elevation_grid(grid)
    if "dist_coast_km" not in grid.columns:
        log.info("Distance côte…")
        grid = add_coast_distance(grid)

    out = grid.drop(columns=["centroid"], errors="ignore")
    path = processed / "forest_grid_1km.gpkg"
    out.to_file(path, driver="GPKG", layer="cells")
    write_metadata(
        path.with_suffix(".meta.json"),
        {
            "n_cells": len(out),
            "n_pnr": int(out["in_pnr"].sum()),
            "n_out_pnr": int((out["in_pnr"] == 0).sum()),
            "grid_size_m": cfg["analysis_unit"]["grid_size_m"],
            "min_forest_fraction": cfg["analysis_unit"]["min_forest_fraction"],
        },
    )
    log.info("OK → %s", path)
    return path


if __name__ == "__main__":
    build_analysis_table()
