"""Validation indépendante et analyses de robustesse."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import ROOT, load_config, setup_logger, write_metadata

log = setup_logger()


def write_validation_protocol() -> Path:
    cfg = load_config()
    out = ROOT / "docs" / "validation_protocol.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    text = """# Protocole de validation

## Ce qui EST validable dans ce design

| Résultat télédétection | Donnée indépendante | Alignement | Limite |
|---|---|---|---|
| Chute NDVI / NDMI estivale | Périmètres EFFIS | spatial + année | EFFIS ≥~30 ha; omission petits feux |
| Type forestier (groupe) | BD Forêt IGN / IFN points | classe | pas de validation biomasse |
| Gradient altitude | MNT / Open-Meteo elev. | spatial | OK |
| Stress hydrique NDMI | IFN dépérissement / observations terrain | rare / décalé | **ne pas prétendre valider NDMI = dépérissement** |

## Ce qui N'EST PAS une validation

- Corréler NDVI avec un autre indice spectral dérivé de Sentinel-2
- Utiliser l'IFN pour "valider" une tendance NDVI pixel sans co-localisation temporelle

## Procédure EFFIS

1. Demander les burnt areas Corse 2017–2025 via le formulaire JRC
2. Intersection avec `forest_grid_1km`
3. Matrice de confusion : événement spectral vs feu cartographié
4. Rapporter précision / rappel — pas seulement des exemples

## Robustesse prévue (scripts)

- Grilles 500 m / 1000 m / 2000 m
- Avec / sans cellules `burned_ever`
- Matching caliper 0.25 / 0.5 / 1.0
- Années 2017–2019 exclues (début S2 L2A plus hétérogène)
"""
    out.write_text(text, encoding="utf-8")
    write_metadata(
        ROOT / cfg["paths"]["processed"] / "validation.meta.json",
        {"protocol": str(out), "status": "protocol_ready_awaiting_effis_and_s2"},
    )
    return out


def sensitivity_placeholder_table() -> Path:
    cfg = load_config()
    rows = [
        {"test": "grid_500m", "status": "pending", "note": "relancer preprocessing grid_size_m=500"},
        {"test": "grid_2000m", "status": "pending", "note": "relancer preprocessing grid_size_m=2000"},
        {"test": "exclude_burned", "status": "pending", "note": "filtrer burned_ever==0 avant matching"},
        {"test": "caliper_0.25", "status": "pending", "note": "matching.caliper_sd"},
        {"test": "drop_years_2017_2018", "status": "pending", "note": "recompute trends"},
        {"test": "S2_only_vs_S2S1", "status": "pending", "note": "S1 optionnel — justifié structure"},
    ]
    path = ROOT / cfg["paths"]["tables"] / "sensitivity_plan.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path
