"""
Poster climat France (température × précipitations) — BukaLab.

Rendu entièrement vectoriel (aplats contourf découpés sur le trait de côte),
classes FIXES identiques pour toutes les années, emprise fixe, palette BukaLab.

  py render_france_animation.py --years 2015 2025

Sorties : output_france/publication/
  france_climat_poster_YYYY.pdf / .png   (A3 paysage, 300 dpi)
  france_climat_2015_2025.mp4            (fondu enchaîné entre posters)
  stats_YYYY.json
"""

from __future__ import annotations

import argparse
import io
import json
import time
import textwrap
from pathlib import Path

import imageio.v2 as imageio
import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapely
from matplotlib.path import Path as MPath
from matplotlib.transforms import Affine2D
from PIL import Image
from shapely.geometry import shape
from shapely.ops import unary_union

BASE = Path(__file__).resolve().parent
GRILLES = BASE / "output_france" / "grilles_annuelles"
OUT = BASE / "output_france" / "publication"
REF_CSV = BASE / "france_climat_2025_grille.csv"
COAST = BASE / "output_france" / "metropole.geojson"
REGIONS = BASE / "output_france" / "regions.geojson"

# ---------------------------------------------------------------------------
# Classes FIXES — quartiles 2025 arrondis, identiques pour toutes les années
# ---------------------------------------------------------------------------
T_BREAKS = [11.2, 12.0, 13.1]
P_BREAKS = [780.0, 900.0, 1040.0]

# Textes dépendant de la période agrégée ; configure() bascule tout le module
SAISON = "annee"
TXT = {
    "annee": {
        "titre": "Température et précipitations annuelles — France, {year}",
        "t_panel": "Température moyenne annuelle",
        "p_panel": "Cumul annuel des précipitations",
        "periode": "annuelle",
        "methode_1": "moyenne annuelle de la température journalière à 2 m et cumul annuel des précipitations.",
        "suffixe": "",
    },
    "printemps_ete": {
        "titre": "Température et précipitations de printemps-été — France, {year}",
        "t_panel": "Température moyenne, 1er mars – 31 août",
        "p_panel": "Cumul des précipitations, 1er mars – 31 août",
        "periode": "de printemps-été",
        "methode_1": "moyenne de la température journalière à 2 m et cumul des précipitations "
                     "du 1er mars au 31 août (printemps + été, 184 jours).",
        "suffixe": "_printemps_ete",
    },
}


def fmt_mm(v: float) -> str:
    return f"{int(round(v)):,}".replace(",", " ")


def labels(breaks, f) -> list[str]:
    b = [f(v) for v in breaks]
    return [f"≤ {b[0]}", f"{b[0]} – {b[1]}", f"{b[1]} – {b[2]}", f"> {b[2]}"]


def season_breaks(grilles: Path) -> tuple[list[float], list[float]]:
    """Quartiles 2025 de la saison, arrondis (0,1 °C ; 10 mm), figés dans un JSON."""
    path = grilles / "classes_fixes_4x4_ref2025.json"
    if path.exists():
        d = json.loads(path.read_text(encoding="utf-8"))
        return d["temp_breaks"], d["precip_breaks"]
    df = pd.read_csv(grilles / "france_climat_2025_grille.csv")
    if len(df) < 2800:
        raise RuntimeError(f"Grille 2025 incomplète ({len(df)} points) : seuils non calculables")
    qs = [0.25, 0.5, 0.75]
    t = [round(float(np.quantile(df.temp_moyenne_2025, q)), 1) for q in qs]
    p = [round(float(np.quantile(df.precip_totale_2025, q)) / 10) * 10.0 for q in qs]
    path.write_text(json.dumps({
        "n_classes": 4, "reference_year": 2025, "saison": grilles.name,
        "method": "quartiles 2025 arrondis (0,1 °C ; 10 mm)",
        "temp_breaks": t, "precip_breaks": p,
    }, indent=2), encoding="utf-8")
    return t, p


def configure(saison: str) -> None:
    global SAISON, GRILLES, OUT, T_BREAKS, P_BREAKS, T_LABELS, P_LABELS
    SAISON = saison
    if saison != "annee":
        GRILLES = BASE / "output_france" / f"grilles_{saison}"
        OUT = BASE / "output_france" / f"publication_{saison}"
        T_BREAKS, P_BREAKS = season_breaks(GRILLES)
    T_LABELS = labels(T_BREAKS, fmt)
    P_LABELS = labels(P_BREAKS, fmt_mm)


