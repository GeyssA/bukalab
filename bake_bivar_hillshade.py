"""
Bake 1 couche visuelle : couleurs bivariées × ombrage

Résultat : un GeoTIFF RGB unique où relief + climat sont déjà fusionnés.
→ Plus besoin de Multiply entre 2 calques en 2D.
→ En 3D : Terrain = MNT (output_hh si c'est bien un DEM) + cette texture RGB drapée.

Exécuter dans la console Python QGIS (éditeur → triangle vert).
"""

from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsRasterFileWriter,
    QgsRasterPipe,
    QgsRectangle,
    Qgis,
)
from qgis.PyQt.QtGui import QColor, QPainter, QImage
from qgis.utils import iface
import processing
import os

# =============================================================================
# ADAPTER
# =============================================================================
BIVAR_NAME = "bivar_TP_codes_3x3"
DEM_NAME = "output_hh"          # MNT pour générer l'ombrage (et terrain 3D)
OUT_DIR = r"C:/Users/arnau/Documents/SIG/land_evolution"
OUT_RGB = os.path.join(OUT_DIR, "bivar_hillshade_bake.tif").replace("\\", "/")

# Force de l'ombrage dans le bake (0.3 = léger, 0.6 = marqué)
SHADE_STRENGTH = 0.45

# =============================================================================
project = QgsProject.instance()
os.makedirs(OUT_DIR, exist_ok=True)


def ban(txt, level=Qgis.Info):
    print(txt)
    try:
        iface.messageBar().pushMessage("Bake", txt, level=level, duration=10)
    except Exception:
        pass


def get_rast(name: str) -> QgsRasterLayer:
    layers = project.mapLayersByName(name)
    if not layers or not isinstance(layers[0], QgsRasterLayer):
        raise RuntimeError(f"Couche raster '{name}' introuvable")
    return layers[0]


bivar = get_rast(BIVAR_NAME)
dem = get_rast(DEM_NAME)

# Vérif DEM
st = dem.dataProvider().bandStatistics(1)
ban(f"DEM {DEM_NAME}: min={st.minimumValue:.1f} max={st.maximumValue:.1f}")
if st.maximumValue <= 255:
    ban(
        "ATTENTION: max<=255 → ça ressemble à un hillshade déjà. "
        "On l'utilisera tel quel comme ombrage.",
        Qgis.Warning,
    )
    hillshade_path = dem.source()
    use_existing_hs = True
else:
    use_existing_hs = False

# =============================================================================
# 1. Ombrage depuis le MNT (si besoin)
# =============================================================================
hs_path = os.path.join(OUT_DIR, "hillshade_from_dem.tif").replace("\\", "/")

if use_existing_hs:
    hs = dem
    ban("Utilisation de output_hh comme ombrage existant")
else:
    ban("Génération ombrage depuis le MNT…")
    res = processing.run(
        "native:hillshade",
        {
            "INPUT": dem,
            "Z_FACTOR": 1.5,
            "AZIMUTH": 315,
            "V_ANGLE": 40,
            "OUTPUT": hs_path,
        },
    )
    hs = QgsRasterLayer(res["OUTPUT"], "hillshade_from_dem")
    project.addMapLayer(hs)
    ban(f"Ombrage créé : {hs_path}")

# =============================================================================
# 2. Aligner ombrage sur l'emprise / résolution du bivarié
# =============================================================================
hs_aligned = os.path.join(OUT_DIR, "hillshade_aligned.tif").replace("\\", "/")
ban("Alignement ombrage → grille du bivarié…")
processing.run(
    "gdal:warpreproject",
    {
        "INPUT": hs,
        "SOURCE_CRS": hs.crs(),
        "TARGET_CRS": bivar.crs(),
        "RESAMPLING": 1,  # bilinear
        "NODATA": None,
        "TARGET_RESOLUTION": 0,
        "OPTIONS": "",
        "DATA_TYPE": 0,
        "TARGET_EXTENT": bivar.extent(),
        "TARGET_EXTENT_CRS": bivar.crs(),
        "MULTITHREADING": True,
        "EXTRA": f"-tr {bivar.rasterUnitsPerPixelX()} {abs(bivar.rasterUnitsPerPixelY())}",
        "OUTPUT": hs_aligned,
    },
)
hs2 = QgsRasterLayer(hs_aligned, "hillshade_aligned")
if not hs2.isValid():
    raise RuntimeError("Alignement ombrage échoué")

# =============================================================================
# 3. Exporter le bivarié rendu (palette) en RGB GeoTIFF
# =============================================================================
bivar_rgb = os.path.join(OUT_DIR, "bivar_rgb_temp.tif").replace("\\", "/")
ban("Export bivarié → RGB…")

# Assurer rendu Normal opaque
bivar.setBlendMode(QPainter.CompositionMode_SourceOver)
bivar.setOpacity(1.0)
bivar.triggerRepaint()

extent = bivar.extent()
width = bivar.width()
height = bivar.height()

pipe = QgsRasterPipe()
provider = bivar.dataProvider()
if not pipe.set(provider.clone()):
    raise RuntimeError("pipe.set provider failed")
