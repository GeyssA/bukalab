"""
BukaLab — identité graphique (logo vectoriel, charte, carte de visite).

Le logo est dessiné en code (vectoriel, reproductible) : la lettre b composée
dans une grille raster 4 × 4 (télédétection, géomatique) et un point
d'observation terracotta dans sa contre-forme (donnée, biostatistique).

  py bukalab_identity.py

Sorties : bukalab_identity/
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

BASE = Path(__file__).resolve().parent
OUT = BASE / "bukalab_identity"

# ---------------------------------------------------------------------------
# Palette de marque
# ---------------------------------------------------------------------------
BRAND = {
    "ink": "#15212B",        # texte principal, traits
    "teal": "#1E5B63",       # couleur primaire — Buka Teal
    "lagoon": "#3A8FA0",     # secondaire — données, liens
    "terracotta": "#C4622D", # accent — point de donnée
    "sand": "#EFE8DC",       # fond chaud
    "mist": "#E6ECEE",       # fond froid / mer
    "stone": "#5B6670",      # texte secondaire
    "white": "#FFFFFF",
}

BRAND_NAMES = {
    "ink": "Encre",
    "teal": "Buka Teal",
    "lagoon": "Lagon",
    "terracotta": "Terracotta",
    "sand": "Sable",
    "mist": "Brume",
    "stone": "Pierre",
}

DOMAINS = ["Sciences", "Biostatistiques", "Biologie", "Géomatique", "IA", "Développement", "Télédétection"]

AUTHOR = {
    "name": "Arnaud Geyssels",
    "linkedin": "linkedin.com/in/arnaud-geyssels-159329243",
}


def font_family() -> str:
    import matplotlib.font_manager as fm

    available = {f.name for f in fm.fontManager.ttflist}
    for name in ("Segoe UI", "Source Sans 3", "Calibri", "DejaVu Sans"):
        if name in available:
            return name
    return "DejaVu Sans"


FONT = font_family()


def setup_rc():
    mpl.rcParams.update(
        {
            "font.family": FONT,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "path",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------
PIXEL_B = [
    [1, 0, 0, 0],
    [1, 1, 1, 0],
    [1, 0, 0, 1],
    [1, 1, 1, 0],
]

OFF_ON_DARK = "#3B6D73"


def _tile(ax, x, y, s, color, zorder, alpha=1.0):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), s, s, boxstyle=f"round,pad=0,rounding_size={0.2 * s}",
        facecolor=color, edgecolor="none", alpha=alpha, zorder=zorder))


def draw_mark(ax, cx: float, cy: float, r: float,
              on: str | None = None, off: str | None = None, dot: str | None = None,
              zorder: int = 10):
    """
    Symbole « pixel b » : la lettre b composée dans une grille 4 × 4 de demi-côté r,
    centrée en (cx, cy), dans un axes à aspect égal. off="none" masque les cases éteintes.
    """
    on = on or BRAND["teal"]
    off = off or BRAND["mist"]
    dot = dot or BRAND["terracotta"]
    s = 2 * r / 4
    g = 0.14 * s
    for i, row in enumerate(PIXEL_B):
        for j, v in enumerate(row):
            if not v and off == "none":
                continue
            _tile(ax, cx - r + j * s + g / 2, cy + r - (i + 1) * s + g / 2, s - g,
                  on if v else off, zorder)
    ax.add_patch(mpatches.Circle((cx - r + 2 * s, cy + r - 2.5 * s), 0.30 * s,
                                 facecolor=dot, edgecolor="none", zorder=zorder + 1))


def draw_logo(fig, rect, variant: str = "light", tagline: bool = True, mark_only: bool = False):
    """
    Logo complet dans un rectangle de figure [x, y, w, h].
    variant : "light" (fond clair) | "dark" (fond Buka Teal)
    """
    ax = fig.add_axes(rect)
    ax.set_axis_off()
    w_in = rect[2] * fig.get_figwidth()
    h_in = rect[3] * fig.get_figheight()
    ax.set_xlim(0, w_in)
    ax.set_ylim(0, h_in)
    ax.set_aspect("equal")

    if variant == "dark":
        word_main, word_lab, tag_c = BRAND["sand"], "#9FD0D8", "#E8F0F2"
        on, off = BRAND["sand"], OFF_ON_DARK
    else:
        word_main, word_lab, tag_c = BRAND["ink"], BRAND["teal"], BRAND["stone"]
        on, off = BRAND["teal"], BRAND["mist"]

    r = h_in * (0.5 if mark_only else 0.38)
    cy = h_in / 2 if (mark_only or not tagline) else h_in * 0.56
    cx = r if not mark_only else w_in / 2
    draw_mark(ax, cx, cy, r, on=on, off=off)
    if mark_only:
        return ax

    fs = r * 72 * 1.25
    x0 = cx + r * 1.3
    t1 = ax.text(x0, cy, "buka", fontsize=fs, fontweight="bold", color=word_main,
                 va="center_baseline", ha="left", family=FONT)
    fig.canvas.draw()
    bb = t1.get_window_extent(fig.canvas.get_renderer())
    x1 = ax.transData.inverted().transform((bb.x1, bb.y0))[0]
    ax.text(x1 + r * 0.02, cy, "lab", fontsize=fs, fontweight="light", color=word_lab,
            va="center_baseline", ha="left", family=FONT)
    if tagline:
        ax.text(x0 + r * 0.05, cy - r * 1.02, "  ·  ".join(d.upper() for d in DOMAINS),
                fontsize=fs * 0.26, color=tag_c, va="top", ha="left", family=FONT)
    return ax


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
def export_logos():
    OUT.mkdir(parents=True, exist_ok=True)
    specs = [
        ("bukalab_logo", "light", True, False, (7.0, 1.7), "white"),
        ("bukalab_logo_dark", "dark", True, False, (7.0, 1.7), BRAND["teal"]),
        ("bukalab_logo_simple", "light", False, False, (5.0, 1.3), "white"),
        ("bukalab_mark", "light", False, True, (2.0, 2.0), "none"),
    ]
    for name, variant, tag, mark_only, size, bg in specs:
        fig = plt.figure(figsize=size)
        fig.patch.set_facecolor(bg if bg != "none" else "white")
        if bg == "none":
            fig.patch.set_alpha(0)
        pad = 0.08
        draw_logo(fig, [pad / 2, pad, 1 - pad, 1 - 2 * pad], variant=variant, tagline=tag, mark_only=mark_only)
        for ext in ("svg", "pdf", "png"):
            fig.savefig(OUT / f"{name}.{ext}", dpi=600, transparent=(bg == "none"),
                        facecolor=fig.get_facecolor())
        plt.close(fig)
    print("Logos ->", OUT)


def _pixel_pattern(ax, x0, y0, nx, ny, s, color, sx=1, sy=1, seed=7):
    """Trame raster qui s'estompe depuis le coin (x0, y0) ; sx, sy orientent la trame."""
    rng = np.random.default_rng(seed)
    g = 0.16 * s
    for i in range(nx):
        for j in range(ny):
            d = np.hypot(i / nx, j / ny)
            if d > 1 or rng.random() > 1.05 - d:
                continue
            x = x0 + sx * i * s - (s if sx < 0 else 0)
            y = y0 + sy * j * s - (s if sy < 0 else 0)
            _tile(ax, x + g / 2, y + g / 2, s - g, color, 1, alpha=0.9 - 0.75 * d)


