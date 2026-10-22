"""
Exporte couches T° / précipitations / bivarié pour une année,
avec SEUILS FIGÉS (réf. 2025) — indispensable pour animer 2015→2025.

  py export_france_annee_couches.py --year 2015 --classes 4

Sorties dans output_france/annees/{year}/ :
  - points CSV classés
  - GeoPackage points
  - QML temp / precip / bivar (mêmes classes que toutes les années)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

BASE = Path(__file__).resolve().parent
REF_CSV = BASE / "france_climat_2025_grille.csv"
GRILLES = BASE / "output_france" / "grilles_annuelles"
OUT_ROOT = BASE / "output_france" / "annees"

# Palette Africa-like 4×4 (T bas→haut, P sec→humide)
# Si classes=3, on sous-échantillonne ; si 5, on interpolera plus tard.
PALETTE_4x4 = {
    11: "#e8e0d4",
    12: "#c5d0c8",
    13: "#7aa0a8",
    14: "#3a7a8a",
    21: "#e0c4a8",
    22: "#c4b896",
    23: "#7a9a7a",
    24: "#3a7a6a",
    31: "#d4a07a",
    32: "#b89060",
    33: "#8a7a4a",
    34: "#4a6a4a",
    41: "#c85a2a",
    42: "#a86b3a",
    43: "#8a6b3a",
    44: "#3d5c3a",
}

TEMP_COLORS_4 = ["#f5efe6", "#e8c4a0", "#c85a2a", "#7a2e12"]
PRECIP_COLORS_4 = ["#f5efe6", "#c5d4e0", "#3a7a8a", "#1a3a5c"]


def load_breaks(n: int) -> dict:
    path = GRILLES / f"classes_fixes_{n}x{n}_ref2025.json"
    if not path.exists():
        # calcule à la volée
        from recuperer_france_climat_grille import compute_fixed_breaks_from_2025

        return compute_fixed_breaks_from_2025(n)
    return json.loads(path.read_text(encoding="utf-8"))


def classify(values: np.ndarray, breaks: list[float]) -> np.ndarray:
    """Classe 1..n selon seuils croissants (quantiles figés)."""
    return np.digitize(values, breaks, right=False) + 1  # 1..n


def write_qml_graduated(path: Path, attr: str, breaks_full: list[float], colors: list[str], labels: list[str]):
    """breaks_full = [vmin, b1, b2, ..., vmax] longueur n+1."""
    ranges = []
    symbols = []
    for i in range(len(colors)):
        lo, hi = breaks_full[i], breaks_full[i + 1]
        ranges.append(
            f'      <range symbol="{i}" lower="{lo}" upper="{hi}" label="{labels[i]}" render="true"/>'
        )
        r, g, b = (int(colors[i][1:3], 16), int(colors[i][3:5], 16), int(colors[i][5:7], 16))
        symbols.append(
            f"""      <symbol type="marker" name="{i}" alpha="1" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="0" enabled="1" locked="0">
          <prop k="color" v="{r},{g},{b},255"/>
          <prop k="name" v="circle"/>
          <prop k="outline_style" v="no"/>
          <prop k="size" v="1.6"/>
        </layer>
      </symbol>"""
        )
    xml = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34.0" styleCategories="Symbology">
  <renderer-v2 type="graduatedSymbol" attr="{attr}" graduatedMethod="GraduatedColor"
               forceraster="0" symbollevels="0" enableorderby="0">
    <ranges>
{chr(10).join(ranges)}
    </ranges>
    <symbols>
{chr(10).join(symbols)}
    </symbols>
  </renderer-v2>
</qgis>
"""
    path.write_text(xml, encoding="utf-8")


def write_qml_bivar(path: Path, n: int, palette: dict):
    cats = []
    syms = []
    for i, (code, hexcol) in enumerate(sorted(palette.items())):
        t, p = divmod(code, 10)
        cats.append(
            f'      <category symbol="{i}" value="{code}" label="T{t}-P{p}" render="true"/>'
        )
        r, g, b = int(hexcol[1:3], 16), int(hexcol[3:5], 16), int(hexcol[5:7], 16)
        syms.append(
            f"""      <symbol type="marker" name="{i}" alpha="1" force_rhr="0" clip_to_extent="1">
        <layer class="SimpleMarker" pass="0" enabled="1" locked="0">
          <prop k="color" v="{r},{g},{b},255"/>
          <prop k="name" v="circle"/>
          <prop k="outline_style" v="no"/>
          <prop k="size" v="1.6"/>
        </layer>
      </symbol>"""
        )
    xml = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34.0" styleCategories="Symbology">
  <renderer-v2 type="categorizedSymbol" attr="bivar_code" forceraster="0" symbollevels="0" enableorderby="0">
    <categories>
{chr(10).join(cats)}
    </categories>
    <symbols>
{chr(10).join(syms)}
    </symbols>
  </renderer-v2>
