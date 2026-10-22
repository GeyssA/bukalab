"""
LinkedIn — document PDF = poster de base (une page, sans retouche).

  py export_poster_linkedin.py --poster output_france/publication/france_climat_poster_2025.png

Sortie à côté du poster :
  france_climat_YYYY_linkedin.pdf   (copie du PDF vectoriel si présent, sinon PNG → PDF)
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve().parent
DEFAULT_POSTER = BASE / "output_france" / "publication" / "france_climat_poster_2025.png"


def _linkedin_pdf_name(stem: str) -> str | None:
    m = re.search(r"(\d{4})", stem)
    year = m.group(1) if m else None
    if "france_climat" in stem and year:
        return f"france_climat_{year}_linkedin.pdf"
    if "herpeto" in stem.lower():
        return "corse_herpeto_linkedin.pdf"
    return f"{stem}_linkedin.pdf"


def export_linkedin_pdf(poster: Path) -> Path:
    if not poster.is_file():
        raise FileNotFoundError(poster)
    pub = poster.parent
    name = _linkedin_pdf_name(poster.stem)
    if not name:
        raise ValueError(f"Nom de sortie inconnu pour {poster.name}")
    out = pub / name

    vector = poster.with_suffix(".pdf")
    if vector.is_file():
        shutil.copy2(vector, out)
        print(f"OK (PDF poster) -> {out}")
        return out

    im = Image.open(poster).convert("RGB")
    im.save(out, "PDF", resolution=300.0)
    print(f"OK (PNG → PDF) -> {out}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poster", type=Path, default=DEFAULT_POSTER)
    args = ap.parse_args()
    export_linkedin_pdf(args.poster)


if __name__ == "__main__":
    main()
