"""
BukaLab — pistes de logo (planche comparative).

  py bukalab_logo_pistes.py

Sortie : bukalab_identity/pistes_logo.png / .pdf
Chaque symbole est dessiné dans un carré [cx ± r, cy ± r] d'un axes à aspect égal.
"""

from __future__ import annotations

import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from bukalab_identity import BRAND, FONT, OUT, setup_rc


def _mix(c1: str, c2: str, f: float) -> tuple:
    a = np.array(mcolors.to_rgb(c1))
    b = np.array(mcolors.to_rgb(c2))
    return tuple(a + (b - a) * f)


# ---------------------------------------------------------------------------
# A — « Pixel b » : la lettre b composée dans une grille 4 × 4 (raster, télédétection)
# ---------------------------------------------------------------------------
PIXEL_B = [
    [1, 0, 0, 0],
    [1, 1, 1, 0],
    [1, 0, 0, 1],
    [1, 1, 1, 0],
]


def mark_pixel(ax, cx, cy, r, dark=False):
    s = 2 * r / 4
    g = 0.14 * s
    on = BRAND["sand"] if dark else BRAND["teal"]
    off = _mix(BRAND["teal"], BRAND["sand"], 0.14) if dark else BRAND["mist"]
    for i, row in enumerate(PIXEL_B):
        for j, v in enumerate(row):
            x = cx - r + j * s + g / 2
            y = cy + r - (i + 1) * s + g / 2
            ax.add_patch(mpatches.FancyBboxPatch(
                (x, y), s - g, s - g, boxstyle=f"round,pad=0,rounding_size={0.18 * s}",
                facecolor=on if v else off, edgecolor="none"))
    # point de donnée dans la contre-forme du b
    ax.add_patch(mpatches.Circle((cx - r + 2 * s, cy + r - 2.5 * s), 0.30 * s,
                                 facecolor=BRAND["terracotta"], edgecolor="none"))


# ---------------------------------------------------------------------------
# B — « Losange » : matrice 4 × 4 pivotée (signature cartographique bivariée)
# ---------------------------------------------------------------------------
def mark_diamond(ax, cx, cy, r, dark=False):
    n = 4
    side = r * np.sqrt(2) / n
    g = 0.12 * side
    base, top = ("#BFD8DE", BRAND["ink"]) if not dark else (_mix(BRAND["teal"], BRAND["sand"], 0.35), BRAND["sand"])
    c45 = np.cos(np.pi / 4)
    for i in range(n):
        for j in range(n):
            f = (i + j) / (2 * n - 2)
            col = BRAND["terracotta"] if (i, j) == (3, 1) else _mix(base, top, 0.15 + 0.85 * f)
            u0, v0 = i * side + g / 2, j * side + g / 2
            u1, v1 = u0 + side - g, v0 + side - g
            pts = []
            for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
                uu, vv = u - n * side / 2, v - n * side / 2
                pts.append((cx + (uu - vv) * c45, cy + (uu + vv) * c45))
            ax.add_patch(mpatches.Polygon(pts, closed=True, facecolor=col, edgecolor="none",
                                          joinstyle="round"))