T_LABELS = labels(T_BREAKS, lambda v: f"{v:.1f}".replace(".", ","))
P_LABELS = labels(P_BREAKS, fmt_mm)

# Rampes univariées ; le bivarié est leur produit (multiply) normalisé
T_RAMP = ["#F1EDE4", "#EEC39B", "#DC8C55", "#C0602B"]
P_RAMP = ["#F1EDE4", "#BCD5DE", "#78A9BF", "#3A7D9C"]

# Emprise FIXE (identique chaque année)
EXTENT = (-5.6, 10.0, 41.0, 51.4)
LAT0 = 46.5
ASPECT = 1.0 / np.cos(np.deg2rad(LAT0))

INK = "#15212B"
STONE = "#5B6670"
TEAL = "#1E5B63"
RULE = "#D5DADE"

CITIES = [
    ("Paris", 2.35, 48.86, (5, 4)),
    ("Lyon", 4.84, 45.76, (5, 3)),
    ("Marseille", 5.37, 43.30, (5, -9)),
    ("Toulouse", 1.44, 43.60, (5, 3)),
    ("Bordeaux", -0.58, 44.84, (-5, 3)),
    ("Nantes", -1.55, 47.22, (-5, 3)),
    ("Lille", 3.06, 50.63, (5, 2)),
    ("Strasbourg", 7.75, 48.58, (-5, 4)),
    ("Brest", -4.49, 48.39, (4, 4)),
    ("Clermont-Ferrand", 3.09, 45.78, (5, -9)),
    ("Ajaccio", 8.74, 41.93, (-5, 3)),
]

SEAS = [
    ("Océan\nAtlantique", -4.3, 45.6),
    ("Manche", -1.9, 50.05),
    ("Mer Méditerranée", 5.6, 42.35),
]


def hex2rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i : i + 2], 16) for i in (0, 2, 4)], dtype=float)


def rgb2hex(c) -> str:
    c = np.clip(np.round(c), 0, 255).astype(int)
    return "#{:02X}{:02X}{:02X}".format(*c)


def bivar_palette() -> dict[int, str]:
    base = hex2rgb(T_RAMP[0])
    pal = {}
    for ti in range(4):
        for pi in range(4):
            c = hex2rgb(T_RAMP[ti]) * hex2rgb(P_RAMP[pi]) / base
            pal[(ti + 1) * 10 + pi + 1] = rgb2hex(c)
    return pal


PAL = bivar_palette()


def fmt(v: float, d: int = 1) -> str:
    return f"{v:.{d}f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Données et champs
# ---------------------------------------------------------------------------
def load_year(year: int) -> tuple[pd.DataFrame, str, str]:
    p = GRILLES / f"france_climat_{year}_grille.csv"
    if not p.exists() and year == 2025 and SAISON == "annee":
        p = REF_CSV
    df = pd.read_csv(p)
    tcol, pcol = f"temp_moyenne_{year}", f"precip_totale_{year}"
    if tcol not in df.columns:
        df = df.rename(columns={
            next(c for c in df.columns if c.startswith("temp_moyenne")): tcol,
            next(c for c in df.columns if c.startswith("precip_totale")): pcol,
        })
    return df, tcol, pcol


def load_geography():
    coast = json.loads(COAST.read_text(encoding="utf-8"))
    land = shape(coast["geometry"]).buffer(0).simplify(0.002, preserve_topology=True)
    regions = json.loads(REGIONS.read_text(encoding="utf-8"))
    borders = unary_union([shape(f["geometry"]).boundary for f in regions["features"]])
    internal = borders.difference(land.boundary.buffer(0.02)).intersection(land)
    shapely.prepare(land)
    return land, internal


