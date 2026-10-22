"""
Pipeline principal — Corsica Forest Resilience

Usage:
  py -m src.download
  py -m src.preprocessing
  py -m src.timeseries          # faisabilité STAC + script GEE
  py -m src.matching            # après forest_grid (+ metrics si S2 prêt)
  py run_pipeline.py            # enchaînement documenté
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import ensure_dirs, setup_logger, load_config
from src.download import extract_pnr_corse, download_region_outline
from src.timeseries import feasibility_s2, load_or_instruct_timeseries, write_gee_export_script
from src.validation import write_validation_protocol, sensitivity_placeholder_table
from src.disturbances import load_effis_if_any

log = setup_logger()


def main():
    ensure_dirs()
    cfg = load_config()
    log.info("=== PHASE download / PNR ===")
    extract_pnr_corse()
    download_region_outline()

    log.info("=== PHASE EO feasibility ===")
    write_gee_export_script()
    try:
        feasibility_s2()
    except Exception as e:
        log.warning("Faisabilité STAC: %s", e)

    log.info("=== PHASE validation protocol ===")
    write_validation_protocol()
    sensitivity_placeholder_table()
    load_effis_if_any()

    # preprocessing needs BD Forêt extracted
    foret = ROOT / "data" / "raw" / "foret"
    shps = list(foret.rglob("*.shp"))
    if shps:
        log.info("=== PHASE preprocessing (BD Forêt détectée) ===")
        from src.preprocessing import build_analysis_table
        from src.matching import mahalanobis_match
        import geopandas as gpd

        grid_path = build_analysis_table()
        grid = gpd.read_file(grid_path)
        mahalanobis_match(grid)
        load_or_instruct_timeseries()
        # figures basiques
        from src.figures import fig_study_area, fig_covariate_balance
        from src.download import extract_pnr_corse, download_region_outline

        pnr = gpd.read_file(extract_pnr_corse())
        region = gpd.read_file(download_region_outline())
        fig_study_area(grid, pnr, region)
        bal = ROOT / cfg["paths"]["tables"] / "covariate_balance.csv"
        fig_covariate_balance(grid, bal if bal.exists() else None)
    else:
        log.warning(
            "BD Forêt non extraite encore dans %s — "
            "téléchargement .7z en cours ou installer 7-Zip puis relancer.",
            foret,
        )

    log.info("=== Pipeline étape terminée ===")
    print(
        """
Suivi:
1. Vérifier data/raw/foret (BD Forêt 2A/2B extraite)
2. py run_pipeline.py
3. Exporter S2 via src/gee_export_s2_seasonal.js → data/processed/
4. py -m src.matching && py -m src.timeseries
"""
    )


if __name__ == "__main__":
    main()