# ---------------------------------------------------------------------------
# C — « Feuille-réseau » : feuille dont les nervures sont un graphe (biologie × IA)
# ---------------------------------------------------------------------------
def mark_leaf(ax, cx, cy, r, dark=False):
    fill = BRAND["sand"] if dark else BRAND["teal"]
    vein = BRAND["teal"] if dark else BRAND["sand"]
    rot = np.deg2rad(40)
    R = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])

    def tr(x, y):
        p = R @ np.vstack([x, y]) * r * 0.92
        return p[0] + cx, p[1] + cy

    x = np.linspace(-1, 1, 300)
    w = 0.46 * (1 - x ** 2) ** 0.85 * (1 + 0.25 * x)
    ox, oy = tr(np.r_[x, x[::-1]], np.r_[w, -w[::-1]])
    ax.add_patch(mpatches.Polygon(np.c_[ox, oy], closed=True, facecolor=fill, edgecolor="none"))
    lw = r * 72 * 0.045
    mx, my = tr(np.array([-1.18, 0.86]), np.array([0.0, 0.0]))
    ax.plot(mx, my, color=fill, lw=lw, solid_capstyle="round")
    mx, my = tr(np.array([-0.92, 0.86]), np.array([0.0, 0.0]))
    ax.plot(mx, my, color=vein, lw=lw, solid_capstyle="round")
    nodes = []
    for x0, k in ((-0.50, 0.62), (-0.05, 0.66), (0.40, 0.60)):
        for sgn in (1, -1):
            x1 = x0 + 0.30
            w1 = 0.46 * (1 - x1 ** 2) ** 0.85 * (1 + 0.25 * x1) * k
            vx, vy = tr(np.array([x0, x1]), np.array([0.0, sgn * w1]))
            ax.plot(vx, vy, color=vein, lw=lw * 0.8, solid_capstyle="round")
            nodes.append((vx[1], vy[1]))
    for k, (nx, ny) in enumerate(nodes):
        col = BRAND["terracotta"] if k == 3 else vein
        ax.add_patch(mpatches.Circle((nx, ny), 0.065 * r, facecolor=col, edgecolor="none", zorder=5))


# ---------------------------------------------------------------------------
# D — « Monogramme B » : B géométrique dans un carré arrondi
# ---------------------------------------------------------------------------
def mark_monogram(ax, cx, cy, r, dark=False):
    tile = BRAND["sand"] if dark else BRAND["teal"]
    ink = BRAND["teal"] if dark else BRAND["sand"]
    ax.add_patch(mpatches.FancyBboxPatch(
        (cx - r, cy - r), 2 * r, 2 * r, boxstyle=f"round,pad=0,rounding_size={0.42 * r}",
        facecolor=tile, edgecolor="none"))
    t = 0.16 * r
    x_stem = cx - 0.40 * r
    y_bot, y_top = cy - 0.56 * r, cy + 0.56 * r
    xc = cx + 0.02 * r
    up_c, up_R = cy + 0.28 * r, 0.28 * r
    lo_c, lo_R = cy - 0.20 * r, 0.36 * r
    parts = [
        mpatches.Rectangle((x_stem, y_bot), t, y_top - y_bot),
        mpatches.Rectangle((x_stem, y_top - t), xc - x_stem, t),
        mpatches.Rectangle((x_stem, up_c - up_R), xc - x_stem, t),
        mpatches.Rectangle((x_stem, y_bot), xc - x_stem, t),
        mpatches.Wedge((xc, up_c), up_R, -90, 90, width=t),
        mpatches.Wedge((xc, lo_c), lo_R, -90, 90, width=t),
    ]
    for p in parts:
        p.set_facecolor(ink)
        p.set_edgecolor("none")
        ax.add_patch(p)
    ax.add_patch(mpatches.Circle((cx - 0.05 * r, cy + 0.28 * r), 0.06 * r,
                                 facecolor=BRAND["terracotta"], edgecolor="none"))


PISTES = [
    ("A", "Pixel b", "La lettre b composée dans une grille 4 × 4 : raster, télédétection,\n"
     "donnée. Le point terracotta marque l'observation.", mark_pixel, "lower"),
    ("B", "Losange", "Matrice 4 × 4 pivotée, signature des cartes bivariées du laboratoire.\n"
     "Une cellule terracotta : la donnée qui ressort.", mark_diamond, "camel"),
    ("C", "Feuille-réseau", "Feuille dont les nervures forment un graphe : biologie et IA,\n"
     "vivant et modèle. Un nœud terracotta.", mark_leaf, "camel"),
    ("D", "Monogramme B", "B géométrique dans un carré arrondi, lisible en très petit\n"
     "(favicon, avatar). Contre-forme ponctuée de terracotta.", mark_monogram, "camel"),
]