def export_business_card():
    """Carte de visite 85 × 55 mm, recto (marque) / verso (personne)."""
    w, h = 85 / 25.4, 55 / 25.4

    # Recto
    fig = plt.figure(figsize=(w, h))
    fig.patch.set_facecolor(BRAND["teal"])
    bg = fig.add_axes([0, 0, 1, 1])
    bg.set_axis_off()
    bg.set_xlim(0, w)
    bg.set_ylim(0, h)
    bg.set_aspect("equal")
    _pixel_pattern(bg, w, 0, 7, 6, 0.115, "#2A6870", sx=-1, sy=1)
    draw_logo(fig, [0.12, 0.36, 0.80, 0.30], variant="dark", tagline=False)
    fig.text(0.5, 0.16, "SCIENCES DES DONNÉES ENVIRONNEMENTALES", ha="center",
             fontsize=4.6, color="#C9D9DB", family=FONT)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"carte_visite_recto.{ext}", dpi=600, facecolor=BRAND["teal"])
    plt.close(fig)

    # Verso
    fig = plt.figure(figsize=(w, h))
    fig.patch.set_facecolor("white")
    bg = fig.add_axes([0, 0, 1, 1])
    bg.set_axis_off()
    bg.set_xlim(0, w)
    bg.set_ylim(0, h)
    bg.set_aspect("equal")
    bg.add_patch(mpatches.Rectangle((0, 0), 0.055, h, facecolor=BRAND["teal"], edgecolor="none"))
    _pixel_pattern(bg, w, 0, 9, 6, 0.09, BRAND["mist"], sx=-1, sy=1, seed=3)
    draw_mark(bg, w - 0.36, h - 0.36, 0.16, off="none")

    fig.text(0.10, 0.70, AUTHOR["name"], fontsize=11, fontweight="bold", color=BRAND["ink"], family=FONT)
    fig.text(0.10, 0.60, "BukaLab", fontsize=7.5, color=BRAND["teal"], fontweight="semibold", family=FONT)
    fig.text(0.10, 0.44, "Géomatique  ·  Télédétection  ·  Biostatistiques",
             fontsize=5.3, color=BRAND["stone"], family=FONT)
    fig.text(0.10, 0.37, "Biologie  ·  IA  ·  Développement", fontsize=5.3, color=BRAND["stone"], family=FONT)
    bg.plot([0.34, w * 0.62], [h * 0.25, h * 0.25], color=BRAND["terracotta"], lw=0.8)
    fig.text(0.10, 0.12, AUTHOR["linkedin"], fontsize=5.0, color=BRAND["ink"], family=FONT)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"carte_visite_verso.{ext}", dpi=600)
    plt.close(fig)
    print("Carte de visite ->", OUT)


