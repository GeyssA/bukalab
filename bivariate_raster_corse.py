"""
Carte bivariée T° × Précipitations — grille 3×3 (codes 11–33)

COMMENT EXÉCUTER :
1. QGIS → Extensions → Console Python
2. Icône "Afficher l'éditeur" (feuille + crayon)
3. Ouvre CE fichier (ou colle TOUT le contenu)
4. Exécuter (triangle vert) EN HAUT de l'éditeur — pas dans >>>

Prérequis :
- rasters déjà dans le projet (idéalement *_smooth, EPSG:2154)
"""

from qgis.core import (
    QgsRasterLayer,
    QgsPalettedRasterRenderer,
    QgsProject,
)
from qgis.PyQt.QtGui import QColor, QPainter
import processing
import numpy as np

# =============================================================================
# 1. ADAPTER CES NOMS à tes couches dans QGIS
# =============================================================================
TEMP_LAYER_NAME = "temp_2025_smooth"
PRECIP_LAYER_NAME = "prec_2025_smooth"
OUT_DIR = r"C:/Users/arnau/Documents/SIG/land_evolution"

# =============================================================================
# 2. Palette Africa 3×3 (9 couleurs)
#    lignes = T1→T3 (bas→haut), colonnes = P1→P3 (sec→humide)
# =============================================================================
#       P1 (sec)     P2          P3 (humide)
#  T3   #c85a2a      #8a6b3a     #3d5c3a
#  T2   #d4a07a      #9a9a7a     #4a7a6a
#  T1   #e8e0d4      #a8b8b0     #3a7a8a

PALETTE = {
    11: "#e8e0d4",  # T1 P1 — frais / sec
    12: "#a8b8b0",  # T1 P2
    13: "#3a7a8a",  # T1 P3 — frais / humide
    21: "#d4a07a",  # T2 P1
    22: "#9a9a7a",  # T2 P2
    23: "#4a7a6a",  # T2 P3
    31: "#c85a2a",  # T3 P1 — chaud / sec
    32: "#8a6b3a",  # T3 P2
    33: "#3d5c3a",  # T3 P3 — chaud / humide
}

# =============================================================================
# 3. Récupérer les couches
# =============================================================================
project = QgsProject.instance()


def get_raster(name: str) -> QgsRasterLayer:
    layers = project.mapLayersByName(name)
    if not layers:
        raise RuntimeError(
            f"Couche '{name}' introuvable. "
            "Vérifie le nom exact dans le panneau Couches."
        )
    lyr = layers[0]
    if not isinstance(lyr, QgsRasterLayer):
        raise RuntimeError(f"'{name}' n'est pas un raster.")
    return lyr


temp_lyr = get_raster(TEMP_LAYER_NAME)
precip_lyr = get_raster(PRECIP_LAYER_NAME)

print("Temp :", temp_lyr.source())
print("Prec :", precip_lyr.source())

# =============================================================================
# 4. Seuils quantiles 33 % / 66 %  →  3 classes
# =============================================================================

def quantile_breaks(layer: QgsRasterLayer, q_list=(1 / 3, 2 / 3)):
    provider = layer.dataProvider()
    extent = layer.extent()
    width = layer.width()
    height = layer.height()
    block = provider.block(1, extent, width, height)
    nodata = provider.sourceNoDataValue(1)

    vals = []
    for r in range(height):
        for c in range(width):
            v = block.value(r, c)
            if v is None:
                continue
            if nodata is not None and v == nodata:
                continue
            if np.isnan(v):
                continue
            vals.append(float(v))

    if len(vals) < 10:
        raise RuntimeError(f"Trop peu de pixels valides sur '{layer.name()}'")

    arr = np.array(vals)
    breaks = [float(np.quantile(arr, q)) for q in q_list]
    print(
        f"  {layer.name()} : min={arr.min():.2f} max={arr.max():.2f} "
        f"seuils Q33/Q66={breaks}"
    )
    return breaks


