"""Utilitaires communs du projet."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from datetime import date

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logger(name: str = "cfr") -> logging.Logger:
    cfg = load_config()
    log_dir = ROOT / cfg["paths"]["logs"]
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8")
        sh = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        fh.setFormatter(fmt)
        sh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger


def ensure_dirs() -> None:
    cfg = load_config()
    for key in ("raw", "processed", "external", "figures", "maps", "tables", "logs"):
        (ROOT / cfg["paths"][key]).mkdir(parents=True, exist_ok=True)


def write_metadata(path: Path, meta: dict) -> None:
    meta = {**meta, "written": date.today().isoformat()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