def export_brand_sheet():
    """Charte graphique A4 paysage."""
    from render_france_animation import T_RAMP, P_RAMP, bivar_palette

    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor("white")
    fig.text(0.05, 0.93, "BukaLab — charte graphique", fontsize=20, fontweight="bold", color=BRAND["ink"])
    fig.text(0.05, 0.895, "  ·  ".join(DOMAINS), fontsize=9, color=BRAND["stone"])
    fig.add_artist(plt.Line2D([0.05, 0.95], [0.875, 0.875], color=BRAND["teal"], lw=1.0))

    # Logos
    fig.text(0.05, 0.835, "LOGO", fontsize=8, fontweight="bold", color=BRAND["teal"])
    draw_logo(fig, [0.05, 0.675, 0.42, 0.125], variant="light")
    dark_bg = fig.add_axes([0.52, 0.655, 0.43, 0.165])
    dark_bg.set_axis_off()
    dark_bg.add_patch(mpatches.Rectangle((0, 0), 1, 1, transform=dark_bg.transAxes,
                                         facecolor=BRAND["teal"], edgecolor="none"))
    draw_logo(fig, [0.545, 0.68, 0.38, 0.11], variant="dark")
    draw_logo(fig, [0.05, 0.50, 0.10, 0.12], mark_only=True)
    fig.text(0.16, 0.57, "Symbole seul : la lettre b dans une grille raster 4 × 4\n"
             "(télédétection, géomatique) et un point d'observation\n"
             "terracotta (donnée, biostatistique).",
             fontsize=8, color=BRAND["stone"], va="center")
    fig.text(0.52, 0.57, "Règles : zone de protection = rayon du symbole ;\n"
             "largeur minimale 25 mm (logo complet), 8 mm (symbole) ;\n"
             "ne pas déformer, recolorer ni ajouter d'effets.",
             fontsize=8, color=BRAND["stone"], va="center")

    # Palette
    fig.text(0.05, 0.455, "COULEURS", fontsize=8, fontweight="bold", color=BRAND["teal"])
    keys = ["teal", "lagoon", "terracotta", "ink", "stone", "sand", "mist"]
    for i, k in enumerate(keys):
        x = 0.05 + i * 0.128
        ax = fig.add_axes([x, 0.32, 0.115, 0.115])
        ax.set_axis_off()
        ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, facecolor=BRAND[k],
                                        edgecolor="#D0D4D8" if k in ("sand", "mist") else "none", lw=0.6))
        fig.text(x, 0.30, BRAND_NAMES[k], fontsize=8.5, fontweight="semibold", color=BRAND["ink"])
        fig.text(x, 0.28, BRAND[k].upper(), fontsize=7.5, color=BRAND["stone"])

    # Typo
    fig.text(0.05, 0.225, "TYPOGRAPHIE", fontsize=8, fontweight="bold", color=BRAND["teal"])
    fig.text(0.05, 0.18, f"{FONT} Bold — titres", fontsize=13, fontweight="bold", color=BRAND["ink"])
    fig.text(0.05, 0.145, f"{FONT} Regular — textes, légendes, méthodes", fontsize=10, color=BRAND["ink"])
    fig.text(0.05, 0.115, f"{FONT} Light — sous-titres", fontsize=10, fontweight="light", color=BRAND["stone"])

    # Palette cartographique
    fig.text(0.52, 0.225, "PALETTE CARTOGRAPHIQUE (climat, bivarié 4 × 4)", fontsize=8,
             fontweight="bold", color=BRAND["teal"])
    pal = bivar_palette()
    for ti in range(4):
        for pi in range(4):
            ax = fig.add_axes([0.52 + pi * 0.03, 0.04 + ti * 0.036, 0.028, 0.033])
            ax.set_axis_off()
            ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, facecolor=pal[(ti + 1) * 10 + pi + 1]))
    for i, c in enumerate(T_RAMP):
        ax = fig.add_axes([0.67, 0.04 + i * 0.036, 0.05, 0.033]); ax.set_axis_off()
        ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, facecolor=c))
    for i, c in enumerate(P_RAMP):
        ax = fig.add_axes([0.73, 0.04 + i * 0.036, 0.05, 0.033]); ax.set_axis_off()
        ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, facecolor=c))
    fig.text(0.67, 0.19, "Température", fontsize=7, color=BRAND["stone"])
    fig.text(0.73, 0.19, "Précipitations", fontsize=7, color=BRAND["stone"])
    fig.text(0.80, 0.12, "Le bivarié = produit (multiply)\ndes deux rampes : chaque couleur\n"
             "de la matrice se lit sur ses deux\naxes.", fontsize=7.5, color=BRAND["stone"], va="center")

    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"bukalab_charte_graphique.{ext}", dpi=300)
    plt.close(fig)
    print("Charte ->", OUT)


