"""
Poster « Amphibiens et reptiles de Corse » — rebranding BukaLab (publication).

Repose sur le visuel HerpétoLab existant (PNG) : remplacement minimal du branding
pour l’aligner sur france_climat_poster_2025 (même pied de page, logo, filet teal).

  py rebrand_poster_herpeto_bukalab.py

Entrée : assets/…poster_herpetolab….png (ou --source)
Sorties : output_corse/publication/
  corse_herpeto_poster_bukalab.png / .pdf  (A3 paysage, 300 dpi)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

BASE = Path(__file__).resolve().parent
_WS_ASSETS = Path(
    r"C:\Users\arnau\.cursor\projects\c-Users-arnau-Documents-DEV-CODE-CARTOGRAPHIES-ANALYSES-CARTES\assets"
)


def _find_source() -> Path | None:
    for root in (BASE / "assets", _WS_ASSETS):
        if root.is_dir():
            hits = sorted(root.glob("*herpetolab*.png"))
            if hits:
                return hits[-1]
    return None


DEFAULT_SRC = _find_source()

OUT = BASE / "output_corse" / "publication"

FIG_W, FIG_H = 16.54, 11.69  # A3 paysage (comme render_france_animation.py)
DPI = 300

RULE = "#D5DADE"


def load_rgb(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"))


def scrub_herpeto_branding(img: np.ndarray) -> np.ndarray:
    """Efface HerpétoLab sur le raster source (coordonnées px du PNG fourni)."""
    out = img.copy()
    h, w = out.shape[:2]
    sx, sy = w / 1024, h / 724

    def white(y0, y1, x0, x1):
        y0, y1 = int(y0 * sy), int(y1 * sy)
        x0, x1 = int(x0 * sx), int(x1 * sx)
        out[y0:y1, x0:x1] = 255

    # Bloc logo + wordmark HerpétoLab (sans toucher au titre à droite)
    white(0, 118, 0, 272)
    # Ligne « HerpétoLab · CEN Corse · … » en bas à droite
    white(676, 696, 638, 1024)
    # Bandeau bas BukaLab (conserve les mentions sources au-dessus)
    white(698, 724, 0, 1024)
    return out


def rebrand(source: Path, dpi: int = DPI) -> tuple[Path, Path]:
    from bukalab_identity import BRAND, DOMAINS, draw_logo, draw_mark, setup_rc

    setup_rc()
    img = scrub_herpeto_branding(load_rgb(source))

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=dpi)
    fig.patch.set_facecolor("white")

    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(img, aspect="auto", zorder=0)
    ax.set_axis_off()

    # Filet sous l’en-tête (≈ 118 px sur le PNG source)
    y_rule = 1 - (118 / 724)
    fig.add_artist(plt.Line2D([0.035, 0.965], [y_rule, y_rule], color=BRAND["teal"], lw=1.2, zorder=6))

    # Logo BukaLab — même emplacement relatif que l’ancien bloc HerpétoLab
    draw_logo(fig, [0.032, 0.915, 0.165, 0.048], variant="light", tagline=False)

    fig.text(
        0.032, y_rule + 0.008,
        "AMPHIBIENS · REPTILES · CORSE",
        fontsize=7.0, color=BRAND["stone"], va="bottom", ha="left", zorder=8,
    )

    # Pied de page (identique à france_climat_poster_2025, + partenaire CEN)
    fig.add_artist(plt.Line2D([0.035, 0.965], [0.05, 0.05], color=RULE, lw=0.8, zorder=3))
    fig.text(
        0.035, 0.032,
        "Données : compilations CEN Corse, INPN, UICN ; cartographie des mailles et statuts — voir mentions en bas de figure.",
        fontsize=7.5, color=BRAND["stone"], va="center", zorder=4,
    )
    fig.text(
        0.035, 0.016,
        "Conception, traitement et cartographie : Arnaud Geyssels — BukaLab · en partenariat avec le CEN Corse, 2026.",
        fontsize=7.5, color=BRAND["stone"], va="center", zorder=4,
    )
    fig.text(0.965, 0.032, "BukaLab", fontsize=9, fontweight="bold", color=BRAND["teal"],
             ha="right", va="center", zorder=4)
    fig.text(
        0.965, 0.016,
        "  ·  ".join(DOMAINS),
        fontsize=6.8, color=BRAND["stone"], ha="right", va="center", zorder=4,
    )
    mark_ax = fig.add_axes([0.919, 0.0245, 0.009, 0.016])
    mark_ax.set_axis_off()
    mark_ax.set_xlim(-1, 1)
    mark_ax.set_ylim(-1, 1)
    mark_ax.set_aspect("equal")
    draw_mark(mark_ax, 0, 0, 0.95)

    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / "corse_herpeto_poster_bukalab.png"
    pdf = OUT / "corse_herpeto_poster_bukalab.pdf"
    fig.savefig(png, dpi=dpi, facecolor="white")
    fig.savefig(pdf, facecolor="white")
    plt.close(fig)
    print(f"OK -> {png}\n     {pdf}")
    return png, pdf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=DEFAULT_SRC, help="PNG source HerpétoLab")
    ap.add_argument("--dpi", type=int, default=DPI)
    args = ap.parse_args()
    if args.source is None or not args.source.is_file():
        raise SystemExit("PNG source introuvable — passe --source chemin/vers/poster.png")
    rebrand(args.source, dpi=args.dpi)


if __name__ == "__main__":
    main()
