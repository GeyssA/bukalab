"""
Figures digne de publication (style revue EO / Remote Sensing).

Génère PNG 300 dpi + PDF vectoriel.
Palette : vert forêt / ocre — pas de dégradés « IA » violets.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, Normalize
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle, FancyArrowPatch
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
import matplotlib.font_manager as fm

from . import ROOT, load_config, setup_logger

log = setup_logger()

# --- style publication ---
mpl.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 9,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)

# Couleurs scientifiques (print-friendly)
C_PNR = "#1B5E4A"       # vert sombre
C_OUT = "#C47B3A"       # ocre
C_SEA = "#E8EEF2"       # fond mer très clair
C_LAND = "#F7F5F1"      # fond terre
C_COAST = "#2C3E50"     # trait de côte
C_PNR_LINE = "#0D3B2E"
C_GRID = "#D5D8DC"

TYPE_COLORS = {
    "broadleaf": "#2E7D4F",
    "conifer": "#1A4D6D",
    "mixed": "#5B8C5A",
    "other": "#8D6E4C",
}
TYPE_LABELS = {
    "broadleaf": "Feuillus",
    "conifer": "Conifères",
    "mixed": "Mixtes",
    "other": "Autres (ouverts / divers)",
}


def _fig_dir() -> Path:
    d = ROOT / load_config()["paths"]["figures"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save(fig: plt.Figure, name: str) -> Path:
    out = _fig_dir()
    png = out / f"{name}.png"
    pdf = out / f"{name}.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight", pad_inches=0.15)
    fig.savefig(pdf, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    log.info("Figure → %s", png.name)
    return png


def _add_scalebar(ax, length_m: float = 20000, label: str = "20 km"):
    scalebar = AnchoredSizeBar(
        ax.transData,
        length_m,
        label,
        "lower left",
        pad=0.4,
        color=C_COAST,
        frameon=False,
        size_vertical=length_m * 0.015,
        fontproperties=fm.FontProperties(size=8),
    )
    ax.add_artist(scalebar)


def _add_north(ax, x_frac=0.92, y_frac=0.92):
    """Flèche nord discrète en coordonnées axes."""
    ax.annotate(
        "N",
        xy=(x_frac, y_frac - 0.06),
        xytext=(x_frac, y_frac),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold",
        color=C_COAST,
        arrowprops=dict(arrowstyle="-|>", color=C_COAST, lw=1.2),
    )


def _panel_label(ax, label: str):
    ax.text(
        0.02,
        0.98,
        label,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=12,
        fontweight="bold",
        color=C_COAST,
        bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none", alpha=0.85),
    )


def _basemap(ax, region: gpd.GeoDataFrame, pnr: gpd.GeoDataFrame):
    """Fond carte : mer claire + terre + côte + PNR."""
    xmin, ymin, xmax, ymax = region.total_bounds
    pad = 8000
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_facecolor(C_SEA)
    region.plot(ax=ax, color=C_LAND, edgecolor="none", zorder=1)
    region.boundary.plot(ax=ax, color=C_COAST, linewidth=0.9, zorder=5)
    pnr.plot(ax=ax, facecolor="#1B5E4A18", edgecolor=C_PNR_LINE, linewidth=1.4, zorder=4)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def fig_study_area(grid: gpd.GeoDataFrame, pnr: gpd.GeoDataFrame, region: gpd.GeoDataFrame) -> Path:
    """Carte de localisation : forêts PNR / hors PNR."""
    region = region.to_crs(grid.crs)
    pnr = pnr.to_crs(grid.crs)

    fig, ax = plt.subplots(figsize=(7.2, 9.0))
    _basemap(ax, region, pnr)

    g0 = grid.loc[grid["in_pnr"] == 0]
    g1 = grid.loc[grid["in_pnr"] == 1]
    g0.plot(ax=ax, color=C_OUT, edgecolor="none", linewidth=0, alpha=0.92, zorder=2)
    g1.plot(ax=ax, color=C_PNR, edgecolor="none", linewidth=0, alpha=0.88, zorder=3)

    _add_scalebar(ax)
    _add_north(ax)
    _panel_label(ax, "a")

    legend_elements = [
        Patch(facecolor=C_PNR, edgecolor="none", label=f"Forêt dans le PNR (n={len(g1):,})"),
        Patch(facecolor=C_OUT, edgecolor="none", label=f"Forêt hors PNR (n={len(g0):,})"),
        Patch(facecolor="none", edgecolor=C_PNR_LINE, linewidth=1.4, label="Limite du PNR"),
        Line2D([0], [0], color=C_COAST, lw=0.9, label="Littoral"),
    ]
    leg = ax.legend(
        handles=legend_elements,
        loc="upper left",
        bbox_to_anchor=(0.02, 0.88),
        fontsize=8,
        handlelength=1.2,
        handleheight=1.0,
    )
    leg.get_frame().set_linewidth(0)

    ax.set_title(
        "Répartition des forêts étudiées et Parc naturel régional de Corse",
        fontsize=11,
        pad=10,
        color=C_COAST,
    )
    fig.text(
        0.5,
        0.02,
        "Grille d'analyse 1 km · fraction forestière ≥ 60 % · BD Forêt IGN v2 (FF/FO) · PNR : FPNRF 2024 · SCR : EPSG:2154",
        ha="center",
        fontsize=7,
        color="0.35",
    )
    return _save(fig, "fig01_study_area")


def fig_forest_types(grid: gpd.GeoDataFrame, pnr: gpd.GeoDataFrame, region: gpd.GeoDataFrame) -> Path:
    region = region.to_crs(grid.crs)
    pnr = pnr.to_crs(grid.crs)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 7.2), gridspec_kw={"width_ratios": [1.15, 0.85]})

    # carte
    ax = axes[0]
    _basemap(ax, region, pnr)
    for key, color in TYPE_COLORS.items():
        sub = grid.loc[grid["forest_type_group"] == key]
        if len(sub):
            sub.plot(ax=ax, color=color, edgecolor="none", linewidth=0, zorder=2)
    _add_scalebar(ax, 20000, "20 km")
    _add_north(ax)
    _panel_label(ax, "a")
    ax.set_title("Types forestiers dominants (BD Forêt v2)", color=C_COAST, pad=8)
    handles = [Patch(facecolor=TYPE_COLORS[k], label=TYPE_LABELS[k]) for k in TYPE_COLORS]
    handles.append(Patch(facecolor="none", edgecolor=C_PNR_LINE, linewidth=1.3, label="PNR"))
    ax.legend(handles=handles, loc="lower left", fontsize=7.5)

    # barres empilées PNR vs hors
    ax2 = axes[1]
    counts = (
        grid.groupby(["in_pnr", "forest_type_group"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=list(TYPE_COLORS.keys()), fill_value=0)
    )
    # proportions
    props = counts.div(counts.sum(axis=1), axis=0) * 100
    x = np.array([0, 1])
    labels = ["Hors PNR", "PNR"]
    bottom = np.zeros(2)
    for key in TYPE_COLORS:
        vals = [props.loc[0, key] if 0 in props.index else 0, props.loc[1, key] if 1 in props.index else 0]
        ax2.bar(
            x,
            vals,
            bottom=bottom,
            color=TYPE_COLORS[key],
            width=0.55,
            label=TYPE_LABELS[key],
            edgecolor="white",
            linewidth=0.4,
        )
        bottom += vals
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("Part des cellules forestières (%)")
    ax2.set_ylim(0, 100)
    ax2.set_title("Composition relative PNR / hors PNR", color=C_COAST, pad=8)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.legend(loc="upper right", fontsize=7.5, bbox_to_anchor=(1.0, 1.0))
    _panel_label(ax2, "b")
    # n=
    n0 = int((grid["in_pnr"] == 0).sum())
    n1 = int((grid["in_pnr"] == 1).sum())
    ax2.text(0, -8, f"n = {n0:,}", ha="center", fontsize=7, color="0.4")
    ax2.text(1, -8, f"n = {n1:,}", ha="center", fontsize=7, color="0.4")

    fig.suptitle(
        "Structure des peuplements dans l'échantillon d'analyse",
        fontsize=12,
        color=C_COAST,
        y=0.98,
    )
    fig.text(
        0.5,
        0.01,
        "Groupe dominant par cellule (surface BD Forêt) · Sources : IGN BD Forêt v2 ; FPNRF",
        ha="center",
        fontsize=7,
        color="0.35",
    )
    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    return _save(fig, "fig02_forest_types")


def fig_elevation_context(grid: gpd.GeoDataFrame, pnr: gpd.GeoDataFrame, region: gpd.GeoDataFrame) -> Path:
    region = region.to_crs(grid.crs)
    pnr = pnr.to_crs(grid.crs)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 7.0))

    ax = axes[0]
    _basemap(ax, region, pnr)
    vmin, vmax = 0, float(np.nanpercentile(grid["elevation_m"], 98))
    grid.plot(
        column="elevation_m",
        ax=ax,
        cmap="cividis",
        linewidth=0,
        edgecolor="none",
        vmin=vmin,
        vmax=vmax,
        legend=True,
        legend_kwds={
            "label": "Altitude (m)",
            "shrink": 0.55,
            "pad": 0.02,
            "orientation": "vertical",
        },
        zorder=2,
    )
    _add_scalebar(ax)
    _add_north(ax)
    _panel_label(ax, "a")
    ax.set_title("Altitude des cellules forestières", color=C_COAST)

    ax2 = axes[1]
    data = [
        grid.loc[grid["in_pnr"] == 0, "elevation_m"].dropna(),
        grid.loc[grid["in_pnr"] == 1, "elevation_m"].dropna(),
    ]
    parts = ax2.violinplot(data, positions=[0, 1], showmeans=False, showmedians=True, showextrema=False)
    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor([C_OUT, C_PNR][i])
        pc.set_alpha(0.85)
        pc.set_edgecolor("white")
    parts["cmedians"].set_color(C_COAST)
    parts["cmedians"].set_linewidth(1.2)
    # box overlay léger
    bp = ax2.boxplot(
        data,
        positions=[0, 1],
        widths=0.12,
        patch_artist=True,
        showfliers=False,
        medianprops=dict(color="white", linewidth=1.2),
        boxprops=dict(facecolor=C_COAST, edgecolor="none", alpha=0.85),
        whiskerprops=dict(color=C_COAST, linewidth=0.8),
        capprops=dict(color=C_COAST, linewidth=0.8),
    )
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["Hors PNR", "PNR"])
    ax2.set_ylabel("Altitude (m)")
    ax2.set_title("Distribution altitudinale", color=C_COAST)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    _panel_label(ax2, "b")
    # annotate medians
    for i, d in enumerate(data):
        ax2.text(i, d.median() + 40, f"méd. {d.median():.0f} m", ha="center", fontsize=7.5, color=C_COAST)

    fig.suptitle(
        "Contexte topographique : pourquoi un matching est nécessaire",
        fontsize=12,
        color=C_COAST,
        y=0.98,
    )
    fig.text(
        0.5,
        0.01,
        "Altitude : ERA5-Land / Open-Meteo (centroïdes) · Les forêts du PNR sont nettement plus élevées en moyenne",
        ha="center",
        fontsize=7,
        color="0.35",
    )
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    return _save(fig, "fig03_elevation")


def fig_covariates(grid: gpd.GeoDataFrame, balance_csv: Path | None = None) -> Path:
    """Distributions jointes + équilibre après matching."""
    specs = [
        ("elevation_m", "Altitude (m)"),
        ("summer_temp_mean", "Température moyenne 2025 (°C)"),
        ("annual_precip", "Précipitations 2025 (mm)"),
        ("dist_coast_km", "Distance à la côte (km)"),
    ]
    specs = [(c, lab) for c, lab in specs if c in grid.columns]

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.2))
    axes = axes.ravel()
    for ax, (col, lab) in zip(axes, specs):
        for flag, color, name in [(0, C_OUT, "Hors PNR"), (1, C_PNR, "PNR")]:
            vals = grid.loc[grid["in_pnr"] == flag, col].dropna()
            ax.hist(
                vals,
                bins=35,
                density=True,
                histtype="stepfilled",
                alpha=0.35,
                color=color,
                edgecolor=color,
                linewidth=1.1,
                label=name,
            )
        ax.set_xlabel(lab)
        ax.set_ylabel("Densité")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(fontsize=7.5, loc="upper right")
    for i, ax in enumerate(axes):
        _panel_label(ax, chr(ord("a") + i))

    fig.suptitle(
        "Distributions des covariables avant matching (PNR vs hors PNR)",
        fontsize=12,
        color=C_COAST,
        y=0.995,
    )
    fig.text(
        0.5,
        0.005,
        "Chevauchement incomplet → risque de biais si comparaison naïve des moyennes satellitaires",
        ha="center",
        fontsize=7.5,
        color="0.35",
        style="italic",
    )
    fig.tight_layout(rect=[0, 0.03, 1, 0.97])
    path = _save(fig, "fig04_covariate_distributions")

    # Balance SMD
    if balance_csv and Path(balance_csv).exists():
        bal = pd.read_csv(balance_csv)
        # garder covariables continues principales
        keep = [
            c
            for c in [
                "elevation_m",
                "slope_deg",
                "summer_temp_mean",
                "annual_precip",
                "dist_coast_km",
                "aspect_sin",
                "aspect_cos",
            ]
            if c in set(bal["covariate"])
        ]
        bal = bal.loc[bal["covariate"].isin(keep)].copy()
        labels_map = {
            "elevation_m": "Altitude",
            "slope_deg": "Pente",
            "summer_temp_mean": "Température",
            "annual_precip": "Précipitations",
            "dist_coast_km": "Distance côte",
            "aspect_sin": "Aspect (sin)",
            "aspect_cos": "Aspect (cos)",
        }
        bal["label"] = bal["covariate"].map(labels_map)
        bal = bal.sort_values("smd_matched")

        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        y = np.arange(len(bal))
        colors = [C_PNR if abs(v) <= 0.1 else ("#B85C38" if abs(v) <= 0.25 else "#8B1E1E") for v in bal["smd_matched"]]
        ax.axvspan(-0.1, 0.1, color="#1B5E4A22", zorder=0)
        ax.axvline(0, color=C_COAST, lw=0.8)
        ax.axvline(-0.1, color="0.55", ls="--", lw=0.7)
        ax.axvline(0.1, color="0.55", ls="--", lw=0.7)
        ax.scatter(bal["smd_matched"], y, c=colors, s=55, zorder=3, edgecolors="white", linewidths=0.4)
        ax.hlines(y, 0, bal["smd_matched"], color="0.75", lw=0.8, zorder=2)
        ax.set_yticks(y)
        ax.set_yticklabels(bal["label"])
        ax.set_xlabel("Différence de moyennes standardisée (SMD) après matching")
        ax.set_title("Équilibre des covariables — paires appariées", color=C_COAST)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        # légende SMD
        leg_el = [
            Line2D([0], [0], marker="o", color="w", markerfacecolor=C_PNR, markersize=8, label="|SMD| ≤ 0,10 (bon)"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="#B85C38", markersize=8, label="0,10 < |SMD| ≤ 0,25"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="#8B1E1E", markersize=8, label="|SMD| > 0,25 (faible)"),
        ]
        ax.legend(handles=leg_el, loc="lower right", fontsize=7.5)
        n_pairs = None
        pairs_path = ROOT / load_config()["paths"]["tables"] / "matched_pairs.csv"
        if pairs_path.exists():
            n_pairs = len(pd.read_csv(pairs_path))
        note = f"Bande verte = seuil usuel |SMD|≤0,1"
        if n_pairs:
            note += f" · {n_pairs:,} paires matchées"
        fig.text(0.5, 0.01, note, ha="center", fontsize=7, color="0.35")
        fig.tight_layout(rect=[0, 0.04, 1, 1])
        _save(fig, "fig05_matching_balance")

    return path


def fig_sample_design(grid: gpd.GeoDataFrame, pnr: gpd.GeoDataFrame, region: gpd.GeoDataFrame) -> Path:
    """Synthèse du design : fraction forestière + comptages."""
    region = region.to_crs(grid.crs)
    pnr = pnr.to_crs(grid.crs)
    fig = plt.figure(figsize=(11.5, 7.0))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.2, 0.9], wspace=0.28)

    ax = fig.add_subplot(gs[0])
    _basemap(ax, region, pnr)
    grid.plot(
        column="forest_fraction",
        ax=ax,
        cmap="YlGn",
        linewidth=0,
        edgecolor="none",
        vmin=0.6,
        vmax=1.0,
        legend=True,
        legend_kwds={"label": "Fraction forestière", "shrink": 0.55, "pad": 0.02},
        zorder=2,
    )
    _add_scalebar(ax)
    _add_north(ax)
    _panel_label(ax, "a")
    ax.set_title("Densité forestière dans la grille d'analyse", color=C_COAST)

    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis("off")
    _panel_label(ax2, "b")

    stats = [
        ("Cellules 1 km (≥ 60 % forêt)", f"{len(grid):,}"),
        ("Dans le PNR", f"{int((grid.in_pnr==1).sum()):,}"),
        ("Hors PNR", f"{int((grid.in_pnr==0).sum()):,}"),
        ("Paires matchées", "—"),
    ]
    pairs_path = ROOT / load_config()["paths"]["tables"] / "matched_pairs.csv"
    if pairs_path.exists():
        stats[3] = ("Paires matchées (1:1)", f"{len(pd.read_csv(pairs_path)):,}")

    y = 0.88
    ax2.text(0.0, 0.95, "Design d'échantillonnage", fontsize=12, fontweight="bold", color=C_COAST, transform=ax2.transAxes)
    for label, val in stats:
        ax2.text(0.0, y, label, fontsize=9, color="0.35", transform=ax2.transAxes)
        ax2.text(1.0, y, val, fontsize=14, fontweight="bold", color=C_PNR, ha="right", transform=ax2.transAxes)
        y -= 0.12

    ax2.text(
        0.0,
        0.28,
        "Unité d'analyse\nCellule carrée 1 × 1 km en Lambert-93,\nretenue si ≥ 60 % de couverture BD Forêt\n(codes FF/FO). Agrégation destinée à\nréduire le bruit SCL / pixels mixtes.",
        fontsize=8,
        color="0.3",
        transform=ax2.transAxes,
        linespacing=1.45,
        va="top",
    )
    ax2.text(
        0.0,
        0.02,
        "Sources : IGN BD Forêt v2 · FPNRF/INPN · EPSG:2154",
        fontsize=7,
        color="0.45",
        transform=ax2.transAxes,
    )

    fig.suptitle(
        "Échantillon forestier pour la comparaison PNR / hors PNR",
        fontsize=12,
        color=C_COAST,
        y=0.98,
    )
    return _save(fig, "fig00_sample_design")


def make_all_publication_figures() -> list[Path]:
    cfg = load_config()
    grid = gpd.read_file(ROOT / cfg["paths"]["processed"] / "forest_grid_1km.gpkg")
    pnr = gpd.read_file(ROOT / cfg["paths"]["processed"] / "pnr_corse.gpkg")
    region = gpd.read_file(ROOT / cfg["paths"]["raw"] / "admin" / "region-corse.geojson").to_crs(grid.crs)
    bal = ROOT / cfg["paths"]["tables"] / "covariate_balance.csv"

    paths = []
    paths.append(fig_sample_design(grid, pnr, region))
    paths.append(fig_study_area(grid, pnr, region))
    paths.append(fig_forest_types(grid, pnr, region))
    paths.append(fig_elevation_context(grid, pnr, region))
    paths.append(fig_covariates(grid, bal if bal.exists() else None))
    return paths


# Compat anciennes signatures
def fig_covariate_balance(grid, balance_csv=None):
    return fig_covariates(grid, balance_csv)


def fig_timeseries(ts, grid):
    return Path()


def fig_outcome_forest(results):
    return Path()


def fig_map_metric(grid, metrics, outcome="trend_slope", variable="NDVI"):
    return Path()


if __name__ == "__main__":
    for p in make_all_publication_figures():
        print(p)