# Profil LinkedIn : photo ronde en bas à gauche → branding à droite (1584×396)
LINKEDIN_BANNER_SIZE = (1584, 396)
LINKEDIN_BANNER_LOGO_RECT = (0.48, 0.38, 0.50, 0.52)  # figure coords, logo + domaines à droite


def _linkedin_gradient(fig):
    """Fond sombre teal → encre (style bannière pro géospatial)."""
    w_px, h_px = LINKEDIN_BANNER_SIZE
    grad = np.linspace(0, 1, 256).reshape(1, -1)
    cmap = mpl.colors.LinearSegmentedColormap.from_list(
        "buka_banner", ["#0F2830", "#15212B", "#1A3D44"], N=256
    )
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(grad, aspect="auto", cmap=cmap, extent=(0, w_px, 0, h_px), origin="lower")
    ax.set_axis_off()
    return ax


def _linkedin_banner_motif(fig):
    """Décor gauche : grille carto + courbes de niveau (sans motif carré)."""
    ax = fig.add_axes([0.0, 0.0, 0.62, 1.0])
    ax.set_facecolor("none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Mailles de grille (géomatique / raster)
    step = 0.075
    for x in np.arange(-0.02, 0.72, step):
        ax.axvline(x, color=BRAND["lagoon"], alpha=0.07, lw=0.55, zorder=1)
    for y in np.arange(0.02, 0.98, step):
        ax.axhline(y, color=BRAND["lagoon"], alpha=0.06, lw=0.55, zorder=1)

    # Courbes de niveau stylisées (topo / MNT)
    xs = np.linspace(-0.05, 0.78, 240)
    for k, (y0, amp, freq, ph) in enumerate([
        (0.22, 0.045, 7.5, 0.0),
        (0.38, 0.038, 9.0, 1.1),
        (0.54, 0.032, 8.0, 2.0),
        (0.68, 0.028, 10.0, 0.6),
    ]):
        ys = y0 + amp * np.sin(xs * freq + ph)
        ax.plot(xs, ys, color="#4E9099", alpha=0.14 + 0.03 * k, lw=1.15, zorder=2)

    # Estompe vers la droite
    fade_w = 100
    fade = np.zeros((60, fade_w, 4))
    fade[..., :3] = 0.07
    fade[..., 3] = np.linspace(0.78, 0.0, fade_w)
    ax.imshow(fade, aspect="auto", extent=(0.35, 1.05, 0, 1), origin="lower", zorder=5)


def export_linkedin_banner():
    """Bannière LinkedIn 1584×396 — logo BukaLab à droite (photo de profil à gauche)."""
    w_px, h_px = LINKEDIN_BANNER_SIZE
    fig = plt.figure(figsize=(w_px / 100, h_px / 100), dpi=100)
    fig.patch.set_facecolor(BRAND["ink"])
    _linkedin_gradient(fig)
    _linkedin_banner_motif(fig)

    draw_logo(fig, list(LINKEDIN_BANNER_LOGO_RECT), variant="dark", tagline=False)
    d1 = "  ·  ".join(DOMAINS[:4]).upper()
    d2 = "  ·  ".join(DOMAINS[4:]).upper()
    fig.text(0.96, 0.21, d1, fontsize=11.2, color="#E8F0F2", ha="right", va="center", fontfamily=FONT)
    fig.text(0.96, 0.12, d2, fontsize=11.2, color="#E8F0F2", ha="right", va="center", fontfamily=FONT)

    import io

    for ext in ("png", "pdf"):
        path = OUT / f"bukalab_linkedin_banner_1584x396.{ext}"
        buf = io.BytesIO()
        fig.savefig(buf, format=ext, dpi=100, facecolor=BRAND["ink"])
        path.write_bytes(buf.getvalue())
    plt.close(fig)
    print("Bannière LinkedIn ->", OUT / "bukalab_linkedin_banner_1584x396.png")


def main():
    setup_rc()
    OUT.mkdir(parents=True, exist_ok=True)
    export_logos()
    export_business_card()
    export_brand_sheet()
    export_linkedin_banner()


if __name__ == "__main__":
    main()
