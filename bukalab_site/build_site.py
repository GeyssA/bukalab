"""
Assemble le site statique BukaLab (logos + cartes de publication).

  py bukalab_site/build_site.py

Pour publier une nouvelle carte : ajouter une entrée dans SOURCES.
Les entrées dont le PNG est absent sont ignorées silencieusement.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
ASSETS = ROOT / "assets"
CARTES = ASSETS / "cartes"
IDENT = BASE / "bukalab_identity"

LOGOS = ("bukalab_logo.svg", "bukalab_logo_dark.svg", "bukalab_mark.svg", "bukalab_logo_simple.svg", "bukalab_logo_plain.svg")

SOURCES = [
    {
        "id": "france-climat-2025",
        "slug": "france_climat_2025",
        "src": BASE / "output_france" / "publication" / "france_climat_poster_2025",
        "title": "Température et précipitations annuelles — France, 2025",
        "subtitle": "Synthèse bivariée ERA5-Land · seuils fixes (quartiles 2025)",
        "year": 2025,
        "tags": ["climat", "France"],
    },
    {
        "id": "corse-herpeto-2025",
        "slug": "corse_herpeto_2025",
        "src": BASE / "output_corse" / "publication" / "corse_herpeto_poster_bukalab",
        "title": "Amphibiens et reptiles de Corse",
        "subtitle": "État des connaissances 2000-2025 · richesse spécifique, statuts et phénologie des 18 espèces",
        "year": 2025,
        "tags": ["faune", "Corse"],
    },
]


def _thumb(src: Path, dest: Path, width: int = 1600) -> None:
    im = Image.open(src).convert("RGB")
    if im.width > width:
        h = int(im.height * width / im.width)
        im = im.resize((width, h), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=88, optimize=True)


def _copy(src: Path, dest: Path) -> None:
    if not src.is_file():
        raise FileNotFoundError(src)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def build_entry(spec: dict) -> dict | None:
    png, pdf = spec["src"].with_suffix(".png"), spec["src"].with_suffix(".pdf")
    if not png.is_file():
        print(f"  ! ignoré (PNG absent) : {png.name}")
        return None

    slug = spec["slug"]
    _copy(png, CARTES / f"{slug}.png")
    _thumb(png, CARTES / f"{slug}_thumb.jpg")
    if pdf.is_file():
        _copy(pdf, CARTES / f"{slug}.pdf")

    with Image.open(png) as im:
        width, height = im.size

    return {
        "id": spec["id"],
        "title": spec["title"],
        "subtitle": spec["subtitle"],
        "image": f"assets/cartes/{slug}.png",
        "pdf": f"assets/cartes/{slug}.pdf" if pdf.is_file() else None,
        "thumb": f"assets/cartes/{slug}_thumb.jpg",
        "width": width,
        "height": height,
        "year": spec["year"],
        "tags": spec["tags"],
    }


def main() -> None:
    CARTES.mkdir(parents=True, exist_ok=True)
    for name in LOGOS:
        _copy(IDENT / name, ASSETS / name)

    catalog = [e for e in (build_entry(s) for s in SOURCES) if e]

    cat_json = json.dumps(catalog, ensure_ascii=False, indent=2)
    (ROOT / "cartographies.json").write_text(cat_json, encoding="utf-8")
    (ROOT / "js" / "catalog.js").write_text(f"window.BUKALAB_CARTO = {cat_json};\n", encoding="utf-8")

    print(f"Site prêt — {len(catalog)} carte(s)")
    for c in catalog:
        print(f"  · {c['id']} ({c['width']}×{c['height']}){' + PDF' if c['pdf'] else ''}")


if __name__ == "__main__":
    main()
