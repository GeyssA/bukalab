"""Exporte les centroïdes de la grille pour Google Earth Engine (CSV WGS84)."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from . import ROOT, load_config, setup_logger

log = setup_logger()


def export_centroids_for_gee(grid_path: Path | None = None) -> Path:
    cfg = load_config()
    grid_path = grid_path or (ROOT / cfg["paths"]["processed"] / "forest_grid_1km.gpkg")
    g = gpd.read_file(grid_path)
    c = g.to_crs(4326)
    out = ROOT / cfg["paths"]["processed"] / "forest_cells_centroids_wgs84.csv"
    df = g[["cell_id", "in_pnr", "forest_fraction", "forest_type_group"]].copy()
    cents2154 = g.geometry.centroid
    c = gpd.GeoDataFrame(geometry=cents2154, crs=g.crs).to_crs(4326)
    df["longitude"] = c.geometry.x.values
    df["latitude"] = c.geometry.y.values
    df.to_csv(out, index=False)
    # GeoJSON points for GEE upload alternative
    pts = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )
    gj = ROOT / cfg["paths"]["processed"] / "forest_cells_centroids_wgs84.geojson"
    pts.to_file(gj, driver="GeoJSON")
    log.info("Centroïdes GEE → %s (%d)", out, len(df))
    return out


if __name__ == "__main__":
    export_centroids_for_gee()
