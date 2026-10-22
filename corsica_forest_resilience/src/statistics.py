"""Wrapper statistiques (exports tables)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .matching import compare_outcomes, naive_vs_matched_means, mahalanobis_match
from . import ROOT, load_config, setup_logger

log = setup_logger()


def run_stats(grid_path: Path, metrics_path: Path) -> None:
    import geopandas as gpd

    grid = gpd.read_file(grid_path)
    pairs = mahalanobis_match(grid)
    metrics = pd.read_csv(metrics_path)
    compare_outcomes(metrics, pairs, grid)
    naive_vs_matched_means(metrics, grid)
    log.info("Statistiques terminées → outputs/tables/")