</qgis>
"""
    path.write_text(xml, encoding="utf-8")


def build_palette(n: int) -> dict:
    if n == 4:
        return PALETTE_4x4.copy()
    # générique : mélange coins
    corners = {
        (1, 1): np.array([232, 224, 212]),
        (1, n): np.array([58, 122, 138]),
        (n, 1): np.array([200, 90, 42]),
        (n, n): np.array([61, 92, 58]),
    }
    pal = {}
    for ti in range(1, n + 1):
        for pi in range(1, n + 1):
            ft = (ti - 1) / (n - 1)
            fp = (pi - 1) / (n - 1)
            c = (
                (1 - ft) * (1 - fp) * corners[(1, 1)]
                + (1 - ft) * fp * corners[(1, n)]
                + ft * (1 - fp) * corners[(n, 1)]
                + ft * fp * corners[(n, n)]
            )
            pal[ti * 10 + pi] = "#{:02x}{:02x}{:02x}".format(*c.astype(int))
    return pal


def export_year(year: int, n_classes: int = 4) -> Path:
    src = GRILLES / f"france_climat_{year}_grille.csv"
    if year == 2025 and not src.exists():
        src = REF_CSV
    if not src.exists():
        raise FileNotFoundError(f"CSV manquant pour {year}: {src}\nLance d'abord recuperer_france_climat_grille.py --year {year}")

    br = load_breaks(n_classes)
    df = pd.read_csv(src)
    # normalise noms de colonnes
    tcol = f"temp_moyenne_{year}"
    pcol = f"precip_totale_{year}"
    if tcol not in df.columns:
        # fallback si fichier 2025 de référence
        alt_t = [c for c in df.columns if c.startswith("temp_moyenne")]
        alt_p = [c for c in df.columns if c.startswith("precip_totale")]
        if not alt_t or not alt_p:
            raise ValueError(f"Colonnes T/P introuvables dans {src}")
        df = df.rename(columns={alt_t[0]: tcol, alt_p[0]: pcol})

    t = df[tcol].values.astype(float)
    p = df[pcol].values.astype(float)
    t_cls = classify(t, br["temp_breaks"])
    p_cls = classify(p, br["precip_breaks"])
    # clip 1..n
    t_cls = np.clip(t_cls, 1, n_classes)
    p_cls = np.clip(p_cls, 1, n_classes)
    df["temp_class"] = t_cls
    df["precip_class"] = p_cls
    df["bivar_code"] = t_cls * 10 + p_cls

    out_dir = OUT_ROOT / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_out = out_dir / f"france_climat_{year}_classe.csv"
    df.to_csv(csv_out, index=False)

    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
        crs="EPSG:4326",
    )
    # Évite fiona/pyogrio (souvent cassés sous Windows) : GeoJSON via to_json()
    geojson = out_dir / f"france_points_{year}.geojson"
    geojson.write_text(gdf.to_json(), encoding="utf-8")

    # QML
    t_full = [br["temp_min"] - 0.01] + br["temp_breaks"] + [br["temp_max"] + 0.01]
    p_full = [br["precip_min"] - 0.01] + br["precip_breaks"] + [br["precip_max"] + 0.01]
    # couleurs mono
    if n_classes == 4:
        tcols, pcols = TEMP_COLORS_4, PRECIP_COLORS_4
    else:
        # interpolate
        def ramp(c0, c1, k):
            out = []
            for i in range(k):
                f = i / (k - 1)
                rgb = tuple(int((1 - f) * int(c0[j : j + 2], 16) + f * int(c1[j : j + 2], 16)) for j in (1, 3, 5))
                out.append("#{:02x}{:02x}{:02x}".format(*rgb))
            return out

        tcols = ramp("#f5efe6", "#7a2e12", n_classes)
        pcols = ramp("#f5efe6", "#1a3a5c", n_classes)

    t_labels = []
    p_labels = []
    for i in range(n_classes):
        t_labels.append(f"T{i+1} {t_full[i]:.1f}–{t_full[i+1]:.1f} °C")
        p_labels.append(f"P{i+1} {p_full[i]:.0f}–{p_full[i+1]:.0f} mm")

    write_qml_graduated(out_dir / f"temp_{year}.qml", tcol, t_full, tcols, t_labels)
    write_qml_graduated(out_dir / f"precip_{year}.qml", pcol, p_full, pcols, p_labels)
    pal = build_palette(n_classes)
    write_qml_bivar(out_dir / f"bivar_{year}.qml", n_classes, pal)

    # mémo seuils
    (out_dir / "README_classes.txt").write_text(
        f"Année {year}\n"
        f"Classes = {n_classes}×{n_classes} (seuils FIGÉS sur 2025)\n"
        f"temp_breaks = {br['temp_breaks']}\n"
        f"precip_breaks = {br['precip_breaks']}\n"
        f"Ne PAS recalculer les quantiles sur cette année seule.\n",
        encoding="utf-8",
    )
    print(f"Export {year} → {out_dir}")
    return out_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--classes", type=int, default=4, choices=[3, 4, 5])
    args = ap.parse_args()
    export_year(args.year, args.classes)


if __name__ == "__main__":
    main()