def idw(lons, lats, vals, xx, yy, power=2.0, k=16):
    pts = np.column_stack([lons, lats])
    out = np.empty(xx.size)
    fx, fy = xx.ravel(), yy.ravel()
    for i in range(0, fx.size, 6000):
        dx = fx[i : i + 6000, None] - pts[None, :, 0]
        dy = (fy[i : i + 6000, None] - pts[None, :, 1]) * ASPECT
        d2 = np.maximum(dx * dx + dy * dy, 1e-14)
        idx = np.argpartition(d2, k, axis=1)[:, :k]
        w = 1.0 / np.take_along_axis(d2, idx, axis=1) ** (power / 2)
        out[i : i + 6000] = (w * vals[idx]).sum(1) / w.sum(1)
    return out.reshape(xx.shape)


def gaussian(a: np.ndarray, sigma: float) -> np.ndarray:
    r = int(np.ceil(3 * sigma))
    x = np.arange(-r, r + 1)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    a = np.pad(a, r, mode="edge")
    a = np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 1, a)
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), 0, a)


def upsample(a: np.ndarray, f: int) -> np.ndarray:
    ny, nx = a.shape
    xo, yo = np.arange(nx), np.arange(ny)
    xn = np.linspace(0, nx - 1, (nx - 1) * f + 1)
    yn = np.linspace(0, ny - 1, (ny - 1) * f + 1)
    tmp = np.vstack([np.interp(xn, xo, row) for row in a])
    return np.vstack([np.interp(yn, yo, col) for col in tmp.T]).T


def classify(v: np.ndarray, breaks) -> np.ndarray:
    return np.digitize(v, breaks) + 1


def build_fields(year: int, land, res=0.04, sigma=2.2, up=4) -> dict:
    df, tcol, pcol = load_year(year)
    xs = np.arange(EXTENT[0], EXTENT[1] + 1e-9, res)
    ys = np.arange(EXTENT[2], EXTENT[3] + 1e-9, res)
    xx, yy = np.meshgrid(xs, ys)
    print(f"  {year}: interpolation IDW {xx.shape[1]}×{xx.shape[0]}", flush=True)
    t = gaussian(idw(df.lon.values, df.lat.values, df[tcol].values, xx, yy), sigma)
    p = gaussian(idw(df.lon.values, df.lat.values, df[pcol].values, xx, yy), sigma)

    # Statistiques surfaciques (pondération cos φ, cellules terrestres)
    on_land = shapely.contains_xy(land, xx, yy)
    w = np.cos(np.deg2rad(yy)) * on_land
    tc, pc = classify(t, T_BREAKS), classify(p, P_BREAKS)
    code = tc * 10 + pc
    W = w.sum()
    stats = {
        "year": year,
        "n_points_era5": int(len(df)),
        "mean_temp_c": float((t * w).sum() / W),
        "mean_precip_mm": float((p * w).sum() / W),
        "share_T": [float(w[tc == k].sum() / W) for k in range(1, 5)],
        "share_P": [float(w[pc == k].sum() / W) for k in range(1, 5)],
        "share_bivar": {str(c): float(w[code == c].sum() / W) for c in PAL},
        "breaks_T": T_BREAKS,
        "breaks_P": P_BREAKS,
    }
    for col, key in ((f"tmax_moyenne_{year}", "mean_tmax_points_c"), (f"jours_30_{year}", "mean_hot_days_points")):
        if col in df.columns:
            stats[key] = float(df[col].mean())

    xsf = np.linspace(xs[0], xs[-1], (len(xs) - 1) * up + 1)
    ysf = np.linspace(ys[0], ys[-1], (len(ys) - 1) * up + 1)
    return {"year": year, "xs": xsf, "ys": ysf, "t": upsample(t, up), "p": upsample(p, up), "stats": stats}


# ---------------------------------------------------------------------------
# Primitives cartographiques
# ---------------------------------------------------------------------------
def geom_to_path(geom) -> MPath:
    verts, codes = [], []
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    for poly in polys:
        for ring in (poly.exterior, *poly.interiors):
            xy = np.asarray(ring.coords)
            verts.extend(xy)
            codes += [MPath.MOVETO] + [MPath.LINETO] * (len(xy) - 2) + [MPath.CLOSEPOLY]
    return MPath(np.asarray(verts), codes)