if bivar.renderer() is not None:
    pipe.set(bivar.renderer().clone())

writer = QgsRasterFileWriter(bivar_rgb)
err = writer.writeRaster(pipe, width, height, extent, bivar.crs())
if err != QgsRasterFileWriter.NoError:
    # Fallback GDAL translate après rendu via processing
    ban(f"writeRaster code={err}, fallback gdal:translate…", Qgis.Warning)
    processing.run(
        "gdal:translate",
        {
            "INPUT": bivar,
            "TARGET_CRS": bivar.crs(),
            "NODATA": None,
            "COPY_SUBDATASETS": False,
            "OPTIONS": "",
            "EXTRA": "-expand rgb",
            "DATA_TYPE": 0,
            "OUTPUT": bivar_rgb,
        },
    )

rgb = QgsRasterLayer(bivar_rgb, "bivar_rgb_temp")
if not rgb.isValid():
    # 2e fallback : renderAsImage
    ban("Fallback renderAsImage…", Qgis.Warning)
    img = bivar.renderer().block(1, extent, width, height)  # may fail for paletted
    raise RuntimeError(
        "Export RGB échoué. Dans QGIS : clic droit bivar → Exporter → "
        "Sauver sous… GeoTIFF, coche 'Rendu' / 'Rendered image', puis relance "
        "en mettant BIVAR_NAME = ce fichier exporté."
    )

# =============================================================================
# 4. Bake : RGB * ombrage  (Raster calculator par bande si possible,
#    sinon GDAL VRT / native via processing sagang)
# =============================================================================
ban("Fusion RGB × ombrage…")

# Méthode robuste : gdal calc si dispo, sinon 3 calculs + merge
# shade normalisé 0.3–1.0 pour ne pas noircir trop
# formula: out = rgb * ((1-s) + s * (hs/255))

def bake_band(band_idx: int, out_path: str):
    # Utilise qgis raster calculator avec noms de couches
    # On ajoute temporairement rgb et hs2 au projet si besoin
    if not project.mapLayersByName(rgb.name()):
        project.addMapLayer(rgb, False)
    if not project.mapLayersByName(hs2.name()):
        project.addMapLayer(hs2, False)

    s = SHADE_STRENGTH
    # Couche RGB peut être 1 bande palettée exportée ou 3 bandes
    nband = rgb.bandCount()
    if nband >= 3:
        ref = f'"{rgb.name()}@{band_idx}"'
    else:
        # rendu mono — on ne peut pas bake correctement
        raise RuntimeError(
            "Le bivarié exporté n'a pas 3 bandes RGB. "
            "Exporte-le manuellement : clic droit → Exporter → "
            "format GeoTIFF + option 'image rendue' / Rendered."
        )

    hsref = f'"{hs2.name()}@1"'
    # mix : couleur * (1 - strength + strength * hs/255)
    expr = (
        f"{ref} * ((1 - {s}) + {s} * ({hsref} / 255.0))"
    )
    processing.run(
        "qgis:rastercalculator",
        {
            "EXPRESSION": expr,
            "LAYERS": [rgb, hs2],
            "CELLSIZE": 0,
            "EXTENT": extent,
            "CRS": bivar.crs(),
            "OUTPUT": out_path,
        },
    )


if rgb.bandCount() < 3:
    ban(
        "Export auto n'a pas donné 3 bandes. "
        "Fais l'export manuel du bivarié (image rendue), "
        "puis mets BIVAR_NAME sur ce GeoTIFF RGB et relance.",
        Qgis.Critical,
    )
    raise SystemExit

r_path = os.path.join(OUT_DIR, "_bake_r.tif").replace("\\", "/")
g_path = os.path.join(OUT_DIR, "_bake_g.tif").replace("\\", "/")
b_path = os.path.join(OUT_DIR, "_bake_b.tif").replace("\\", "/")

bake_band(1, r_path)
bake_band(2, g_path)
bake_band(3, b_path)

# Merge R,G,B
processing.run(
    "gdal:merge",
    {
        "INPUT": [r_path, g_path, b_path],
        "PCT": False,
        "SEPARATE": True,
        "NODATA_INPUT": None,
        "NODATA_OUTPUT": None,
        "OPTIONS": "",
        "EXTRA": "",
        "DATA_TYPE": 1,  # Byte
        "OUTPUT": OUT_RGB,
    },
)

out = QgsRasterLayer(OUT_RGB, "bivar_hillshade_BAKE")
if not out.isValid():
    raise RuntimeError(f"Bake invalide : {OUT_RGB}")

project.addMapLayer(out)
ban(f"OK → couche unique : bivar_hillshade_BAKE\n{OUT_RGB}", Qgis.Success)

print(
    f"""
TERMINÉ.

Couche à utiliser en 2D : bivar_hillshade_BAKE  (plus besoin de Multiply)

En 3D :
  Terrain  = {DEM_NAME}          (élévation)
  Texture  = bivar_hillshade_BAKE (couleurs déjà ombrées)

Les 2 restent complémentaires :
  - MNT → forme 3D
  - Bake → apparence (bivar + ombrage intégrés)
"""
)
