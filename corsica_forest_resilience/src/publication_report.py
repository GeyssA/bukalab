"""
Rapport PDF publiable — figures retravaillées + texte scientifique en français.

Usage:
    py -m src.publication_report
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from . import ROOT, load_config, setup_logger
from .figures import (
    C_COAST,
    C_LAND,
    C_OUT,
    C_PNR,
    C_PNR_LINE,
    C_SEA,
    _add_north,
    _add_scalebar,
    _basemap,
    _panel_label,
    _save,
)

log = setup_logger("pub_report")

mpl.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 9.5,
        "axes.linewidth": 0.7,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)

OUTCOME_FR = {
    "trend_slope": "Pente de tendance",
    "mean_level": "Niveau moyen",
    "anomaly_mean": "Anomalie moyenne",
    "cv": "Coefficient de variation",
    "recovery_years": "Délai de récupération",
}


# ---------------------------------------------------------------------------
# Figures publication
# ---------------------------------------------------------------------------


def fig_pub_design_map() -> Path:
    """Carte design : cellules matchées PNR / contrôles."""
    cfg = load_config()
    grid = gpd.read_file(ROOT / cfg["paths"]["processed"] / "forest_grid_1km.gpkg")
    pnr = gpd.read_file(ROOT / cfg["paths"]["processed"] / "pnr_corse.gpkg")
    pairs = pd.read_csv(ROOT / cfg["paths"]["tables"] / "matched_pairs.csv")
    region = grid.dissolve().reset_index(drop=True)

    treat = set(pairs["treat_cell"])
    ctrl = set(pairs["ctrl_cell"])
    g_t = grid.loc[grid["cell_id"].isin(treat)]
    g_c = grid.loc[grid["cell_id"].isin(ctrl)]
    g_other = grid.loc[~grid["cell_id"].isin(treat | ctrl)]

    fig, ax = plt.subplots(figsize=(7.2, 8.6))
    _basemap(ax, region, pnr)
    if len(g_other):
        g_other.plot(ax=ax, color="#D0D3D4", edgecolor="none", alpha=0.45, zorder=2)
    g_c.plot(ax=ax, color=C_OUT, edgecolor="none", alpha=0.9, zorder=3)
    g_t.plot(ax=ax, color=C_PNR, edgecolor="none", alpha=0.9, zorder=3)
    _add_scalebar(ax)
    _add_north(ax)
    ax.legend(
        handles=[
            Patch(facecolor=C_PNR, edgecolor="none", label=f"PNR matché (n={len(g_t)})"),
            Patch(facecolor=C_OUT, edgecolor="none", label=f"Contrôle matché (n={len(g_c)})"),
            Patch(facecolor="#D0D3D4", edgecolor="none", label="Forêt hors support commun"),
            Patch(facecolor="#1B5E4A18", edgecolor=C_PNR_LINE, label="Limite PNR"),
        ],
        loc="upper left",
        fontsize=8,
        frameon=True,
        fancybox=False,
        edgecolor="0.85",
        framealpha=0.95,
    )
    ax.set_title(
        "Plan d'échantillonnage — paires appariées (1 km, ≥60 % forêt)",
        fontsize=11,
        color=C_COAST,
        pad=10,
    )
    fig.text(
        0.5,
        0.02,
        "EPSG:2154 · BD Forêt v2 · Appariement 1:1 sur covariables standardisées · "
        "Les cellules hors support commun ne sont pas dans l'inférence principale.",
        ha="center",
        fontsize=7,
        color="0.35",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return _save(fig, "pub_fig01_matched_sample")


def fig_pub_balance() -> Path:
    """Love plot SMD avant logique de lecture claire."""
    bal = pd.read_csv(ROOT / load_config()["paths"]["tables"] / "covariate_balance.csv")
    labels = {
        "elevation_m": "Altitude (m)",
        "slope_deg": "Pente (°)",
        "aspect_sin": "Aspect (sin)",
        "aspect_cos": "Aspect (cos)",
        "summer_temp_mean": "Température estivale (°C)",
        "annual_precip": "Précipitations annuelles (mm)",
        "dist_coast_km": "Distance à la côte (km)",
        "ft_broadleaf": "Type : feuillus",
        "ft_conifer": "Type : conifères",
        "ft_mixed": "Type : mixtes",
        "ft_other": "Type : autres",
    }
    bal = bal.copy()
    bal["label"] = bal["covariate"].map(labels).fillna(bal["covariate"])
    bal = bal.sort_values("smd_matched")

    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    y = np.arange(len(bal))
    ax.axvline(0, color=C_COAST, lw=0.9)
    ax.axvspan(-0.1, 0.1, color="#1B5E4A", alpha=0.08, zorder=0)
    ax.axvline(-0.1, color="#1B5E4A", lw=0.6, ls=":", alpha=0.7)
    ax.axvline(0.1, color="#1B5E4A", lw=0.6, ls=":", alpha=0.7)
    ax.scatter(bal["smd_matched"], y, s=55, color=C_PNR, zorder=3, edgecolors="white", lw=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(bal["label"])
    ax.set_xlabel("Différence moyenne standardisée (SMD) après appariement")
    ax.set_title(
        "Équilibre des covariables après matching 1:1",
        color=C_COAST,
        fontsize=11,
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(
        0.98,
        0.02,
        "Bande grisée : |SMD| ≤ 0,1\n(seuil souvent jugé satisfaisant)",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.5,
        color="0.35",
    )
    fig.text(
        0.5,
        0.01,
        "SMD = (moyenne PNR − moyenne contrôle) / écart-type combiné. "
        "Altitude, climat et distance à la côte restent déséquilibrés → matching imparfait.",
        ha="center",
        fontsize=7,
        color="0.35",
    )
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    return _save(fig, "pub_fig02_covariate_balance")


def fig_pub_timeseries() -> Path:
    cfg = load_config()
    ts = pd.read_csv(ROOT / cfg["paths"]["processed"] / "s2_summer_matched_cells.csv")
    pairs = pd.read_csv(ROOT / cfg["paths"]["tables"] / "matched_pairs.csv")
    treat, ctrl = set(pairs["treat_cell"]), set(pairs["ctrl_cell"])
    ts = ts.copy()
    ts["group"] = np.where(
        ts["cell_id"].isin(treat), "PNR", np.where(ts["cell_id"].isin(ctrl), "Hors PNR", "x")
    )
    ts = ts.loc[ts["group"] != "x"]

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.6), sharex=True)
    titles = {
        "NDVI": "NDVI — activité / verdure de canopée",
        "NDMI": "NDMI — proxy d'humidité de canopée",
    }
    for ax, var in zip(axes, ["NDVI", "NDMI"]):
        for group, color, marker in [("PNR", C_PNR, "o"), ("Hors PNR", C_OUT, "s")]:
            g = ts.loc[ts["group"] == group].groupby("year")[var].agg(["mean", "sem"])
            ax.plot(
                g.index,
                g["mean"],
                color=color,
                lw=2.2,
                marker=marker,
                ms=5.5,
                label=group,
                zorder=3,
            )
            ax.fill_between(
                g.index,
                g["mean"] - 1.96 * g["sem"],
                g["mean"] + 1.96 * g["sem"],
                color=color,
                alpha=0.16,
                zorder=2,
            )
        # Annoter 2022
        ax.axvspan(2021.5, 2022.5, color="#B03A2E", alpha=0.08, zorder=1)
        ax.set_ylabel(titles[var].split("—")[0].strip())
        ax.set_xlabel("Année (médiane estivale JJA)")
        ax.set_title(titles[var], fontsize=10, color=C_COAST, pad=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_xticks(range(2017, 2026))
        ax.tick_params(axis="x", rotation=45)
        ax.legend(loc="lower left", fontsize=8)
    axes[0].annotate(
        "2022",
        xy=(2022, axes[0].get_ylim()[0] + 0.02 * np.diff(axes[0].get_ylim())[0]),
        ha="center",
        fontsize=8,
        color="#922B21",
        fontweight="bold",
    )
    _panel_label(axes[0], "a")
    _panel_label(axes[1], "b")
    fig.suptitle(
        "Trajectoires estivales Sentinel-2 sur cellules appariées (2017–2025)",
        fontsize=12,
        color=C_COAST,
        y=1.02,
    )
    fig.text(
        0.5,
        -0.02,
        "Moyenne spatiale ± IC95 % approximatif (1,96 × erreur-type). "
        "Sentinel-2 L2A (Planetary Computer) · masque SCL {4,5,7} · médiane JJA à 200 m. "
        "Les deux groupes suivent une dynamique quasi parallèle, avec une chute commune en 2022.",
        ha="center",
        fontsize=7.2,
        color="0.35",
    )
    fig.tight_layout()
    return _save(fig, "pub_fig03_timeseries")


def fig_pub_trends() -> Path:
    cfg = load_config()
    metrics = pd.read_csv(ROOT / cfg["paths"]["processed"] / "trajectory_metrics.csv")
    pairs = pd.read_csv(ROOT / cfg["paths"]["tables"] / "matched_pairs.csv")
    treat, ctrl = set(pairs["treat_cell"]), set(pairs["ctrl_cell"])
    m = metrics.copy()
    m["group"] = np.where(
        m["cell_id"].isin(treat), "PNR", np.where(m["cell_id"].isin(ctrl), "Hors PNR", "x")
    )
    m = m.loc[m["group"] != "x"]

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.5))
    for ax, var in zip(axes, ["NDVI", "NDMI"]):
        sub = m.loc[m["variable"] == var]
        data = [
            sub.loc[sub["group"] == "Hors PNR", "trend_slope"].dropna().values,
            sub.loc[sub["group"] == "PNR", "trend_slope"].dropna().values,
        ]
        parts = ax.violinplot(data, positions=[0, 1], widths=0.7, showmedians=False, showextrema=False)
        for i, body in enumerate(parts["bodies"]):
            body.set_facecolor([C_OUT, C_PNR][i])
            body.set_alpha(0.75)
            body.set_edgecolor("white")
        # box overlay
        bp = ax.boxplot(
            data,
            positions=[0, 1],
            widths=0.18,
            patch_artist=True,
            showfliers=False,
            medianprops=dict(color="white", lw=1.4),
            whiskerprops=dict(color=C_COAST, lw=0.8),
            capprops=dict(color=C_COAST, lw=0.8),
        )
        for i, box in enumerate(bp["boxes"]):
            box.set_facecolor([C_OUT, C_PNR][i])
            box.set_alpha(0.95)
        ax.axhline(0, color="0.55", lw=0.8, ls="--")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Hors PNR", "PNR"])
        ax.set_ylabel(f"Pente {var} (unités·an⁻¹)")
        ax.set_title(f"Distribution des tendances {var}", color=C_COAST, fontsize=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        # mean delta annotation
        delta = np.nanmean(data[1]) - np.nanmean(data[0])
        ax.text(
            0.98,
            0.98,
            f"Δ moyenne ≈ {delta:+.4f}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=8,
            color="0.35",
        )
    _panel_label(axes[0], "a")
    _panel_label(axes[1], "b")
    fig.suptitle(
        "Tendances linéaires estivales — cellules des paires matchées",
        color=C_COAST,
        fontsize=12,
    )
    fig.text(
        0.5,
        0.01,
        "Violons = densité empirique ; boîtes = médiane et IQR. "
        "Une pente nulle indique une stabilité temporelle moyenne sur 2017–2025.",
        ha="center",
        fontsize=7.2,
        color="0.35",
    )
    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
    return _save(fig, "pub_fig04_trends")


def fig_pub_effects() -> Path:
    """Forest plots séparés par famille de métriques (échelles lisibles)."""
    res = pd.read_csv(ROOT / load_config()["paths"]["tables"] / "matched_outcome_tests.csv")
    panels = [
        ("Tendances (cœur de la question)", ["trend_slope"]),
        ("Niveaux et anomalies", ["mean_level", "anomaly_mean"]),
        ("Variabilité et récupération", ["cv", "recovery_years"]),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 4.8), sharey=False)
    for ax, (title, outcomes) in zip(axes, panels):
        focus = res.loc[res["outcome"].isin(outcomes)].copy()
        focus["ylab"] = focus.apply(
            lambda r: f"{r['variable']} · {OUTCOME_FR.get(r['outcome'], r['outcome'])}",
            axis=1,
        )
        focus = focus.iloc[::-1].reset_index(drop=True)
        y = np.arange(len(focus))
        ax.axvline(0, color=C_COAST, lw=1.0, zorder=1)
        xerr = np.vstack(
            [
                focus["mean_diff_pnr_minus_ctrl"] - focus["ci95_low"],
                focus["ci95_high"] - focus["mean_diff_pnr_minus_ctrl"],
            ]
        )
        colors_pt = [
            "#922B21" if not (lo <= 0 <= hi) else C_PNR
            for lo, hi in zip(focus["ci95_low"], focus["ci95_high"])
        ]
        ax.errorbar(
            focus["mean_diff_pnr_minus_ctrl"],
            y,
            xerr=xerr,
            fmt="none",
            ecolor="0.55",
            elinewidth=1.2,
            capsize=3.5,
            zorder=2,
        )
        ax.scatter(
            focus["mean_diff_pnr_minus_ctrl"],
            y,
            c=colors_pt,
            s=48,
            zorder=3,
            edgecolors="white",
            lw=0.7,
        )
        ax.set_yticks(y)
        ax.set_yticklabels(focus["ylab"], fontsize=8)
        ax.set_title(title, fontsize=9.5, color=C_COAST, pad=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_xlabel("Δ (PNR − contrôle)", fontsize=8)
    fig.suptitle(
        "Effets appariés après matching — IC95 % bootstrap (ne pas lire comme effet causal)",
        fontsize=12,
        color=C_COAST,
    )
    fig.text(
        0.5,
        0.01,
        "Point rouge : IC95 % n'inclut pas 0 (signal statistique, pas preuve causale). "
        "Point vert : compatible avec une différence nulle. "
        "Δ = moyenne des différences sur paires matchées.",
        ha="center",
        fontsize=7.2,
        color="0.35",
    )
    # legend
    axes[0].legend(
        handles=[
            Line2D([0], [0], marker="o", color="w", markerfacecolor=C_PNR, markersize=7, label="IC inclut 0"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="#922B21", markersize=7, label="IC exclut 0"),
        ],
        loc="lower right",
        fontsize=7,
    )
    fig.tight_layout(rect=[0, 0.06, 1, 0.93])
    return _save(fig, "pub_fig05_effects")


def fig_pub_covariate_context() -> Path:
    """Deux cartes : altitude et température estivale des cellules forestières."""
    cfg = load_config()
    grid = gpd.read_file(ROOT / cfg["paths"]["processed"] / "forest_grid_1km.gpkg")
    pnr = gpd.read_file(ROOT / cfg["paths"]["processed"] / "pnr_corse.gpkg")
    region = grid.dissolve().reset_index(drop=True)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 6.2))
    specs = [
        ("elevation_m", "Altitude (m)", "terrain"),
        ("summer_temp_mean", "Température estivale moyenne (°C)", "coolwarm"),
    ]
    for ax, (col, label, cmap) in zip(axes, specs):
        _basemap(ax, region, pnr)
        grid.plot(
            ax=ax,
            column=col,
            cmap=cmap,
            linewidth=0,
            legend=True,
            legend_kwds={"shrink": 0.55, "label": label, "pad": 0.02},
            zorder=3,
        )
        _add_scalebar(ax, length_m=25000, label="25 km")
        _add_north(ax)
        ax.set_title(label, color=C_COAST, fontsize=10)
    _panel_label(axes[0], "a")
    _panel_label(axes[1], "b")
    fig.suptitle(
        "Contexte environnemental des cellules forestières (1 km)",
        color=C_COAST,
        fontsize=12,
    )
    fig.text(
        0.5,
        0.02,
        "Les forêts du PNR (contour sombre) sont en moyenne plus élevées et plus fraîches — "
        "d'où la nécessité d'un appariement avant toute comparaison de trajectoires.",
        ha="center",
        fontsize=7.2,
        color="0.35",
    )
    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
    return _save(fig, "pub_fig00_context")


def rebuild_all_figures() -> list[Path]:
    log.info("Régénération des figures publication…")
    paths = [
        fig_pub_covariate_context(),
        fig_pub_design_map(),
        fig_pub_balance(),
        fig_pub_timeseries(),
        fig_pub_trends(),
        fig_pub_effects(),
    ]
    return paths


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def _register_fonts() -> tuple[str, str]:
    """Enregistre DejaVu pour les caractères français."""
    candidates = list(Path(mpl.get_data_path()).glob("fonts/ttf/DejaVuSans*.ttf"))
    regular = next((p for p in candidates if p.name == "DejaVuSans.ttf"), None)
    bold = next((p for p in candidates if p.name == "DejaVuSans-Bold.ttf"), None)
    if regular is None:
        return "Helvetica", "Helvetica-Bold"
    pdfmetrics.registerFont(TTFont("DejaVu", str(regular)))
    if bold:
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(bold)))
        return "DejaVu", "DejaVu-Bold"
    return "DejaVu", "DejaVu"


def _styles(font: str, font_bold: str):
    base = getSampleStyleSheet()
    styles = {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName=font_bold,
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1B5E4A"),
            spaceAfter=12,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            parent=base["Normal"],
            fontName=font,
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#2C3E50"),
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName=font_bold,
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1B5E4A"),
            spaceBefore=14,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName=font_bold,
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#2C3E50"),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName=font,
            fontSize=9.5,
            leading=13.2,
            alignment=TA_JUSTIFY,
            spaceAfter=7,
            textColor=colors.HexColor("#1C2833"),
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=base["Normal"],
            fontName=font,
            fontSize=8.2,
            leading=11,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#566573"),
            spaceBefore=4,
            spaceAfter=10,
            leftIndent=4,
            rightIndent=4,
        ),
        "note": ParagraphStyle(
            "note",
            parent=base["Normal"],
            fontName=font,
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor("#7B241C"),
            spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName=font,
            fontSize=8,
            textColor=colors.HexColor("#7F8C8D"),
            alignment=TA_CENTER,
        ),
    }
    return styles


def _img(path: Path, max_w_cm: float = 16.5, max_h_cm: float = 11.5) -> Image:
    im = Image(str(path))
    aspect = im.imageHeight / float(im.imageWidth)
    w = max_w_cm * cm
    h = w * aspect
    max_h = max_h_cm * cm
    if h > max_h:
        h = max_h
        w = h / aspect
    im.drawWidth = w
    im.drawHeight = h
    return im


def _fmt(x: float, digits: int = 4) -> str:
    if abs(x) >= 1:
        return f"{x:.3f}"
    return f"{x:.{digits}f}"


def build_pdf(fig_paths: dict[str, Path]) -> Path:
    cfg = load_config()
    out = ROOT / cfg["paths"]["figures"] / "Rapport_PNR_Corse_Trajectoires_Forestieres.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)

    font, font_bold = _register_fonts()
    styles = _styles(font, font_bold)

    res = pd.read_csv(ROOT / cfg["paths"]["tables"] / "matched_outcome_tests.csv")
    bal = pd.read_csv(ROOT / cfg["paths"]["tables"] / "covariate_balance.csv")
    meta = json.loads((ROOT / cfg["paths"]["tables"] / "matching.meta.json").read_text(encoding="utf-8"))
    summary = json.loads((ROOT / cfg["paths"]["tables"] / "analysis_summary.json").read_text(encoding="utf-8"))

    n_pairs_match = int(meta.get("n_pairs", 1498))
    n_pairs_test = int(summary.get("n_pairs_tests", 1495))

    def header_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#1B5E4A"))
        canvas.setLineWidth(0.6)
        canvas.line(1.8 * cm, A4[1] - 1.2 * cm, A4[0] - 1.8 * cm, A4[1] - 1.2 * cm)
        canvas.setFont(font, 7.5)
        canvas.setFillColor(colors.HexColor("#7F8C8D"))
        canvas.drawString(1.8 * cm, A4[1] - 1.0 * cm, "Forest Resilience · PNR Corse · Sentinel-2")
        canvas.drawRightString(A4[0] - 1.8 * cm, A4[1] - 1.0 * cm, "Étude observationnelle — 24/09/2026")
        canvas.line(1.8 * cm, 1.3 * cm, A4[0] - 1.8 * cm, 1.3 * cm)
        canvas.drawCentredString(A4[0] / 2, 0.8 * cm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="Trajectoires forestières PNR Corse — rapport",
        author="corsica_forest_resilience",
    )

    story = []

    # --- Couverture ---
    story.append(Spacer(1, 2.2 * cm))
    story.append(Paragraph(
        "Trajectoires forestières Sentinel-2<br/>à l'intérieur et à l'extérieur<br/>du Parc naturel régional de Corse",
        styles["cover_title"],
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "Comparaison observationnelle sur cellules forestières appariées<br/>"
        "NDVI · NDMI · tendances estivales 2017–2025",
        styles["cover_sub"],
    ))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "<b>Rapport de résultats</b> — design reproductible, données officielles,<br/>"
        "pas d'attribution causale automatique au statut de protection.",
        styles["cover_sub"],
    ))
    story.append(Spacer(1, 1.0 * cm))
    if "context" in fig_paths:
        story.append(_img(fig_paths["context"], max_w_cm=15.5, max_h_cm=9.5))
        story.append(Paragraph(
            "<b>Figure de couverture.</b> Contexte topoclimatique des cellules forestières 1 km "
            "(altitude et température estivale). Le contour sombre délimite le PNR.",
            styles["caption"],
        ))
    story.append(PageBreak())

    # --- Résumé ---
    story.append(Paragraph("1. Résumé", styles["h1"]))
    story.append(Paragraph(
        "Nous testons si les forêts <b>comparables</b> situées dans le Parc naturel régional (PNR) "
        "de Corse présentent des trajectoires satellitaires différentes des forêts hors PNR. "
        f"Après appariement 1:1 ({n_pairs_match} paires ; {n_pairs_test} retenues pour les tests), "
        "les <b>pentes de tendance estivales</b> du NDVI et du NDMI sur 2017–2025 ne diffèrent pas "
        "de façon détectable (intervalles de confiance à 95 % incluant zéro). Les séries temporelles "
        "des deux groupes sont quasi parallèles, y compris lors de la chute marquée de 2022. "
        "Un niveau moyen de NDMI légèrement plus élevé dans le PNR (Δ ≈ +0,012) constitue un signal "
        "statistique faible, non interprétable comme preuve d'un effet causal du PNR.",
        styles["body"],
    ))
    story.append(Paragraph(
        "<b>Avertissement méthodologique.</b> Le matching laisse des déséquilibres résiduels "
        "(altitude, climat, distance à la côte). Les résultats portent sur le <i>support commun</i> "
        "des cellules appariables, et non sur l'ensemble du PNR.",
        styles["note"],
    ))

    # --- Glossaire ---
    story.append(Paragraph("2. Glossaire des acronymes et termes", styles["h1"]))
    glossary = [
        ("PNR", "Parc naturel régional — aire de protection française associant conservation "
         "et développement durable ; ce n'est pas une réserve intégrale ni un traitement expérimental."),
        ("BD Forêt", "Base de Données Forêt (IGN) version 2 — référentiel national des formations "
         "végétales arborées (polygones ≥ 0,5 ha)."),
        ("S2 / Sentinel-2", "Constellation optique Copernicus (ESA) ; ici produits L2A (réflectance "
         "de surface atmosphériquement corrigée)."),
        ("L2A", "Level-2A — image Sentinel-2 en réflectance de surface."),
        ("SCL", "Scene Classification Layer — masque de classes (nuages, ombres, végétation…). "
         "Nous retenons les classes claires 4, 5 et 7."),
        ("NDVI", "Normalized Difference Vegetation Index = (NIR − Rouge) / (NIR + Rouge). "
         "Proxy d'activité / verdure de canopée (bande NIR = B08, rouge = B04)."),
        ("NDMI", "Normalized Difference Moisture Index = (NIR − SWIR) / (NIR + SWIR). "
         "Proxy d'humidité de canopée (SWIR = B11)."),
        ("JJA", "Juin–Juillet–Août — fenêtre estivale de stress hydrique en climat méditerranéen."),
        ("STAC", "SpatioTemporal Asset Catalog — catalogue d'accès aux archives satellitaires "
         "(ici Microsoft Planetary Computer)."),
        ("ERA5-Land", "Réanalyse climatique ECMWF à fine échelle ; ici via l'API Open-Meteo "
         "(température, précipitations)."),
        ("SMD", "Standardized Mean Difference — différence des moyennes divisée par un écart-type "
         "combiné ; mesure d'équilibre des covariables après matching (|SMD| ≤ 0,1 souvent ciblé)."),
        ("IC95 %", "Intervalle de confiance à 95 % — ici obtenu par bootstrap des différences appariées."),
        ("CV", "Coefficient de variation (écart-type / moyenne) — mesure de variabilité interannuelle."),
        ("EPSG:2154", "Système de coordonnées Lambert-93 (France métropolitaine)."),
        ("EFFIS", "European Forest Fire Information System — périmètres de feux (non intégré "
         "dans cette version des résultats)."),
    ]
    th = ParagraphStyle("th", fontName=font_bold, fontSize=9, textColor=colors.white, leading=11)
    td_term = ParagraphStyle("td_term", fontName=font_bold, fontSize=8, leading=10.5, textColor=colors.HexColor("#1C2833"))
    td_def = ParagraphStyle("td_def", fontName=font, fontSize=8, leading=10.5, textColor=colors.HexColor("#1C2833"))
    gdata = [[Paragraph("Terme", th), Paragraph("Définition", th)]]
    for term, definition in glossary:
        gdata.append([Paragraph(term, td_term), Paragraph(definition, td_def)])
    gt = Table(gdata, colWidths=[3.2 * cm, 13.5 * cm])
    gt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E4A")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5D8DC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F7")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(gt)
    story.append(PageBreak())

    # --- Question ---
    story.append(Paragraph("3. Question de recherche", styles["h1"]))
    story.append(Paragraph(
        "Les forêts méditerranéennes corses font face à la sécheresse, aux feux et aux changements "
        "d'usage. Le PNR de Corse est une aire de protection à vocation mixte. Évaluer si les forêts "
        "<i>à l'intérieur</i> du PNR évoluent différemment de celles <i>à l'extérieur</i> exige de "
        "contrôler le biais de composition : les forêts du PNR sont, en moyenne, plus élevées, plus "
        "fraîches, plus arrosées et plus éloignées de la côte.",
        styles["body"],
    ))
    story.append(Paragraph(
        "<b>Question opérationnelle.</b> Sur des cellules forestières 1 km appariées selon des "
        "covariables topographiques, climatiques et de type forestier, observe-t-on des différences "
        "de trajectoires Sentinel-2 (NDVI, NDMI) entre PNR et hors PNR sur la période 2017–2025 ?",
        styles["body"],
    ))
    story.append(Paragraph(
        "Nous rejetons explicitement la formulation vague « les forêts du PNR sont-elles meilleures ? ».",
        styles["body"],
    ))

    # --- Données & méthodo ---
    story.append(Paragraph("4. Données et méthodes", styles["h1"]))
    story.append(Paragraph("4.1 Sources", styles["h2"]))
    story.append(Paragraph(
        "Limites du PNR : couche nationale FPNRF (07/11/2024), extraction du site « Corse ». "
        "Masque forestier et types : BD Forêt® v2 (IGN), départements 2A et 2B, codes FF*/FO* "
        "(landes exclues). Imagerie : Sentinel-2 L2A via le catalogue STAC Microsoft Planetary Computer. "
        "Covariables climatiques et d'altitude : ERA5-Land / Open-Meteo (température estivale, "
        "précipitations annuelles, élévation).",
        styles["body"],
    ))

    story.append(Paragraph("4.2 Unité d'analyse et design", styles["h2"]))
    story.append(Paragraph(
        "Grille régulière de 1 km en Lambert-93 (EPSG:2154). Une cellule est retenue si la fraction "
        "de couverture BD Forêt est ≥ 60 %. Ce seuil limite le bruit des pixels mixtes tout en "
        "restant plus fin que les gradients climatiques régionaux. L'inférence principale porte sur "
        "les paires appariées ; les forêts sans contrepartie comparable (hors support commun) sont "
        "exclues des tests.",
        styles["body"],
    ))
    if "design" in fig_paths:
        story.append(_img(fig_paths["design"], max_w_cm=14.5, max_h_cm=12))
        story.append(Paragraph(
            f"<b>Figure 1.</b> Plan d'échantillonnage : {n_pairs_match} cellules PNR (vert) et "
            f"{n_pairs_match} contrôles hors PNR (ocre) après matching 1:1. Le gris indique les "
            "cellules forestières hors support commun, non utilisées dans l'estimation principale.",
            styles["caption"],
        ))

    story.append(Paragraph("4.3 Prétraitement Sentinel-2", styles["h2"]))
    story.append(Paragraph(
        "Pour chaque été (JJA, 2017–2025), une mosaïque médiane de réflectance est construite à "
        "200 m après filtrage SCL (classes 4 = végétation, 5 = sols non végétaux, 7 = nuages bas "
        "non opaques / classes claires retenues selon le protocole du projet). Les indices calculés "
        "sont le NDVI (activité) et le NDMI (humidité de canopée). La médiane saisonnière réduit "
        "l'influence des scènes aberrantes.",
        styles["body"],
    ))

    story.append(Paragraph("4.4 Métriques de trajectoire", styles["h2"]))
    story.append(Paragraph(
        "Par cellule et par indice : (i) <b>pente linéaire</b> annuelle (tendance) ; "
        "(ii) <b>niveau moyen</b> sur la période ; (iii) <b>anomalie moyenne</b> par rapport à une "
        "baseline précoce ; (iv) <b>coefficient de variation</b> interannuel ; "
        "(v) <b>délai de récupération</b> après une chute spectrale (retour à ≥ 90 % du niveau de "
        "référence), calculé sur un sous-échantillon.",
        styles["body"],
    ))

    story.append(Paragraph("4.5 Appariement (matching)", styles["h2"]))
    story.append(Paragraph(
        "Appariement 1:1 par plus proche voisin sur covariables standardisées (distance euclidienne "
        "avec caliper ≈ 0,5√p) : altitude, pente, aspect (sinus/cosinus), température estivale, "
        "précipitations annuelles, distance à la côte, groupe de type forestier. L'équilibre est "
        "évalué via la SMD. Les types forestiers sont parfaitement alignés ; altitude, climat et "
        "distance à la côte restent déséquilibrés — le matching est donc <b>imparfait</b> et doit "
        "être lu comme un contrôle partiel, non comme une randomisation.",
        styles["body"],
    ))
    if "balance" in fig_paths:
        story.append(_img(fig_paths["balance"], max_w_cm=15.5, max_h_cm=9))
        story.append(Paragraph(
            "<b>Figure 2.</b> Love plot des SMD après matching. La bande grisée (|SMD| ≤ 0,1) "
            "représente un équilibre souvent jugé satisfaisant. Plusieurs covariables topoclimatiques "
            "restent hors de cette bande.",
            styles["caption"],
        ))

    story.append(Paragraph("4.6 Inférence statistique", styles["h2"]))
    story.append(Paragraph(
        "Pour chaque métrique, on calcule la différence appariée Δ = valeur<sub>PNR</sub> − "
        "valeur<sub>contrôle</sub> sur chaque paire, puis la moyenne de Δ et un IC95 % par bootstrap. "
        "Un test des signes complète la lecture. <b>Aucune conclusion causale</b> du type "
        "« le PNR cause… » n'est autorisée par ce design seul.",
        styles["body"],
    ))
    story.append(PageBreak())

    # --- Résultats ---
    story.append(Paragraph("5. Résultats", styles["h1"]))
    story.append(Paragraph("5.1 Trajectoires temporelles", styles["h2"]))
    story.append(Paragraph(
        "Les médianes estivales moyennes des cellules matchées montrent une dynamique commune : "
        "niveaux élevés en 2017–2021, rupture nette en 2022, puis niveaux bas en 2023–2025 avec "
        "récupération lente. Les courbes PNR et hors PNR se superposent largement pour le NDVI ; "
        "le NDMI du PNR reste légèrement au-dessus, sans divergence de forme.",
        styles["body"],
    ))
    if "timeseries" in fig_paths:
        story.append(_img(fig_paths["timeseries"], max_w_cm=16.2, max_h_cm=8.5))
        story.append(Paragraph(
            "<b>Figure 3.</b> Trajectoires estivales NDVI (a) et NDMI (b) sur cellules appariées. "
            "Bandes : IC95 % approximatif autour de la moyenne spatiale. La zone rougeâtre marque 2022.",
            styles["caption"],
        ))

    story.append(Paragraph("5.2 Distributions des tendances", styles["h2"]))
    story.append(Paragraph(
        "Les distributions des pentes NDVI et NDMI se chevauchent fortement entre PNR et hors PNR. "
        "Les médianes sont proches de zéro dans les deux groupes, indiquant l'absence de tendance "
        "monotone marquée une fois le choc 2022 intégré dans la série.",
        styles["body"],
    ))
    if "trends" in fig_paths:
        story.append(_img(fig_paths["trends"], max_w_cm=15.8, max_h_cm=8))
        story.append(Paragraph(
            "<b>Figure 4.</b> Densités empiriques (violons) et boîtes à moustaches des pentes "
            "linéaires estivales. Δ moyenne annotée sur chaque panneau.",
            styles["caption"],
        ))

    story.append(Paragraph("5.3 Effets appariés (tableau et figure)", styles["h2"]))

    # results table
    res_disp = res.copy()
    rows = [[
        Paragraph("<b>Indice</b>", ParagraphStyle("th", fontName=font_bold, fontSize=8, textColor=colors.white)),
        Paragraph("<b>Métrique</b>", ParagraphStyle("th", fontName=font_bold, fontSize=8, textColor=colors.white)),
        Paragraph("<b>n</b>", ParagraphStyle("th", fontName=font_bold, fontSize=8, textColor=colors.white)),
        Paragraph("<b>Δ moyen</b>", ParagraphStyle("th", fontName=font_bold, fontSize=8, textColor=colors.white)),
        Paragraph("<b>IC95 % bas</b>", ParagraphStyle("th", fontName=font_bold, fontSize=8, textColor=colors.white)),
        Paragraph("<b>IC95 % haut</b>", ParagraphStyle("th", fontName=font_bold, fontSize=8, textColor=colors.white)),
        Paragraph("<b>Lecture</b>", ParagraphStyle("th", fontName=font_bold, fontSize=8, textColor=colors.white)),
    ]]
    cell_style = ParagraphStyle("td", fontName=font, fontSize=7.5, leading=9.5)
    for _, r in res_disp.iterrows():
        excludes = not (r["ci95_low"] <= 0 <= r["ci95_high"])
        lecture = "Signal (IC exclut 0)" if excludes else "Compatible avec Δ = 0"
        rows.append([
            Paragraph(str(r["variable"]), cell_style),
            Paragraph(OUTCOME_FR.get(r["outcome"], r["outcome"]), cell_style),
            Paragraph(str(int(r["n_pairs"])), cell_style),
            Paragraph(_fmt(float(r["mean_diff_pnr_minus_ctrl"])), cell_style),
            Paragraph(_fmt(float(r["ci95_low"])), cell_style),
            Paragraph(_fmt(float(r["ci95_high"])), cell_style),
            Paragraph(lecture, cell_style),
        ])
    rt = Table(rows, colWidths=[1.6*cm, 3.6*cm, 1.2*cm, 2.0*cm, 2.2*cm, 2.2*cm, 3.4*cm])
    rt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E4A")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5D8DC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F7")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(rt)
    story.append(Paragraph(
        "<b>Tableau 1.</b> Différences appariées Δ = PNR − contrôle. Les pentes NDVI et NDMI "
        "(cœur de la question « trajectoires ») sont compatibles avec une différence nulle.",
        styles["caption"],
    ))

    if "effects" in fig_paths:
        story.append(_img(fig_paths["effects"], max_w_cm=16.2, max_h_cm=8.2))
        story.append(Paragraph(
            "<b>Figure 5.</b> Forest plots par famille de métriques (échelles adaptées). "
            "Points rouges : IC95 % n'incluant pas zéro. Même dans ces cas, l'interprétation "
            "reste associative, non causale.",
            styles["caption"],
        ))

    story.append(PageBreak())

    # --- Discussion ---
    story.append(Paragraph("6. Discussion", styles["h1"]))
    story.append(Paragraph(
        "<b>Ce que montrent les données.</b> Après tentative de contrôle des covariables observées, "
        "les forêts PNR et hors PNR du support commun évoluent de façon très similaire en NDVI et "
        "NDMI estivaux. Le choc de 2022 — vraisemblablement lié à un épisode de stress thermique "
        "et hydrique exceptionnel — affecte les deux groupes de manière comparable.",
        styles["body"],
    ))
    story.append(Paragraph(
        "<b>Ce qu'elles ne montrent pas.</b> Ni un avantage clair du PNR sur les tendances ou la "
        "récupération, ni un désavantage. Le Δ NDMI de niveau moyen (+0,012) est un signal faible "
        "pouvant encore refléter le biais résiduel d'altitude/climat.",
        styles["body"],
    ))
    story.append(Paragraph(
        "<b>Portée.</b> Les conclusions concernent les cellules appariables. Les forêts très "
        "montagnardes du PNR sans contrepartie hors PNR ne sont pas dans l'estimation. "
        "Le statut PNR n'est pas un traitement assigné aléatoirement : toute lecture causale "
        "exigerait un design plus fort (par ex. différences-en-différences autour d'une "
        "désignation — difficile pour un PNR ancien).",
        styles["body"],
    ))

    story.append(Paragraph("7. Limites", styles["h1"]))
    limits = [
        "Masque forestier statique (BD Forêt v2) — pas de dynamique d'occupation du sol.",
        "Matching imparfait : SMD élevés pour altitude, température estivale et distance à la côte.",
        "Covariables climatiques / altimétriques à grain ~1 km (proxies Open-Meteo / ERA5-Land).",
        "EFFIS (feux) non intégré dans cette version.",
        "Autocorrélation spatiale possible ; IC bootstrap sans modèle spatial formel.",
        "NDMI est un proxy spectral, non une mesure physiologique de sécheresse.",
        "Résolution de travail 200 m et grille 1 km — sensibilités 500 m / 2 km non exécutées ici.",
    ]
    story.append(ListFlowable(
        [ListItem(Paragraph(t, styles["body"]), leftIndent=8, bulletColor=colors.HexColor("#1B5E4A")) for t in limits],
        bulletType="bullet",
        start="•",
    ))

    story.append(Paragraph("8. Conclusion", styles["h1"]))
    story.append(Paragraph(
        "Sur 1 495 paires de cellules forestières matchées en Corse, <b>aucune différence détectable "
        "des tendances estivales NDVI et NDMI</b> n'apparaît entre PNR et hors PNR pour 2017–2025. "
        "Les trajectoires sont parallèles, y compris lors de la rupture de 2022. Ce résultat "
        "observationnel ne permet pas de conclure à l'absence (ni à la présence) d'un effet causal "
        "du Parc naturel régional ; il montre que, sur le support commun et après contrôle partiel "
        "des covariables, les dynamiques satellitaires sont semblables.",
        styles["body"],
    ))

    story.append(Paragraph("9. Reproductibilité", styles["h1"]))
    story.append(Paragraph(
        "Configuration : <font face='Courier'>config.yaml</font>. "
        "Pipeline : <font face='Courier'>py run_pipeline.py</font> → "
        "<font face='Courier'>py -m src.matching</font> → "
        "<font face='Courier'>py -m src.run_s2_matched</font> → "
        "<font face='Courier'>py -m src.publication_report</font>. "
        "Tables : <font face='Courier'>outputs/tables/</font>. "
        "Figures : <font face='Courier'>outputs/figures/pub_fig*.png</font>.",
        styles["body"],
    ))

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(
        "Document généré automatiquement à partir des sorties empiriques du dépôt "
        "<i>corsica_forest_resilience</i> — aucun résultat inventé.",
        styles["footer"],
    ))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    log.info("PDF → %s", out)
    return out


def main() -> Path:
    paths_list = rebuild_all_figures()
    key = {
        "context": ROOT / "outputs" / "figures" / "pub_fig00_context.png",
        "design": ROOT / "outputs" / "figures" / "pub_fig01_matched_sample.png",
        "balance": ROOT / "outputs" / "figures" / "pub_fig02_covariate_balance.png",
        "timeseries": ROOT / "outputs" / "figures" / "pub_fig03_timeseries.png",
        "trends": ROOT / "outputs" / "figures" / "pub_fig04_trends.png",
        "effects": ROOT / "outputs" / "figures" / "pub_fig05_effects.png",
    }
    for k, p in key.items():
        if not p.exists():
            log.warning("Figure manquante: %s", p)
    pdf = build_pdf(key)
    print(pdf)
    return pdf


if __name__ == "__main__":
    main()