def map_axes(fig, rect, ticks=False):
    ax = fig.add_axes(rect)
    ax.set_xlim(EXTENT[0], EXTENT[1])
    ax.set_ylim(EXTENT[2], EXTENT[3])
    ax.set_aspect(ASPECT)
    ax.set_anchor("N")
    ax.set_facecolor("white")
    for s in ax.spines.values():
        s.set_color(RULE)
        s.set_linewidth(0.6)
    if ticks:
        ax.set_xticks([-4, -2, 0, 2, 4, 6, 8])
        ax.set_yticks([42, 44, 46, 48, 50])
        ax.set_xticklabels([f"{abs(v)}° {'O' if v < 0 else 'E'}" if v else "0°" for v in ax.get_xticks()])
        ax.set_yticklabels([f"{v}° N" for v in ax.get_yticks()])
        ax.tick_params(labelsize=7, colors=STONE, length=2.5, width=0.5)
        ax.grid(color="#EEF0F2", lw=0.5, zorder=0)
    else:
        ax.set_xticks([])
        ax.set_yticks([])
    return ax


def clip_patch(ax, land_path):
    patch = mpatches.PathPatch(land_path, transform=ax.transData, facecolor="none", edgecolor="none")
    ax.add_patch(patch)
    return patch


def _seamless(cs, clip):
    cs.set_clip_path(clip)
    cs.set_edgecolor("face")
    cs.set_linewidth(0.25)


def draw_frame(ax, land_path, internal, lw_coast=0.6, lw_reg=0.35):
    for g in getattr(internal, "geoms", [internal]):
        if g.geom_type in ("LineString", "LinearRing"):
            x, y = g.xy
            ax.plot(x, y, color="white", lw=lw_reg, alpha=0.85, zorder=8, solid_capstyle="round")
    ax.add_patch(mpatches.PathPatch(land_path, facecolor="none", edgecolor=INK, lw=lw_coast, zorder=9))


def plot_univariate(ax, F, field, breaks, ramp, land_path, internal):
    clip = clip_patch(ax, land_path)
    cs = ax.contourf(F["xs"], F["ys"], F[field], levels=[-1e9, *breaks, 1e9], colors=ramp, zorder=2)
    _seamless(cs, clip)
    iso = ax.contour(F["xs"], F["ys"], F[field], levels=breaks, colors=[INK], linewidths=0.25, alpha=0.3, zorder=3)
    iso.set_clip_path(clip)
    draw_frame(ax, land_path, internal, lw_coast=0.45, lw_reg=0.25)


def plot_bivariate(ax, F, land_path, internal):
    clip = clip_patch(ax, land_path)
    base = mpatches.PathPatch(land_path, facecolor=PAL[22], edgecolor="none", zorder=1)
    ax.add_patch(base)
    code = classify(F["t"], T_BREAKS) * 10 + classify(F["p"], P_BREAKS)
    for c, col in PAL.items():
        m = (code == c).astype(float)
        if m.max() == 0:
            continue
        cs = ax.contourf(F["xs"], F["ys"], m, levels=[0.5, 1.5], colors=[col], zorder=2)
        _seamless(cs, clip)
    draw_frame(ax, land_path, internal)


def annotate_main(ax, scale: float = 1.0):
    halo = [pe.withStroke(linewidth=2.2 * scale, foreground="white")]
    for name, x, y, (ox, oy) in CITIES:
        ax.plot(x, y, "o", ms=2.6 * scale, mfc=INK, mec="white", mew=0.6 * scale, zorder=12)
        ax.annotate(name, (x, y), xytext=(ox * scale, oy * scale), textcoords="offset points",
                    ha="left" if ox >= 0 else "right", fontsize=7.2 * scale, color=INK,
                    path_effects=halo, zorder=12)
    for name, x, y in SEAS:
        ax.text(x, y, name, fontsize=8 * scale, color="#8A98A3", style="italic", ha="center", va="center", zorder=1)

    # Barre d'échelle (à 42° N)
    lat_b, x0 = 41.55, -5.0
    km_deg = 111.32 * np.cos(np.deg2rad(lat_b))
    for i, col in enumerate([INK, "white", INK, "white"]):
        ax.add_patch(mpatches.Rectangle((x0 + i * 50 / km_deg, lat_b), 50 / km_deg, 0.07,
                                        facecolor=col, edgecolor=INK, lw=0.5, zorder=12))
    for km in (0, 100, 200):
        ax.text(x0 + km / km_deg, lat_b + 0.14, f"{km}", fontsize=6.5 * scale, color=INK, ha="center", zorder=12)
    ax.text(x0 + 200 / km_deg + 0.15, lat_b + 0.035, "km", fontsize=6.5 * scale, color=INK, va="center", zorder=12)

    # Nord
    ax.annotate("", xy=(-4.6, 43.05), xytext=(-4.6, 42.45),
                arrowprops=dict(arrowstyle="-|>,head_width=0.25,head_length=0.5", color=INK, lw=0.8 * scale), zorder=12)
    ax.text(-4.6, 43.15, "N", fontsize=8 * scale, fontweight="bold", color=INK, ha="center", va="bottom", zorder=12)


