"""
Téléchargement des données vectorielles / climatiques / métadonnées EO.

Sentinel-2 : pas de bulk local — accès via Planetary Computer STAC
(voir timeseries.py) pour éviter des centaines de Go.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from . import ROOT, ensure_dirs, load_config, setup_logger, write_metadata

log = setup_logger()


def download_file(url: str, dest: Path, timeout: int = 600) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        log.info("Déjà présent: %s", dest.name)
        return dest
    log.info("Téléchargement %s", url)
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                if chunk:
                    f.write(chunk)
    return dest


def extract_pnr_corse() -> Path:
    """Extrait le PNR Corse depuis le GeoJSON national FPNRF."""
    cfg = load_config()
    raw = ROOT / cfg["paths"]["raw"] / "pnr"
    gj = raw / "Parcs_naturels_regionaux_de_France.geojson"
    if not gj.exists():
        url = (
            "https://static.data.gouv.fr/resources/"
            "parcs-naturels-regionaux-de-france-au-07-novembre-2024-59-pnr/"
            "20241107-163138/parcs-naturels-regionaux-de-france-geojson-espg2154.zip"
        )
        zpath = raw / "pnr_france.zip"
        download_file(url, zpath)
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(raw)

    gdf = gpd.read_file(gj)
    # Cherche Corse dans colonnes texte
    mask = None
    for c in gdf.columns:
        if c == "geometry":
            continue
        s = gdf[c].map(lambda x: str(x) if x is not None else "")
        m = s.str.contains("Corse|CORSE|Corsica", case=False, regex=True, na=False)
        if m.any():
            mask = m if mask is None else (mask | m)
            log.info("PNR Corse trouvé via colonne %s (%d)", c, int(m.sum()))
    if mask is None or not mask.any():
        raise RuntimeError("PNR Corse introuvable dans le fichier national — vérifier attributs")
    pnr = gdf.loc[mask].copy()
    out = ROOT / cfg["paths"]["processed"] / "pnr_corse.gpkg"
    out.parent.mkdir(parents=True, exist_ok=True)
    pnr = pnr.to_crs(cfg["project"]["crs_analysis"])
    pnr["geometry"] = pnr.buffer(0)
    pnr.to_file(out, driver="GPKG", layer="pnr")
    write_metadata(
        out.with_suffix(".meta.json"),
        {
            "source": cfg["data_sources"]["pnr"],
            "n_features": len(pnr),
            "crs": str(pnr.crs),
            "bounds": list(pnr.total_bounds),
            "columns": list(pnr.columns),
        },
    )
    log.info("PNR Corse → %s (%d entités)", out, len(pnr))
    return out


def load_bd_foret() -> gpd.GeoDataFrame:
    """Charge BD Forêt v2 2A+2B (couche FORMATION_VEGETALE)."""
    cfg = load_config()
    foret_dir = ROOT / cfg["paths"]["raw"] / "foret"
    shps = list(foret_dir.rglob("FORMATION_VEGETALE.shp"))
    if not shps:
        raise FileNotFoundError(
            f"FORMATION_VEGETALE.shp introuvable dans {foret_dir}. "
            "Télécharger D02A/D02B BDFORET puis extraire les .7z (py7zr)."
        )

    parts = []
    for shp in shps:
        g = gpd.read_file(shp)
        g["source_file"] = shp.name
        parts.append(g)
        log.info("Lu %s (%d)", shp, len(g))
    gdf = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=parts[0].crs)
    gdf = gdf.to_crs(cfg["project"]["crs_analysis"])
    gdf["geometry"] = gdf.buffer(0)
    return gdf


def filter_forest_polygons(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Conserve les formations boisées BD Forêt v2.
    Codes TFV : FF* / FO* = forêts ; LA* = landes/herbacées (exclues du masque forêt strict).
    """
    if "CODE_TFV" not in gdf.columns:
        raise RuntimeError("CODE_TFV manquant — fichier BD Forêt inattendu")

    code = gdf["CODE_TFV"].astype(str).str.upper()
    keep = code.str.startswith("FF") | code.str.startswith("FO")
    out = gdf.loc[keep].copy()
    out["forest_type_raw"] = out["CODE_TFV"].astype(str)
    tfv = out.get("TFV", out["CODE_TFV"]).astype(str).str.lower()

    out["forest_type_group"] = "other"
    out.loc[tfv.str.contains("feuill", na=False) & ~tfv.str.contains("conif", na=False), "forest_type_group"] = "broadleaf"
    out.loc[tfv.str.contains("conif", na=False) & ~tfv.str.contains("feuill", na=False), "forest_type_group"] = "conifer"
    out.loc[tfv.str.contains("mélange|melange|feuillus et conif|conifères prépond|feuillus prépond", regex=True, na=False), "forest_type_group"] = "mixed"
    # codes FO/FF mixtes via CODE
    out.loc[out["CODE_TFV"].astype(str).str.match(r"FF3|FO3", na=False), "forest_type_group"] = "mixed"

    log.info("Forêts retenues (FF/FO): %d / %d", len(out), len(gdf))
    log.info("Groupes: %s", out["forest_type_group"].value_counts().to_dict())
    return out


def download_region_outline() -> Path:
    """Contour Corse (france-geojson, usage contexte)."""
    cfg = load_config()
    out = ROOT / cfg["paths"]["raw"] / "admin" / "region-corse.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        return out
    # copie locale si présente dans le monorepo
    local = ROOT.parent / "region-corse.geojson"
    if local.exists():
        out.write_bytes(local.read_bytes())
        return out
    url = (
        "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/"
        "regions/corse/region-corse.geojson"
    )
    download_file(url, out)
    return out


if __name__ == "__main__":
    ensure_dirs()
    extract_pnr_corse()
    download_region_outline()
    print("OK download étape 1")