def lockup(fig, rect, mark_fn, style="camel", dark=False):
    ax = fig.add_axes(rect)
    ax.set_axis_off()
    w_in, h_in = rect[2] * fig.get_figwidth(), rect[3] * fig.get_figheight()
    ax.set_xlim(0, w_in)
    ax.set_ylim(0, h_in)
    ax.set_aspect("equal")
    if dark:
        ax.add_patch(mpatches.Rectangle((0, 0), w_in, h_in, facecolor=BRAND["teal"], edgecolor="none"))
    r = h_in * 0.30
    cx, cy = h_in * 0.18 + r, h_in / 2
    mark_fn(ax, cx, cy, r, dark=dark)
    fs = r * 72 * 0.95
    main = BRAND["sand"] if dark else BRAND["ink"]
    lab = "#9FD0D8" if dark else BRAND["teal"]
    x0 = cx + r * 1.45
    w1, w2 = ("buka", "lab") if style == "lower" else ("Buka", "Lab")
    t1 = ax.text(x0, cy, w1, fontsize=fs, fontweight="bold", color=main, va="center", ha="left", family=FONT)
    fig.canvas.draw()
    bb = t1.get_window_extent(fig.canvas.get_renderer())
    x1 = ax.transData.inverted().transform((bb.x1, bb.y0))[0]
    ax.text(x1 + r * 0.03, cy, w2, fontsize=fs, fontweight="light", color=lab, va="center", ha="left", family=FONT)


def mark_only(fig, rect, mark_fn, bg=None, dark=False):
    ax = fig.add_axes(rect)
    ax.set_axis_off()
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-1.25, 1.25)
    ax.set_aspect("equal")
    if bg:
        ax.add_patch(mpatches.FancyBboxPatch((-1.25, -1.25), 2.5, 2.5,
                                             boxstyle="round,pad=0,rounding_size=0.3",
                                             facecolor=bg, edgecolor="none"))
    mark_fn(ax, 0, 0, 1.0, dark=dark)


def main():
    setup_rc()
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.05, 0.94, "BukaLab — pistes de logo", fontsize=18, fontweight="bold", color=BRAND["ink"])
    fig.text(0.05, 0.905, "Quatre directions, même palette. Chaque piste : version claire, version sombre, "
             "symbole seul en grand et en très petit.", fontsize=9, color=BRAND["stone"])
    fig.add_artist(plt.Line2D([0.05, 0.95], [0.885, 0.885], color=BRAND["teal"], lw=1.0))

    for k, (code, name, desc, fn, style) in enumerate(PISTES):
        col, row = k % 2, k // 2
        x0 = 0.05 + col * 0.465
        y0 = 0.48 - row * 0.425
        fig.text(x0, y0 + 0.37, f"{code}", fontsize=13, fontweight="bold", color=BRAND["terracotta"])
        fig.text(x0 + 0.025, y0 + 0.37, name, fontsize=13, fontweight="bold", color=BRAND["ink"])
        fig.text(x0, y0 + 0.345, desc, fontsize=7.6, color=BRAND["stone"], va="top", linespacing=1.4)
        lockup(fig, [x0, y0 + 0.155, 0.43, 0.12], fn, style)
        lockup(fig, [x0, y0 + 0.025, 0.25, 0.115], fn, style, dark=True)
        mark_only(fig, [x0 + 0.27, y0 + 0.025, 0.09, 0.115], fn, bg=BRAND["mist"])
        mark_only(fig, [x0 + 0.375, y0 + 0.06, 0.03, 0.04], fn)
        mark_only(fig, [x0 + 0.41, y0 + 0.068, 0.018, 0.024], fn)

    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"pistes_logo.{ext}", dpi=220)
    plt.close(fig)
    print("Pistes ->", OUT / "pistes_logo.png")


if __name__ == "__main__":
    main()