def map_box(ax):
    ax.apply_aspect()
    return ax.get_position()


def class_legend_strip(fig, ax, ramp, labels, unit):
    """Bandeau de classes sous la carte, aligné sur sa largeur réelle."""
    pos = map_box(ax)
    gap = 0.003
    w = (pos.width - 3 * gap) / 4
    y = pos.y0 - 0.03
    fig.text(pos.x0, pos.y0 - 0.011, f"Classes fixes ({unit})", fontsize=7, color=STONE, va="center")
    for i, (c, lab) in enumerate(zip(ramp, labels)):
        x = pos.x0 + i * (w + gap)
        fig.add_artist(mpatches.Rectangle((x, y), w, 0.011, transform=fig.transFigure, facecolor=c,
                                          edgecolor="#9AA4AC", lw=0.4))
        fig.text(x + w / 2, y - 0.006, lab, fontsize=6.8, color=INK, ha="center", va="top")


def diamond_legend(fig, rect):
    ax = fig.add_axes(rect)
    ax.set_axis_off()
    ax.set_aspect("equal")
    ax.set_xlim(-4.6, 4.6)
    ax.set_ylim(-2.3, 6.6)
    tr = Affine2D().rotate_deg(45) + ax.transData
    c45 = np.cos(np.pi / 4)

    def rot(x, y):
        return (x - y) * c45, (x + y) * c45

    for ti in range(4):
        for pi in range(4):
            ax.add_patch(mpatches.Rectangle((pi, ti), 1, 1, facecolor=PAL[(ti + 1) * 10 + pi + 1],
                                            edgecolor="white", lw=1.0, transform=tr))
    for k, lab in enumerate([fmt_mm(v) for v in P_BREAKS], start=1):
        x, y = rot(k, -0.32)
        ax.text(x, y, lab, fontsize=6.5, color=STONE, rotation=45, ha="center", va="center")
    for k, lab in enumerate([fmt(v) for v in T_BREAKS], start=1):
        x, y = rot(-0.32, k)
        ax.text(x, y, lab, fontsize=6.5, color=STONE, rotation=-45, ha="center", va="center")

    ax.annotate("", xy=rot(4.0, -0.85), xytext=rot(0.7, -0.85),
                arrowprops=dict(arrowstyle="-|>,head_width=0.18,head_length=0.35", color=INK, lw=0.7))
    ax.annotate("", xy=rot(-0.85, 4.0), xytext=rot(-0.85, 0.7),
                arrowprops=dict(arrowstyle="-|>,head_width=0.18,head_length=0.35", color=INK, lw=0.7))
    x, y = rot(2.35, -1.35)
    ax.text(x, y, "Précipitations (mm)", fontsize=7.5, color=INK, rotation=45, ha="center", va="center")
    x, y = rot(-1.35, 2.35)
    ax.text(x, y, "Température (°C)", fontsize=7.5, color=INK, rotation=-45, ha="center", va="center")

    corners = [
        ((4, 4), "Chaud et humide", "center", "bottom", (0, 0.22)),
        ((0, 4), "Chaud\net sec", "right", "center", (-0.2, 0)),
        ((4, 0), "Frais\net humide", "left", "center", (0.2, 0)),
    ]
    for (cx, cy), lab, ha, va, (dx, dy) in corners:
        x, y = rot(cx, cy)
        ax.text(x + dx, y + dy, lab, fontsize=7, color=STONE, style="italic", ha=ha, va=va)
    ax.text(0, -0.3, "Frais et sec", fontsize=7, color=STONE, style="italic", ha="center", va="top")
    return ax


