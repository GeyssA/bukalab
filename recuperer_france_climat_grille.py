"""
Grille climat ERA5-Land France (Open-Meteo Archive) — multi-années.

Réutilise les mêmes points que france_climat_2025_grille.csv (lat/lon/elevation).
Reprise auto si le CSV annuel existe déjà.

Exemples :
  py recuperer_france_climat_grille.py --year 2015
  py recuperer_france_climat_grille.py --year 2015 --year 2016
  py recuperer_france_climat_grille.py --from 2015 --to 2024
  py recuperer_france_climat_grille.py --saison printemps_ete --year 2025 --year 2015
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE = Path(__file__).resolve().parent
REF_CSV = BASE / "france_climat_2025_grille.csv"
OUT_DIR = BASE / "output_france" / "grilles_annuelles"
CACHE_DIR = BASE / "output_france" / "_cache_openmeteo"

BATCH_SIZE = 10
PAUSE_ENTRE_LOTS = 15.0
MAX_RETRIES = 8
RATE_LIMIT_MAX_WAITS = 160  # 160 × 10 min ≈ 27 h, couvre un quota journalier
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Saisons : (début MM-DD, fin MM-DD, dossier de sortie)
SAISONS = {
    "annee": ("01-01", "12-31", BASE / "output_france" / "grilles_annuelles"),
    "printemps_ete": ("03-01", "08-31", BASE / "output_france" / "grilles_printemps_ete"),
}
SAISON = "annee"
SEUIL_CHAUD = 30.0


def load_ref_points() -> pd.DataFrame:
    if not REF_CSV.exists():
        raise FileNotFoundError(
            f"Grille de référence absente : {REF_CSV}\n"
            "Il faut d'abord france_climat_2025_grille.csv (même maillage pour toutes les années)."
        )
    df = pd.read_csv(REF_CSV)
    need = {"lat", "lon"}
    if not need.issubset(df.columns):
        raise ValueError(f"Colonnes manquantes dans {REF_CSV}: {need - set(df.columns)}")
    cols = ["lat", "lon"]
    if "elevation" in df.columns:
        cols.append("elevation")
    return df[cols].drop_duplicates(subset=["lat", "lon"]).reset_index(drop=True)


def out_dir() -> Path:
    d = SAISONS[SAISON][2]
    d.mkdir(parents=True, exist_ok=True)
    return d


def out_path(year: int) -> Path:
    return out_dir() / f"france_climat_{year}_grille.csv"


def fetch_batch(lats: list[float], lons: list[float], year: int) -> list[dict]:
    """Un lot Open-Meteo (plusieurs points)."""
    debut, fin, _ = SAISONS[SAISON]
    avec_tmax = SAISON != "annee"
    variables = "temperature_2m_mean,precipitation_sum" + (",temperature_2m_max" if avec_tmax else "")
    params = {
        "latitude": ",".join(f"{x:.4f}" for x in lats),
        "longitude": ",".join(f"{x:.4f}" for x in lons),
        "start_date": f"{year}-{debut}",
        "end_date": f"{year}-{fin}",
        "daily": variables,
        "timezone": "Europe/Paris",
    }
    last_err = None
    tentative = 0
    limites = 0
    while tentative < MAX_RETRIES:
        tentative += 1
        try:
            r = requests.get(ARCHIVE_URL, params=params, timeout=120)
            if r.status_code == 429:
                raise RuntimeError("rate limit exceeded")
            r.raise_for_status()
            data = r.json()
            # Open-Meteo renvoie un dict si 1 point, une liste si plusieurs
            items = data if isinstance(data, list) else [data]
            rows = []
            for i, item in enumerate(items):
                daily = item.get("daily") or {}
                t = daily.get("temperature_2m_mean") or []
                p = daily.get("precipitation_sum") or []
                t_valid = [x for x in t if x is not None]
                p_valid = [x for x in p if x is not None]
                if not t_valid or not p_valid:
                    continue
                row = {
                    "lat": float(lats[i]),
                    "lon": float(lons[i]),
                    f"temp_moyenne_{year}": float(np.mean(t_valid)),
                    f"precip_totale_{year}": float(np.sum(p_valid)),
                    "elevation": item.get("elevation"),
                }
                if avec_tmax:
                    tx = np.array([x for x in (daily.get("temperature_2m_max") or []) if x is not None])
                    if tx.size:
                        row[f"tmax_moyenne_{year}"] = float(tx.mean())
                        row[f"jours_30_{year}"] = int((tx >= SEUIL_CHAUD).sum())
                rows.append(row)
            return rows
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            server_down = any(c in msg for c in ("502", "503", "504", "bad gateway", "getaddrinfo"))
            if "limit" in msg or "rate" in msg or "429" in msg or server_down:
                # quotas Open-Meteo horaires / journaliers : on attend sans épuiser les essais
                limites += 1
                if limites > RATE_LIMIT_MAX_WAITS:
                    raise RuntimeError(f"Quota toujours dépassé après {limites} attentes") from e
                tentative -= 1
                attente = 600
            else:
                attente = 5 * tentative
            print(f"  tentative {tentative} echouee ({e}) -> pause {attente}s", flush=True)
            time.sleep(attente)
    raise RuntimeError(f"Lot abandonné après {MAX_RETRIES} essais : {last_err}")


def fetch_year(year: int) -> Path:
    points = load_ref_points()
    dest = out_path(year)
    tcol = f"temp_moyenne_{year}"
    pcol = f"precip_totale_{year}"

    done_keys: set[tuple[float, float]] = set()
    existing = pd.DataFrame()
    if dest.exists():
        existing = pd.read_csv(dest)
        if tcol in existing.columns and pcol in existing.columns:
            ok = existing.dropna(subset=[tcol, pcol])
            done_keys = {(round(r.lat, 4), round(r.lon, 4)) for r in ok.itertuples()}
            print(f"{year}: reprise - {len(done_keys)}/{len(points)} deja faits", flush=True)
        else:
            existing = pd.DataFrame()

    todo = []
    for r in points.itertuples(index=False):
        key = (round(float(r.lat), 4), round(float(r.lon), 4))
        if key not in done_keys:
            todo.append((float(r.lat), float(r.lon)))

    print(f"{year}: restants = {len(todo)} (maillage {len(points)} points)", flush=True)
    if not todo:
        print(f"{year}: deja complet -> {dest}", flush=True)
        return dest

    new_rows: list[dict] = []
    n_lots = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(todo), BATCH_SIZE):
        lot = todo[i : i + BATCH_SIZE]
        lot_idx = i // BATCH_SIZE + 1
        lats = [p[0] for p in lot]
        lons = [p[1] for p in lot]
        print(f"  Lot {lot_idx}/{n_lots} ({len(lot)} pts)...", flush=True)
        rows = fetch_batch(lats, lons, year)
        new_rows.extend(rows)
        # sauvegarde incrémentale
        part = pd.DataFrame(new_rows)
        if len(existing):
            merged = pd.concat([existing, part], ignore_index=True)
        else:
            merged = part
        merged = merged.drop_duplicates(subset=["lat", "lon"], keep="last")
        merged.to_csv(dest, index=False)
        time.sleep(PAUSE_ENTRE_LOTS)

    print(f"{year}: termine -> {dest} ({len(pd.read_csv(dest))} lignes)", flush=True)
    return dest


def compute_fixed_breaks_from_2025(n_classes: int = 4) -> dict:
    """
    Seuils FIGÉS pour l'animation multi-années.
    Calculés sur 2025 uniquement (référence de ta carte actuelle).
    """
    df = pd.read_csv(REF_CSV)
    t = df["temp_moyenne_2025"].dropna().values
    p = df["precip_totale_2025"].dropna().values
    qs = np.linspace(0, 1, n_classes + 1)[1:-1]  # seuils internes
    t_breaks = [float(np.quantile(t, q)) for q in qs]
    p_breaks = [float(np.quantile(p, q)) for q in qs]
    out = {
        "n_classes": n_classes,
        "reference_year": 2025,
        "method": "quantiles",
        "temp_breaks": t_breaks,
        "precip_breaks": p_breaks,
        "temp_min": float(np.min(t)),
        "temp_max": float(np.max(t)),
        "precip_min": float(np.min(p)),
        "precip_max": float(np.max(p)),
        "note": (
            "Pour une animation année→année, TOUTES les cartes doivent utiliser "
            "ces mêmes seuils (pas de requantiles par année). "
            "Mono T/P et bivarié doivent partager le même n_classes "
            "(4 → matrice 4×4 ; 5 → matrice 5×5)."
        ),
    }
    path = OUT_DIR / f"classes_fixes_{n_classes}x{n_classes}_ref2025.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    import json

    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Seuils figes -> {path}", flush=True)
    return out


def keep_awake() -> None:
    """Empêche la mise en veille de Windows tant que le processus tourne."""
    if os.name == "nt":
        import ctypes

        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


def main():
    keep_awake()
    ap = argparse.ArgumentParser(description="Extraction climat France Open-Meteo par année")
    ap.add_argument("--year", type=int, action="append", help="Année(s) à extraire")
    ap.add_argument("--from", dest="y_from", type=int, help="Début de plage")
    ap.add_argument("--to", dest="y_to", type=int, help="Fin de plage (incluse)")
    ap.add_argument(
        "--classes",
        type=int,
        default=4,
        choices=[3, 4, 5],
        help="Nb de classes pour seuils figés (défaut 4 = losange 4×4)",
    )
    ap.add_argument("--breaks-only", action="store_true", help="Ne calcule que les seuils figés")
    ap.add_argument("--saison", choices=sorted(SAISONS), default="annee",
                    help="annee (01/01–31/12) ou printemps_ete (01/03–31/08)")
    args = ap.parse_args()

    global SAISON
    SAISON = args.saison
    if SAISON != "annee":
        years = sorted(set((args.year or []) + (
            list(range(args.y_from, args.y_to + 1)) if args.y_from is not None and args.y_to is not None else []
        ))) or [2025]
        print(f"Saison {SAISON} - annees demandees : {years}", flush=True)
        for y in years:
            fetch_year(y)
        return

    if args.breaks_only or not (OUT_DIR / f"classes_fixes_{args.classes}x{args.classes}_ref2025.json").exists():
        compute_fixed_breaks_from_2025(args.classes)
    if args.breaks_only:
        return

    years: list[int] = []
    if args.year:
        years.extend(args.year)
    if args.y_from is not None and args.y_to is not None:
        years.extend(range(args.y_from, args.y_to + 1))
    if not years:
        years = [2015]

    years = sorted(set(years))
    print(f"Annees demandees : {years}", flush=True)
    for y in years:
        fetch_year(y)


if __name__ == "__main__":
    main()
