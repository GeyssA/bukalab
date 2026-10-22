"""Indices de télédétection et justifications écologiques."""
from __future__ import annotations

import numpy as np

# Justifications (voir docs/report.md)
JUSTIFICATIONS = {
    "NDVI": (
        "Indice de végétation normalisé (NIR-Red)/(NIR+Red). "
        "Proxy d'activité photosynthétique / verdure de canopée. "
        "Limite: saturé en canopées denses; sensible au sol en maquis ouvert."
    ),
    "NDMI": (
        "Normalized Difference Moisture Index (NIR-SWIR)/(NIR+SWIR). "
        "Sensible au contenu en eau du feuillage / stress hydrique relatif. "
        "Limite: confusions possibles avec structure et ombres."
    ),
    "EVI": (
        "Enhanced Vegetation Index — moins saturé que NDVI, correction atmosphérique partielle. "
        "Complément pour peuplements denses."
    ),
    "VH_VV": (
        "Ratio Sentinel-1 VH/VV : information structurelle / volume de diffusion. "
        "Complément sous nuages; non interprété seul comme stress hydrique."
    ),
}


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    return (nir - red) / (nir + red + 1e-6)


def ndmi(nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
    return (nir - swir) / (nir + swir + 1e-6)


def evi(nir: np.ndarray, red: np.ndarray, blue: np.ndarray) -> np.ndarray:
    return 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1 + 1e-6)


def sen2cor_scl_clear(scl: np.ndarray) -> np.ndarray:
    """Masque pixels clairs SCL: vegetation(4), bare(5), water(6) exclus water optionnel.
    Garde 4 (vegetation), 5 (not vegetated), 7 (unclassified) prudemment.
    Exclut nuages 8,9,10,11 et ombres 3.
    """
    return np.isin(scl, [4, 5, 7])