def share_matrix(fig, rect, stats):
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 4)
    ax.set_aspect("equal")
    ax.set_anchor("W")
    for s in ax.spines.values():
        s.set_visible(False)
    for ti in range(4):
        for pi in range(4):
            c = (ti + 1) * 10 + pi + 1
            col = PAL[c]
            ax.add_patch(mpatches.Rectangle((pi, ti), 1, 1, facecolor=col, edgecolor="white", lw=1.2))
            v = 100 * stats["share_bivar"][str(c)]
            lum = hex2rgb(col) @ np.array([0.299, 0.587, 0.114])
            ax.text(pi + 0.5, ti + 0.5, fmt(v, 1) if v >= 0.05 else "–", fontsize=6.8,
                    ha="center", va="center", color="white" if lum < 120 else INK)
    ax.set_xticks(np.arange(4) + 0.5)
    pb, tb = [fmt_mm(v) for v in P_BREAKS], [fmt(v) for v in T_BREAKS]
    ax.set_xticklabels([f"≤ {pb[0]}", f"{pb[0]}–\n{pb[1]}", f"{pb[1]}–\n{pb[2]}", f"> {pb[2]}"],
                       fontsize=6, color=STONE)
    ax.set_yticks(np.arange(4) + 0.5)
    ax.set_yticklabels([f"≤ {tb[0]}", f"{tb[0]}–{tb[1]}", f"{tb[1]}–{tb[2]}", f"> {tb[2]}"],
                       fontsize=6, color=STONE)
    ax.tick_params(length=0, pad=2)
    ax.set_xlabel("Précipitations (mm)", fontsize=6.8, color=INK, labelpad=2)
    ax.set_ylabel("Température (°C)", fontsize=6.8, color=INK, labelpad=2)
    return ax


def share_bar(fig, rect, shares, ramp, label):
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()
    x = 0.0
    for s, c in zip(shares, ramp):
        ax.add_patch(mpatches.Rectangle((x, 0), s, 1, facecolor=c, edgecolor="white", lw=0.8))
        if s >= 0.08:
            lum = hex2rgb(c) @ np.array([0.299, 0.587, 0.114])
            ax.text(x + s / 2, 0.5, f"{fmt(100 * s, 0)} %", fontsize=6.5, ha="center", va="center",
                    color="white" if lum < 120 else INK)
        x += s
    ax.text(0, 1.25, label, fontsize=7, color=INK, va="bottom", transform=ax.transAxes)


# ---------------------------------------------------------------------------
# Poster
# ---------------------------------------------------------------------------
def _write_bytes(path: Path, data: bytes, tries: int = 6) -> None:
    """Écriture tolérante aux verrous transitoires (visionneuse, synchronisation)."""
    tmp = path.with_name(f".{path.stem}.tmp{path.suffix}")
    for i in range(tries):
        try:
            tmp.write_bytes(data)
            tmp.replace(path)
            return
        except OSError:
            time.sleep(1.5 * (i + 1))
    raise OSError(f"Impossible d'écrire {path}")


