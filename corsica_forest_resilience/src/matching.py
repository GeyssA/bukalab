"""
Matching PNR vs hors-PNR et analyses statistiques.

Méthode : nearest-neighbour sur covariables standardisées (+ caliper).
Design observationnel — PAS une preuve causale automatique du statut PNR.

Note Windows : scipy.stats évité (DLL parfois bloquée) → bootstrap numpy.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd

from . import ROOT, load_config, setup_logger, write_metadata

log = setup_logger()

COVARS = [
    "elevation_m",
    "slope_deg",
    "aspect_sin",
    "aspect_cos",
    "summer_temp_mean",
    "annual_precip",
    "dist_coast_km",
]


def _prepare_matrix(df: pd.DataFrame, cols: list[str]) -> tuple[np.ndarray, pd.Index]:
    sub = df.dropna(subset=cols).copy()
    X = sub[cols].astype(float).values
    mu = X.mean(axis=0)
    sd = X.std(axis=0) + 1e-6
    Z = (X - mu) / sd
    return Z, sub.index


def mahalanobis_match(
    grid: gpd.GeoDataFrame | pd.DataFrame,
    treatment_col: str = "in_pnr",
    covars: list[str] | None = None,
    caliper: float = 0.5,
) -> pd.DataFrame:
    cfg = load_config()
    covars = list(covars or [c for c in COVARS if c in grid.columns])
    df = pd.DataFrame(grid).copy()
    if "forest_type_group" in df.columns:
        dummies = pd.get_dummies(df["forest_type_group"], prefix="ft")
        for c in dummies.columns:
            df[c] = dummies[c]
            covars.append(c)

    treat = df.loc[df[treatment_col] == 1]
    ctrl = df.loc[df[treatment_col] == 0]
    Zt, idx_t = _prepare_matrix(treat, covars)
    Zc, idx_c = _prepare_matrix(ctrl, covars)
    if len(Zt) == 0 or len(Zc) == 0:
        raise RuntimeError("Pas assez d'unités pour matching")

    t2 = np.sum(Zt**2, axis=1)[:, None]
    c2 = np.sum(Zc**2, axis=1)[None, :]
    D = np.sqrt(np.maximum(t2 + c2 - 2 * Zt @ Zc.T, 0))

    pairs = []
    used = set()
    cal = caliper * np.sqrt(len(covars))
    for i in range(len(Zt)):
        for j in np.argsort(D[i]):
            if j in used:
                continue
            if D[i, j] <= cal:
                pairs.append(
                    {
                        "treat_idx": idx_t[i],
                        "ctrl_idx": idx_c[j],
                        "distance": float(D[i, j]),
                        "treat_cell": treat.loc[idx_t[i], "cell_id"]
                        if "cell_id" in treat.columns
                        else idx_t[i],
                        "ctrl_cell": ctrl.loc[idx_c[j], "cell_id"]
                        if "cell_id" in ctrl.columns
                        else idx_c[j],
                    }
                )
                used.add(j)
                break

    pairs_df = pd.DataFrame(pairs)
    log.info("Paires matchées: %d / %d traités", len(pairs_df), len(treat))
    bal_rows = []
    for c in covars:
        if c not in treat.columns or pairs_df.empty:
            continue
        mt = treat.loc[pairs_df["treat_idx"], c].astype(float)
        mc = ctrl.loc[pairs_df["ctrl_idx"], c].astype(float)
        smd = (mt.mean() - mc.mean()) / (np.sqrt((mt.var() + mc.var()) / 2) + 1e-6)
        bal_rows.append(
            {
                "covariate": c,
                "smd_matched": float(smd),
                "mean_t": float(mt.mean()),
                "mean_c": float(mc.mean()),
            }
        )
    balance = pd.DataFrame(bal_rows)

    out_dir = ROOT / cfg["paths"]["tables"]
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs_df.to_csv(out_dir / "matched_pairs.csv", index=False)
    balance.to_csv(out_dir / "covariate_balance.csv", index=False)
    write_metadata(
        out_dir / "matching.meta.json",
        {
            "method": "nearest_neighbor_euclidean_on_standardized_covars",
            "caliper_rule": f"{caliper} * sqrt(p)",
            "covars": covars,
            "n_pairs": len(pairs_df),
            "causal_claim": "NOT causal",
        },
    )
    return pairs_df


def compare_outcomes(
    metrics: pd.DataFrame,
    pairs: pd.DataFrame,
    grid: pd.DataFrame,
) -> pd.DataFrame:
    cfg = load_config()
    results = []
    rng = np.random.default_rng(42)
    for var, g in metrics.groupby("variable"):
        m = g.set_index("cell_id")
        for outcome in ("trend_slope", "anomaly_mean", "cv", "recovery_years", "mean_level"):
            if outcome not in m.columns:
                continue
            diffs = []
            for _, row in pairs.iterrows():
                a = m.loc[row["treat_cell"], outcome] if row["treat_cell"] in m.index else np.nan
                b = m.loc[row["ctrl_cell"], outcome] if row["ctrl_cell"] in m.index else np.nan
                if np.isfinite(a) and np.isfinite(b):
                    diffs.append(a - b)
            diffs = np.array(diffs, dtype=float)
            if len(diffs) < 10:
                continue
            boots = [
                diffs[rng.integers(0, len(diffs), len(diffs))].mean()
                for _ in range(cfg["statistics"]["bootstrap_n"])
            ]
            p_sign = 2 * min((diffs > 0).mean(), (diffs < 0).mean())
            results.append(
                {
                    "variable": var,
                    "outcome": outcome,
                    "n_pairs": len(diffs),
                    "mean_diff_pnr_minus_ctrl": float(diffs.mean()),
                    "median_diff": float(np.median(diffs)),
                    "sign_test_p": float(p_sign),
                    "ci95_low": float(np.percentile(boots, 2.5)),
                    "ci95_high": float(np.percentile(boots, 97.5)),
                }
            )
    res = pd.DataFrame(results)
    path = ROOT / cfg["paths"]["tables"] / "matched_outcome_tests.csv"
    res.to_csv(path, index=False)
    log.info("Tests → %s", path)
    return res


def naive_vs_matched_means(metrics: pd.DataFrame, grid: pd.DataFrame) -> pd.DataFrame:
    cfg = load_config()
    g = grid.set_index("cell_id")[["in_pnr"]]
    m = metrics.merge(g, left_on="cell_id", right_index=True, how="inner")
    rows = []
    for var in m["variable"].unique():
        sub = m.loc[m["variable"] == var]
        for outcome in ("trend_slope", "mean_level", "cv"):
            if outcome not in sub.columns:
                continue
            a = sub.loc[sub["in_pnr"] == 1, outcome].dropna()
            b = sub.loc[sub["in_pnr"] == 0, outcome].dropna()
            if len(a) < 5 or len(b) < 5:
                continue
            rows.append(
                {
                    "variable": var,
                    "outcome": outcome,
                    "mean_pnr_naive": float(a.mean()),
                    "mean_out_naive": float(b.mean()),
                    "diff_naive": float(a.mean() - b.mean()),
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / cfg["paths"]["tables"] / "naive_means.csv", index=False)
    return out


if __name__ == "__main__":
    cfg = load_config()
    grid = gpd.read_file(ROOT / cfg["paths"]["processed"] / "forest_grid_1km.gpkg")
    mahalanobis_match(grid)
    metrics_path = ROOT / cfg["paths"]["processed"] / "trajectory_metrics.csv"
    if metrics_path.exists():
        metrics = pd.read_csv(metrics_path)
        pairs = pd.read_csv(ROOT / cfg["paths"]["tables"] / "matched_pairs.csv")
        compare_outcomes(metrics, pairs, grid)
        naive_vs_matched_means(metrics, grid)
    else:
        log.warning("Pas de trajectory_metrics.csv — matching covariables seul")