print("Calcul des quantiles 3 classes…")
t1, t2 = quantile_breaks(temp_lyr)
p1, p2 = quantile_breaks(precip_lyr)

# =============================================================================
# 5. Classification 1 / 2 / 3
# =============================================================================

def classify_raster_3(layer, s1, s2, out_path, out_name):
    """
    classe 1 si < s1
    classe 2 si >= s1 et < s2
    classe 3 si >= s2
    """
    ref = f'"{layer.name()}@1"'
    expr = (
        f"(({ref} < {s1}) * 1) + "
        f"(({ref} >= {s1}) AND ({ref} < {s2})) * 2 + "
        f"(({ref} >= {s2}) * 3)"
    )
    result = processing.run(
        "qgis:rastercalculator",
        {
            "EXPRESSION": expr,
            "LAYERS": [layer],
            "CELLSIZE": 0,
            "EXTENT": layer.extent(),
            "CRS": layer.crs(),
            "OUTPUT": out_path,
        },
    )
    out_lyr = QgsRasterLayer(result["OUTPUT"], out_name)
    project.addMapLayer(out_lyr)
    print("Créé :", out_name, "→", out_path)
    return out_lyr


temp_class_path = f"{OUT_DIR}/temp_class_3.tif"
precip_class_path = f"{OUT_DIR}/precip_class_3.tif"
bivar_path = f"{OUT_DIR}/bivar_TP_codes_3x3.tif"

print("Classification température (1–3)…")
temp_class = classify_raster_3(temp_lyr, t1, t2, temp_class_path, "temp_class_3")

print("Classification précipitations (1–3)…")
precip_class = classify_raster_3(
    precip_lyr, p1, p2, precip_class_path, "precip_class_3"
)

# =============================================================================
# 6. Code bivarié = 10 * classe_T + classe_P  →  11…33
# =============================================================================
print("Combinaison bivariée 3×3…")
expr_bivar = '("temp_class_3@1" * 10) + "precip_class_3@1"'
result_bivar = processing.run(
    "qgis:rastercalculator",
    {
        "EXPRESSION": expr_bivar,
        "LAYERS": [temp_class, precip_class],
        "CELLSIZE": 0,
        "EXTENT": temp_class.extent(),
        "CRS": temp_class.crs(),
        "OUTPUT": bivar_path,
    },
)

bivar = QgsRasterLayer(result_bivar["OUTPUT"], "bivar_TP_codes_3x3")
project.addMapLayer(bivar)
print("Raster bivarié :", bivar_path)

# =============================================================================
# 7. Palette en mode « Valeurs uniques » (Paletted)
#    IMPORTANT : ne PAS utiliser Luminosité / Contraste / Saturation sur ce raster.
#    Ces curseurs cassent le rendu Exact/PseudoColor et font disparaître des classes
#    (effet « île blanche »). Pour voir l’ombrage : Multiply + Opacité seulement.
# =============================================================================
classes = [
    QgsPalettedRasterRenderer.Class(code, QColor(hexcol), str(code))
    for code, hexcol in PALETTE.items()
]
renderer = QgsPalettedRasterRenderer(bivar.dataProvider(), 1, classes)
bivar.setRenderer(renderer)

# Fusion avec l’ombrage (place l’ombrage EN DESSOUS dans le panneau Couches)
bivar.setBlendMode(QPainter.CompositionMode_Multiply)
bivar.setOpacity(0.85)
bivar.triggerRepaint()

print("\nTerminé.")
print("Couche à garder : bivar_TP_codes_3x3 (codes 11–33, rendu Paletted).")
print("Ne touche PAS à Luminosité/Contraste — utilise Opacité + mode Multiplier.")
print("Tu peux masquer temp_class_3 / precip_class_3.")
print("\nLégende :")
print("       P1 (sec)     P2          P3 (humide)")
print("  T3 ", PALETTE[31], PALETTE[32], PALETTE[33])
print("  T2 ", PALETTE[21], PALETTE[22], PALETTE[23])
print("  T1 ", PALETTE[11], PALETTE[12], PALETTE[13])