def render_poster(F: dict, land, internal, dpi=300) -> Path:
    from bukalab_identity import DOMAINS, draw_logo, draw_mark, setup_rc

    setup_rc()
    mpl.rcParams.update({"font.size": 8, "axes.unicode_minus": False})
    year, st = F["year"], F["stats"]
    land_path = geom_to_path(land)

    fig = plt.figure(figsize=(16.54, 11.69), dpi=dpi)

    # En-tête
    tx = TXT[SAISON]
    fig.text(0.035, 0.952, tx["titre"].format(year=year),
             fontsize=23, fontweight="bold", color=INK, va="center")
    fig.text(0.035, 0.917,
             "Chaque couleur combine une classe de température et une classe de précipitations. "
             "Seuils fixes, identiques pour toutes les années de la série.",
             fontsize=10.5, color=STONE, va="center")
    draw_logo(fig, [0.80, 0.912, 0.165, 0.062], variant="light", tagline=False)
    fig.add_artist(plt.Line2D([0.035, 0.965], [0.893, 0.893], color=TEAL, lw=1.2))

    # (a) Température
    ax_t = map_axes(fig, [0.035, 0.475, 0.215, 0.385])
    plot_univariate(ax_t, F, "t", T_BREAKS, T_RAMP, land_path, internal)
    class_legend_strip(fig, ax_t, T_RAMP, T_LABELS, "°C")
    fig.text(0.035, 0.872, "a", fontsize=12, fontweight="bold", color=INK, va="center")
    fig.text(0.05, 0.872, tx["t_panel"], fontsize=10, color=INK, va="center")

    # (b) Précipitations
    ax_p = map_axes(fig, [0.035, 0.07, 0.215, 0.385])
    plot_univariate(ax_p, F, "p", P_BREAKS, P_RAMP, land_path, internal)
    class_legend_strip(fig, ax_p, P_RAMP, P_LABELS, "mm")
    fig.text(0.035, 0.467, "b", fontsize=12, fontweight="bold", color=INK, va="center")
    fig.text(0.05, 0.467, tx["p_panel"], fontsize=10, color=INK, va="center")

    # (c) Bivariée
    ax_b = map_axes(fig, [0.285, 0.085, 0.49, 0.775], ticks=True)
    plot_bivariate(ax_b, F, land_path, internal)
    annotate_main(ax_b)
    fig.text(0.285, 0.872, "c", fontsize=12, fontweight="bold", color=INK, va="center")
    fig.text(0.30, 0.872, f"Synthèse bivariée température × précipitations — {year}",
             fontsize=10, color=INK, va="center")
    pos_b = map_box(ax_b)

    # Colonne droite
    xr, wr = 0.80, 0.165
    fig.text(xr, 0.872, "Légende", fontsize=10, fontweight="bold", color=INK, va="center")
    diamond_legend(fig, [xr - 0.005, 0.615, wr + 0.005, 0.245])

    fig.text(xr, 0.585, "Part du territoire par classe (%)", fontsize=9, fontweight="bold", color=INK)
    share_matrix(fig, [xr + 0.04, 0.395, wr - 0.04, 0.17], st)

    fig.text(xr, 0.335, "Répartition des surfaces", fontsize=9, fontweight="bold", color=INK)
    share_bar(fig, [xr, 0.285, wr, 0.02], st["share_T"], T_RAMP, "Température")
    share_bar(fig, [xr, 0.233, wr, 0.02], st["share_P"], P_RAMP, "Précipitations")
    fig.text(xr, 0.205,
             f"Moyennes pondérées par la surface :\n{fmt(st['mean_temp_c'])} °C  ·  "
             f"{fmt(st['mean_precip_mm'], 0)} mm",
             fontsize=7.2, color=STONE, va="top", linespacing=1.4)

    sT, sP = st["share_T"], st["share_P"]
    lecture = (
        f"En {year}, {fmt(100 * sP[0], 0)} % du territoire reçoit au plus {fmt_mm(P_BREAKS[0])} mm et "
        f"{fmt(100 * sP[3], 0)} % plus de {fmt_mm(P_BREAKS[2])} mm ; {fmt(100 * sT[3], 0)} % dépasse "
        f"{fmt(T_BREAKS[2])} °C de moyenne {tx['periode']}. Les seuils étant fixes, ces parts se comparent "
        f"directement entre années."
    )
    for a, b in ((" %", "\u00a0%"), (" mm", "\u00a0mm"), (" °C", "\u00a0°C"), ("1 0", "1\u00a00")):
        lecture = lecture.replace(a, b)
    fig.text(xr, 0.158, "Lecture", fontsize=9, fontweight="bold", color=INK)
    fig.text(xr, 0.145, "\n".join(textwrap.wrap(lecture, 46)), fontsize=7.2, color=STONE,
             va="top", linespacing=1.4)

    # Méthode, deux colonnes sous la carte principale
    y_m = pos_b.y0 - 0.032
    fig.text(pos_b.x0, y_m, "Méthode", fontsize=9, fontweight="bold", color=INK, va="center")
    steps = [
        f"{st['n_points_era5']:,}".replace(",", " ") + " points ERA5-Land (pas ≈ 0,15°) : " + tx["methode_1"],
        "Interpolation par pondération inverse à la distance (IDW, p = 2, 16 voisins), "
        "puis lissage gaussien (σ ≈ 0,09°).",
        f"Classes fixes, quartiles 2025 arrondis : T {' / '.join(fmt(v) for v in T_BREAKS)} °C ; "
        f"P {' / '.join(fmt_mm(v) for v in P_BREAKS)} mm. Comparables d'une année à l'autre.",
        "Coordonnées WGS 84, rapport d'aspect corrigé à 46,5° N. Données de réanalyse, "
        "et non mesures de stations.",
    ]
    col_w = pos_b.width / 2
    for i, s in enumerate(steps):
        x = pos_b.x0 + (i // 2) * col_w
        y = y_m - 0.016 - (i % 2) * 0.036
        fig.text(x, y, f"{i + 1}.", fontsize=7, color=TEAL, fontweight="bold", va="top")
        fig.text(x + 0.011, y, "\n".join(textwrap.wrap(s, 84)), fontsize=7, color=STONE,
                 va="top", linespacing=1.35)

    # Pied de page
    fig.add_artist(plt.Line2D([0.035, 0.965], [0.05, 0.05], color=RULE, lw=0.8))
    fig.text(0.035, 0.032,
             "Données : ERA5-Land, Copernicus Climate Change Service / ECMWF, via l'API Open-Meteo Archive.",
             fontsize=7.5, color=STONE, va="center")
    fig.text(0.035, 0.016, "Conception, traitement et cartographie : Arnaud Geyssels — BukaLab, 2026.",
             fontsize=7.5, color=STONE, va="center")
    fig.text(0.965, 0.032, "BukaLab", fontsize=9, fontweight="bold", color=TEAL, ha="right", va="center")
    fig.text(0.965, 0.016, "  ·  ".join(DOMAINS), fontsize=9.2, color=STONE, ha="right", va="center")
    mark_ax = fig.add_axes([0.919, 0.0245, 0.009, 0.016])
    mark_ax.set_axis_off()
    mark_ax.set_xlim(-1, 1)
    mark_ax.set_ylim(-1, 1)
    mark_ax.set_aspect("equal")
    draw_mark(mark_ax, 0, 0, 0.95)

    png = OUT / f"france_climat{tx['suffixe']}_poster_{year}.png"
    pdf = OUT / f"france_climat{tx['suffixe']}_poster_{year}.pdf"
    for path, kw in ((pdf, {}), (png, {"dpi": dpi})):
        buf = io.BytesIO()
        fig.savefig(buf, format=path.suffix[1:], **kw)
        _write_bytes(path, buf.getvalue())
    plt.close(fig)
    (OUT / f"stats_{year}.json").write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Poster {year} -> {pdf.name} / {png.name}", flush=True)
    return png


# ---------------------------------------------------------------------------
# Animation (fondu enchaîné entre posters)
# ---------------------------------------------------------------------------
def make_animation(posters: list[Path], years: list[int], fps=30, width=1920) -> Path:
    imgs = []
    for p in posters:
        im = Image.open(p).convert("RGB")
        h = int(round(im.height * width / im.width))
        im = im.resize((width, h), Image.LANCZOS)
        canvas = Image.new("RGB", (width, h + (-h) % 16), "white")
        canvas.paste(im, (0, 0))
        imgs.append(np.asarray(canvas).astype(np.float32))

    frames = []
    hold, fade = int(fps * 2.5), int(fps * 1.5)
    for i, im in enumerate(imgs):
        frames += [im] * hold
        if i < len(imgs) - 1:
            for k in range(fade):
                s = k / (fade - 1)
                s = s * s * (3 - 2 * s)
                frames.append((1 - s) * im + s * imgs[i + 1])
    frames += [imgs[-1]] * hold

    mp4 = OUT / f"france_climat{TXT[SAISON]['suffixe']}_{years[0]}_{years[-1]}.mp4"
    w = imageio.get_writer(mp4, fps=fps, codec="libx264", quality=None,
                           ffmpeg_params=["-crf", "16", "-pix_fmt", "yuv420p"], macro_block_size=16)
    for f in frames:
        w.append_data(np.clip(f, 0, 255).astype(np.uint8))
    w.close()
    print(f"  Animation -> {mp4.name}", flush=True)
    return mp4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="+", default=[2015, 2025])
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--saison", choices=sorted(TXT), default="annee")
    args = ap.parse_args()
    configure(args.saison)

    OUT.mkdir(parents=True, exist_ok=True)
    land, internal = load_geography()
    posters = []
    for y in args.years:
        F = build_fields(y, land)
        posters.append(render_poster(F, land, internal, dpi=args.dpi))
    if not args.no_video and len(posters) > 1:
        make_animation(posters, args.years)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
