"""
Phase 4.2 -- Thesis Visualization Suite
=========================================
Generates 9 figures for the Results chapter.

KEY STRUCTURAL FINDING (framing throughout):
  profit-optimal threshold >= max(prob_calibrated) at ALL Gini levels
  => profit-optimal strategy = APPROVE ALL loans
  => "uplift" = profit gained by approving everyone vs applying accuracy filter

Figures produced:
  fig01_roc_curves.{pdf,png}
  fig02_profit_curves.{pdf,png}
  fig03_uplift_ci.{pdf,png}             [HEADLINE]
  fig04_threshold_divergence.{pdf,png}
  fig05_sensitivity_heatmap.{pdf,png}
  fig06_pd_distribution.{pdf,png}
  fig07_calibration_reliability.{pdf,png}
  fig08_threshold_cv.{pdf,png}
  fig09_profit_comparison.{pdf,png}

Run:
    python scripts/phase4_visualization.py

Outputs: artifacts/phase4/figures/
"""
from __future__ import annotations

import hashlib
import json
import sys
import traceback
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                          # headless -- must precede pyplot import

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import roc_auc_score, roc_curve

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
P3_DIR    = REPO_ROOT / "artifacts" / "phase3"
P4_DIR    = REPO_ROOT / "artifacts" / "phase4"
FIG_DIR   = P4_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LEVELS = ["raw", "0.60", "0.45", "0.30"]
LEVEL_LABELS = {
    "raw":  "Raw (Gini~0.80)",
    "0.60": "Gini~0.60",
    "0.45": "Gini~0.45",
    "0.30": "Gini~0.30",
}

# Viridis palette -- dark purple (raw/best) -> bright yellow (0.30/worst)
GINI_PALETTE = {
    "raw":  "#440154",
    "0.60": "#3b528b",
    "0.45": "#21918c",
    "0.30": "#fde725",
}

# Actual model parameters from run_config.json / phase3_profit_analysis.py
APR_BASE = 0.20
LGD_BASE = 0.75

DPI        = 300
ERROR_LOG  = FIG_DIR / "error_log.txt"
INDEX_FILE = FIG_DIR / "figure_index.txt"

# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def apply_thesis_style() -> None:
    """Apply consistent thesis-grade matplotlib style."""
    for name in ["seaborn-v0_8-whitegrid", "seaborn-whitegrid", "seaborn"]:
        try:
            plt.style.use(name)
            break
        except OSError:
            continue

    plt.rcParams.update({
        "font.family":       "DejaVu Sans",
        "font.size":         11,
        "axes.titlesize":    12,
        "axes.labelsize":    11,
        "xtick.labelsize":   9,
        "ytick.labelsize":   9,
        "legend.fontsize":   9,
        "figure.dpi":        DPI,
        "savefig.dpi":       DPI,
        "savefig.bbox":      "tight",
        "axes.spines.top":   False,
        "axes.spines.right": False,
    })


def save_figure(fig: plt.Figure, name: str) -> None:
    """Save figure as PNG (300 dpi) and PDF (vector)."""
    fig.savefig(FIG_DIR / f"{name}.png", dpi=DPI, bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.pdf",            bbox_inches="tight")
    plt.close(fig)


def _log_error(name: str, exc: Exception) -> None:
    with open(ERROR_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"\n{'='*60}\nFIGURE: {name}\n")
        traceback.print_exc(file=fh)
    print(f"  [SKIPPED] {name}: {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Data loader  (called once; passed as dict to all builders)
# ---------------------------------------------------------------------------

def load_all_data() -> dict:
    d: dict = {}
    d["predictions"]  = {lv: pd.read_parquet(P3_DIR / f"predictions_gini_{lv}.parquet")
                         for lv in LEVELS}
    d["sweep_fine"]   = {lv: pd.read_parquet(P3_DIR / f"threshold_sweep_finegrid_gini_{lv}.parquet")
                         for lv in LEVELS}
    d["mr_fine"]      = json.loads((P3_DIR / "main_results_finegrid.json").read_text())
    d["mr_orig"]      = json.loads((P3_DIR / "main_results.json").read_text())
    d["cal_log"]      = json.loads((P3_DIR / "calibration_experiment_log.json").read_text())
    d["sensitivity"]  = pd.read_parquet(P3_DIR / "sensitivity_apr_lgd.parquet")
    d["ci_summary"]   = json.loads((P4_DIR / "bootstrap_ci_summary.json").read_text())
    d["boot_samples"] = {lv: pd.read_parquet(P4_DIR / f"bootstrap_samples_gini_{lv}.parquet")
                         for lv in LEVELS}
    d["max_prob"]     = {lv: float(d["predictions"][lv]["prob_calibrated"].max())
                         for lv in LEVELS}
    return d


# ===========================================================================
# Fig 01 -- ROC Curves
# ===========================================================================

def build_fig01_roc(data: dict) -> plt.Figure:
    """ROC curves for all four Gini degradation levels."""
    fig, ax = plt.subplots(figsize=(6, 5))

    for lv in LEVELS:
        pred    = data["predictions"][lv]
        fpr, tpr, _ = roc_curve(pred["y_true"], pred["prob_calibrated"])
        auc_val = float(roc_auc_score(pred["y_true"], pred["prob_calibrated"]))
        gini_v  = 2 * auc_val - 1
        ax.plot(fpr, tpr, color=GINI_PALETTE[lv], lw=1.8,
                label=f"{LEVEL_LABELS[lv]}  AUC={auc_val:.3f}  Gini={gini_v:.3f}")

    ax.plot([0, 1], [0, 1], "k--", lw=0.8, alpha=0.45, label="Random classifier")
    ax.set_xlabel("False Positive Rate  (reject non-defaulters)")
    ax.set_ylabel("True Positive Rate  (reject defaulters)")
    ax.set_title("ROC Curves by Gini Degradation Level")
    ax.legend(loc="lower right", framealpha=0.92, fontsize=8.5)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    return fig


# ===========================================================================
# Fig 02 -- Profit Curves  (2 x 2)
# ===========================================================================

def build_fig02_profit(data: dict) -> plt.Figure:
    """Expected-profit curves with acc-opt and approve-all boundary annotations."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    for ax, lv in zip(axes.flatten(), LEVELS):
        sw   = data["sweep_fine"][lv]
        mr   = data["mr_fine"][lv]
        mxp  = data["max_prob"][lv]
        acc  = mr["accuracy_optimal_threshold"]

        ax.plot(sw["threshold"], sw["expected_profit"] / 1e6,
                color=GINI_PALETTE[lv], lw=1.8, label="Expected profit")

        ax.axvline(acc, color="steelblue", lw=1.4, linestyle="--",
                   label=f"Acc-opt  t={acc:.3f}")
        ax.axvline(mxp, color="crimson",   lw=1.4, linestyle=":",
                   label=f"max(p)={mxp:.3f}  [prof-opt boundary]")

        ax.set_xlim(0, mxp * 1.05)
        ax.set_xlabel("Classification Threshold")
        ax.set_ylabel("Expected Profit (M USD)")
        ax.set_title(f"{LEVEL_LABELS[lv]}\n"
                     f"acc-opt={acc:.3f}  |  prof-opt >= max(p)={mxp:.3f} [approve-all]",
                     fontsize=10)
        ax.legend(fontsize=8, framealpha=0.88)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"{v:.0f}M"))

    fig.suptitle(
        "Expected-Profit Curves: profit-optimal threshold >= max(predicted PD)\n"
        "=> profit-optimal strategy = APPROVE ALL  (APR=20%, LGD=75%)",
        fontsize=12, y=1.01,
    )
    fig.tight_layout()
    return fig


# ===========================================================================
# Fig 03 -- Uplift CI Bar Chart  (HEADLINE)
# ===========================================================================

def build_fig03_uplift_ci(data: dict) -> plt.Figure:
    """HEADLINE: Approve-all profit uplift vs accuracy-optimal, 95% bootstrap CI."""
    mr  = data["mr_fine"]
    ci  = data["ci_summary"]

    point_est = [mr[lv]["profit_uplift_pct"]          for lv in LEVELS]
    ci_lo     = [ci[lv]["uplift_pct"]["ci_lower"]      for lv in LEVELS]
    ci_hi     = [ci[lv]["uplift_pct"]["ci_upper"]      for lv in LEVELS]
    verdicts  = [ci[lv].get("uplift_verdict", "N/A")   for lv in LEVELS]

    err_lo = [pe - lo for pe, lo in zip(point_est, ci_lo)]
    err_hi = [hi - pe for hi, pe in zip(ci_hi, point_est)]
    x      = np.arange(len(LEVELS))

    fig, ax = plt.subplots(figsize=(7, 5))

    ax.bar(x, point_est, color=[GINI_PALETTE[lv] for lv in LEVELS],
           width=0.55, alpha=0.85, edgecolor="white", linewidth=0.8)
    ax.errorbar(x, point_est, yerr=[err_lo, err_hi],
                fmt="none", color="black", capsize=6, lw=1.5, capthick=1.5)

    top_margin = max(err_hi) * 0.18
    for xi, (pe, v) in enumerate(zip(point_est, verdicts)):
        short = (v
                 .replace("STAT_SIG_AND_MEANINGFUL", "SS+M")
                 .replace("STAT_SIG_SMALL_EFFECT",   "SS")
                 .replace("NOT_SIGNIFICANT",          "NS"))
        ax.text(xi, pe + top_margin,
                f"{pe:.1f}%\n[{short}]",
                ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([LEVEL_LABELS[lv] for lv in LEVELS])
    ax.set_ylabel("Profit Uplift vs Accuracy-Optimal Filter (%)")
    ax.set_title(
        "Approve-All (profit-optimal boundary) vs Accuracy-Optimal Threshold\n"
        "Uplift widens monotonically as discriminative power degrades\n"
        "95% bootstrap CI  |  1 000 stratified resamples  |  SS+M = CI_lower > 5pp",
        fontsize=10,
    )
    ax.axhline(0, color="black", lw=0.8, linestyle="--", alpha=0.45)
    ax.axhline(5, color="grey",  lw=0.7, linestyle=":",  alpha=0.45,
               label="5 pp practical significance threshold")
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=8, framealpha=0.88)
    fig.tight_layout()
    return fig


# ===========================================================================
# Fig 04 -- Threshold Divergence with CI bands
# ===========================================================================

def build_fig04_threshold_divergence(data: dict) -> plt.Figure:
    """Acc-opt vs prof-opt thresholds across Gini levels with 95% CI bands."""
    ci   = data["ci_summary"]
    mr   = data["mr_fine"]
    mxp  = data["max_prob"]

    acc_pt  = [mr[lv]["accuracy_optimal_threshold"]  for lv in LEVELS]
    acc_lo  = [ci[lv]["acc_opt_thr"]["ci_lower"]     for lv in LEVELS]
    acc_hi  = [ci[lv]["acc_opt_thr"]["ci_upper"]     for lv in LEVELS]

    prof_pt = [mr[lv]["profit_optimal_threshold"]    for lv in LEVELS]
    prof_lo = [ci[lv]["prof_opt_thr"]["ci_lower"]    for lv in LEVELS]
    prof_hi = [ci[lv]["prof_opt_thr"]["ci_upper"]    for lv in LEVELS]

    max_probs = [mxp[lv] for lv in LEVELS]
    x = np.arange(len(LEVELS))

    fig, ax = plt.subplots(figsize=(7, 5))

    # Acc-opt
    ax.plot(x, acc_pt, "o-", color="steelblue", lw=1.8, ms=7,
            label="Acc-opt threshold")
    ax.fill_between(x, acc_lo, acc_hi, color="steelblue", alpha=0.18,
                    label="Acc-opt 95% CI")

    # Prof-opt (approve-all boundary)
    ax.plot(x, prof_pt, "s-", color="crimson", lw=1.8, ms=7,
            label="Prof-opt threshold (approve-all boundary)")
    ax.fill_between(x, prof_lo, prof_hi, color="crimson", alpha=0.18,
                    label="Prof-opt 95% CI")

    # max(prob) markers
    ax.scatter(x, max_probs, marker="x", color="black", s=75, zorder=5,
               label="max(prob_calibrated)")

    ax.set_xticks(x)
    ax.set_xticklabels([LEVEL_LABELS[lv] for lv in LEVELS])
    ax.set_ylabel("Threshold Value")
    ax.set_title(
        "Threshold Divergence Across Gini Degradation Levels\n"
        "Prof-opt >= max(p) at every level => approve-all remains structural\n"
        "Shaded bands = 95% bootstrap CI",
        fontsize=10,
    )
    ax.legend(framealpha=0.92, fontsize=8.5)
    fig.tight_layout()
    return fig


# ===========================================================================
# Fig 05 -- APR x LGD Sensitivity Heatmaps  (2 x 2)
# ===========================================================================

def build_fig05_sensitivity_heatmap(data: dict) -> plt.Figure:
    """Profit sensitivity to APR and LGD under approve-all strategy."""
    sens = data["sensitivity"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    for ax, lv in zip(axes.flatten(), LEVELS):
        sub   = sens[sens["gini_level"] == lv].copy()
        pivot = sub.pivot(index="lgd", columns="apr", values="realized_profit") / 1e6
        pivot = pivot.reindex(index=sorted(pivot.index, reverse=True))  # LGD high->low

        # Format index/columns as percentages for display
        pivot.index   = [f"{v:.0%}" for v in pivot.index]
        pivot.columns = [f"{v:.0%}" for v in pivot.columns]

        sns.heatmap(
            pivot,
            ax=ax,
            annot=True, fmt=".1f",
            cmap="YlOrRd",
            cbar_kws={"label": "Realized Profit (M USD)", "shrink": 0.85},
            linewidths=0.5,
            annot_kws={"size": 9},
        )
        ax.set_title(f"{LEVEL_LABELS[lv]}\n(profit-opt = approve-all for all param values)",
                     fontsize=10)
        ax.set_xlabel("APR")
        ax.set_ylabel("LGD")
        ax.tick_params(axis="x", rotation=0)
        ax.tick_params(axis="y", rotation=0)

        # Bold-border the base case cell (APR=20%, LGD=75%)
        # After formatting, APR "20%" -> column index 1, LGD "75%" -> row index 1
        try:
            col_idx = list(pivot.columns).index("20%")
            row_idx = list(pivot.index).index("75%")
            ax.add_patch(plt.Rectangle(
                (col_idx, row_idx), 1, 1,
                fill=False, edgecolor="navy", lw=2.5, zorder=5,
            ))
        except ValueError:
            pass

    fig.suptitle(
        f"Profit Sensitivity: APR x LGD Combinations (Realized Profit, Approve-All Strategy)\n"
        f"Base case: APR={APR_BASE:.0%}, LGD={LGD_BASE:.0%}  [navy border]  "
        f"All 48 cells => profit-opt = approve-all",
        fontsize=11, y=1.01,
    )
    fig.tight_layout()
    return fig


# ===========================================================================
# Fig 06 -- PD Distribution  (1 x 4 row)
# ===========================================================================

def build_fig06_pd_distribution(data: dict) -> plt.Figure:
    """Predicted PD distributions per Gini level with threshold annotations."""
    mr  = data["mr_fine"]
    mxp = data["max_prob"]

    fig, axes = plt.subplots(1, 4, figsize=(12, 4), sharey=False)

    for ax, lv in zip(axes, LEVELS):
        pred  = data["predictions"][lv]["prob_calibrated"]
        acc   = mr[lv]["accuracy_optimal_threshold"]
        mp    = mxp[lv]
        sigma = data["cal_log"][lv]["sigma"]

        ax.hist(pred, bins=60, color=GINI_PALETTE[lv], alpha=0.75, edgecolor="none",
                density=True)

        ax.axvline(acc, color="steelblue", lw=1.4, linestyle="--",
                   label=f"acc-opt\n{acc:.3f}")
        ax.axvline(mp,  color="crimson",   lw=1.4, linestyle=":",
                   label=f"max(p)\n{mp:.3f}")

        ymax = ax.get_ylim()[1]

        # Annotate approve-all structural finding
        ax.text(mp * 0.48, ymax * 0.83,
                "prof-opt\n>= max(p)\n[approve-all]",
                fontsize=7, ha="center", color="crimson", alpha=0.85)

        ax.set_xlabel("prob_calibrated")
        ax.set_ylabel("Density" if ax is axes[0] else "")
        ax.set_title(f"{LEVEL_LABELS[lv]}\nsigma={sigma:.3f}", fontsize=9)
        ax.legend(fontsize=7, loc="upper right", framealpha=0.85)

    fig.suptitle(
        "Predicted PD Distributions  |  Blue dashed=acc-opt  |  Red dotted=max(p)=prof-opt boundary\n"
        "Gaussian logit noise compresses score range; prof-opt boundary always at distribution edge",
        fontsize=10,
    )
    fig.tight_layout()
    return fig


# ===========================================================================
# Fig 07 -- Calibration Reliability Diagram
# ===========================================================================

def build_fig07_calibration(data: dict) -> plt.Figure:
    """Reliability diagram: predicted PD vs actual default rate (10 equal-freq bins)."""
    N_BINS = 10
    fig, ax = plt.subplots(figsize=(6, 5))

    for lv in LEVELS:
        pred   = data["predictions"][lv].copy()
        sigma  = data["cal_log"][lv]["sigma"]
        pred["bin"] = pd.qcut(pred["prob_calibrated"], q=N_BINS, duplicates="drop")
        grp = (
            pred.groupby("bin", observed=True)
            .agg(mean_pred=("prob_calibrated", "mean"),
                 actual_dr =("y_true", "mean"),
                 n         =("y_true", "count"))
            .dropna()
        )
        ax.plot(grp["mean_pred"], grp["actual_dr"],
                "o-", color=GINI_PALETTE[lv], lw=1.6, ms=5,
                label=f"{LEVEL_LABELS[lv]}  (sigma={sigma:.2f})")

    # Reference lines
    ref_max = 0.35
    ax.plot([0, ref_max], [0, ref_max], "k--", lw=0.8, alpha=0.45,
            label="Perfect calibration")
    # OOT default rate reference
    oot_dr = data["cal_log"]["raw"]["mean_actual"]
    ax.axhline(oot_dr, color="grey", lw=0.8, linestyle=":", alpha=0.6,
               label=f"OOT default rate ({oot_dr:.4f})")

    ax.set_xlabel("Mean Predicted PD (prob_calibrated)")
    ax.set_ylabel("Actual Default Rate in Bin")
    ax.set_title(
        "Calibration Reliability Diagram  (10 equal-frequency bins)\n"
        "Raw: train DR=2.76% vs OOT DR=1.29% => known overestimation\n"
        "Platt scaling (sigma>0) restores mean prediction to OOT rate",
        fontsize=10,
    )
    ax.legend(framealpha=0.92, fontsize=8.5)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    return fig


# ===========================================================================
# Fig 08 -- Threshold Stability (CV)
# ===========================================================================

def build_fig08_threshold_cv(data: dict) -> plt.Figure:
    """Coefficient of Variation for optimal thresholds from 1 000 bootstrap resamples."""
    boot = data["boot_samples"]

    acc_cv, prof_cv = [], []
    for lv in LEVELS:
        bs = boot[lv]
        a_mean = float(bs["acc_opt_thr"].mean())
        a_std  = float(bs["acc_opt_thr"].std())
        p_mean = float(bs["prof_opt_thr"].mean())
        p_std  = float(bs["prof_opt_thr"].std())
        acc_cv.append( a_std / a_mean  if a_mean  != 0 else float("nan"))
        prof_cv.append(p_std / p_mean  if p_mean  != 0 else float("nan"))

    x     = np.arange(len(LEVELS))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 5))

    ax.bar(x - width / 2, acc_cv,  width, label="Acc-opt CV",
           color="steelblue", alpha=0.82, edgecolor="white")
    ax.bar(x + width / 2, prof_cv, width, label="Prof-opt CV (approve-all boundary)",
           color="crimson",   alpha=0.82, edgecolor="white")

    ax.axhline(0.30, color="black", lw=1.0, linestyle="--", alpha=0.55,
               label="CV=0.30 stability boundary")

    for xi, (ac, pc) in enumerate(zip(acc_cv, prof_cv)):
        if not np.isnan(ac):
            ax.text(xi - width / 2, ac  + 0.004,  f"{ac:.3f}",
                    ha="center", va="bottom", fontsize=8)
        if not np.isnan(pc):
            ax.text(xi + width / 2, pc  + 0.0005, f"{pc:.4f}",
                    ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([LEVEL_LABELS[lv] for lv in LEVELS])
    ax.set_ylabel("Coefficient of Variation  (std / mean)")
    ax.set_title(
        "Threshold Stability: CV from 1 000 Bootstrap Resamples\n"
        "CV < 0.30 => well-identified | Prof-opt very stable (tightly clustered at max(p))\n"
        "Acc-opt CV rises as Gini degrades (noise widens optimal region)",
        fontsize=10,
    )
    ax.legend(framealpha=0.92, fontsize=8.5)
    fig.tight_layout()
    return fig


# ===========================================================================
# Fig 09 -- Profit Comparison: Acc-opt vs Approve-All  (grouped bars + CI)
# ===========================================================================

def build_fig09_profit_comparison(data: dict) -> plt.Figure:
    """Grouped bars: realized profit at acc-opt vs approve-all, with 95% CI."""
    ci  = data["ci_summary"]
    mr  = data["mr_fine"]

    acc_pt  = [mr[lv]["realized_profit_at_acc_optimal"]  / 1e6 for lv in LEVELS]
    prof_pt = [mr[lv]["realized_profit_at_prof_optimal"] / 1e6 for lv in LEVELS]

    acc_lo  = [ci[lv]["realized_profit_acc"]["ci_lower"]  / 1e6 for lv in LEVELS]
    acc_hi  = [ci[lv]["realized_profit_acc"]["ci_upper"]  / 1e6 for lv in LEVELS]
    prof_lo = [ci[lv]["realized_profit_prof"]["ci_lower"] / 1e6 for lv in LEVELS]
    prof_hi = [ci[lv]["realized_profit_prof"]["ci_upper"] / 1e6 for lv in LEVELS]

    acc_err_lo  = [pt - lo for pt, lo in zip(acc_pt,  acc_lo)]
    acc_err_hi  = [hi - pt for hi, pt in zip(acc_hi,  acc_pt)]
    prof_err_lo = [pt - lo for pt, lo in zip(prof_pt, prof_lo)]
    prof_err_hi = [hi - pt for hi, pt in zip(prof_hi, prof_pt)]

    x     = np.arange(len(LEVELS))
    width = 0.35

    fig, ax = plt.subplots(figsize=(7, 5))

    ax.bar(x - width / 2, acc_pt,  width, label="Accuracy-optimal threshold",
           color="steelblue", alpha=0.82, edgecolor="white")
    ax.errorbar(x - width / 2, acc_pt, yerr=[acc_err_lo, acc_err_hi],
                fmt="none", color="black", capsize=5, lw=1.3, capthick=1.3)

    ax.bar(x + width / 2, prof_pt, width, label="Profit-optimal  (approve-all boundary)",
           color="crimson",   alpha=0.82, edgecolor="white")
    ax.errorbar(x + width / 2, prof_pt, yerr=[prof_err_lo, prof_err_hi],
                fmt="none", color="black", capsize=5, lw=1.3, capthick=1.3)

    # Annotate % uplift above each approve-all bar
    max_hi  = max(pt + hi for pt, hi in zip(prof_pt, prof_err_hi))
    offset  = (max_hi - min(acc_pt)) * 0.025
    for xi, (ac, pr) in enumerate(zip(acc_pt, prof_pt)):
        uplift_pct = (pr - ac) / abs(ac) * 100
        ax.annotate(
            f"+{uplift_pct:.1f}%",
            xy=(xi + width / 2, pr + prof_err_hi[xi]),
            xytext=(0, 5), textcoords="offset points",
            ha="center", va="bottom", fontsize=8.5,
            color="crimson", fontweight="bold",
        )

    ax.set_xticks(x)
    ax.set_xticklabels([LEVEL_LABELS[lv] for lv in LEVELS])
    ax.set_ylabel("Realized Profit (M USD)")
    ax.set_title(
        "Realized Profit: Approve-All vs Accuracy-Optimal Filter\n"
        "95% bootstrap CI  |  Uplift widens monotonically with Gini degradation\n"
        "(Accuracy filter increasingly destroys profit as discriminative power falls)",
        fontsize=10,
    )
    ax.legend(framealpha=0.92, fontsize=9)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:.0f}M"))
    # Ensure bars start from a sensible floor
    ylo = min(acc_lo) * 0.97
    ax.set_ylim(bottom=ylo)
    fig.tight_layout()
    return fig


# ===========================================================================
# Reproducibility hash
# ===========================================================================

def compute_png_hashes() -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        for p in sorted(FIG_DIR.glob("*.png"))
    }


# ===========================================================================
# Figure index writer
# ===========================================================================

def write_figure_index(results: list[dict]) -> None:
    lines = [
        "FIGURE INDEX",
        "=" * 72,
        "Phase 4.2 -- Thesis Visualization Suite",
        f"Output dir: artifacts/phase4/figures/",
        "",
        "STRUCTURAL FRAMING:",
        "  profit-optimal threshold >= max(prob_calibrated) at ALL Gini levels",
        "  => profit-optimal strategy = APPROVE ALL",
        "  => APR=20%, LGD=75% => break-even PD ~34.8% > max(prob)~31% (raw)",
        "",
    ]
    for r in results:
        lines += [
            "=" * 72,
            f"FILE   : {r['name']}.{{png,pdf}}",
            f"STATUS : {r['status']}",
            f"CAPTION: {r['caption']}",
            f"SOURCE : {r['source']}",
        ]
        if r.get("note"):
            lines.append(f"NOTE   : {r['note']}")
        lines.append("")

    INDEX_FILE.write_text("\n".join(lines), encoding="utf-8")


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    apply_thesis_style()

    print("=" * 60)
    print("Phase 4.2 -- Thesis Visualization Suite")
    print("=" * 60)
    print()
    print("Loading artifacts ...", flush=True)
    data = load_all_data()
    print("  All artifacts loaded OK.")
    print()

    # Clear old error log
    if ERROR_LOG.exists():
        ERROR_LOG.unlink()

    figures = [
        # (stem_name,  builder_fn,  caption,  source_files,  note_or_None)
        (
            "fig01_roc_curves",
            build_fig01_roc,
            "ROC curves for four Gini degradation levels (sigma=0 / 1.875 / 2.969 / 5.0). "
            "AUC and Gini coefficient annotated per curve.",
            "phase3/predictions_gini_{raw,0.60,0.45,0.30}.parquet",
            None,
        ),
        (
            "fig02_profit_curves",
            build_fig02_profit,
            "Expected-profit curves from fine-grid threshold sweep (200 steps). "
            "Blue dashed: accuracy-optimal threshold. Red dotted: max(prob_calibrated) = "
            "profit-optimal boundary (approve-all). Profit is monotonically maximised at "
            "the right boundary in all four panels.",
            "phase3/threshold_sweep_finegrid_gini_*.parquet + main_results_finegrid.json",
            "profit-optimal threshold > max(prob) => approve-all at every Gini level",
        ),
        (
            "fig03_uplift_ci",
            build_fig03_uplift_ci,
            "HEADLINE FIGURE. Profit uplift (%) from approve-all vs accuracy-optimal strategy, "
            "with 95% percentile bootstrap CI (1 000 stratified resamples). Uplift is "
            "statistically significant and practically meaningful (CI lower > 5pp) at all levels.",
            "phase3/main_results_finegrid.json + phase4/bootstrap_ci_summary.json",
            "SS+M = STAT_SIG_AND_MEANINGFUL (CI_lower > 5pp)",
        ),
        (
            "fig04_threshold_divergence",
            build_fig04_threshold_divergence,
            "Accuracy-optimal and profit-optimal thresholds across Gini levels with 95% CI bands. "
            "Crosses mark max(prob_calibrated). Prof-opt always equals or exceeds max(prob), "
            "confirming the approve-all finding is structural.",
            "phase3/main_results_finegrid.json + phase4/bootstrap_ci_summary.json",
            None,
        ),
        (
            "fig05_sensitivity_heatmap",
            build_fig05_sensitivity_heatmap,
            "Realized profit (M USD) under profit-optimal (approve-all) strategy across 48 "
            "APR x LGD parameter combinations. Navy border: base case APR=20%, LGD=75%. "
            "All 48 combinations retain approve-all as optimal.",
            "phase3/sensitivity_apr_lgd.parquet",
            "approval_rate=1.0 at profit-optimal for all sensitivity combinations",
        ),
        (
            "fig06_pd_distribution",
            build_fig06_pd_distribution,
            "Predicted PD distributions per Gini level (density histogram). "
            "Blue dashed: accuracy-optimal threshold. Red dotted: max(prob_calibrated) = "
            "profit-optimal boundary. Gaussian logit noise progressively compresses scores.",
            "phase3/predictions_gini_*.parquet + main_results_finegrid.json",
            None,
        ),
        (
            "fig07_calibration_reliability",
            build_fig07_calibration,
            "Reliability diagram (10 equal-frequency bins). Perfect calibration = diagonal. "
            "Raw level overestimates PD due to train/OOT default rate gap (2.76% vs 1.29%). "
            "Platt re-calibration restores mean prediction to OOT rate for sigma>0 levels.",
            "phase3/predictions_gini_*.parquet + calibration_experiment_log.json",
            "Known calibration deviation: train DR=2.76%, OOT DR=1.29% (+1.47pp, documented)",
        ),
        (
            "fig08_threshold_cv",
            build_fig08_threshold_cv,
            "Coefficient of Variation (CV = std/mean) for acc-opt and prof-opt thresholds "
            "across 1 000 bootstrap resamples. CV < 0.30 = well-identified. Prof-opt is "
            "highly stable (tightly clustered at max(p)); acc-opt CV increases with noise.",
            "phase4/bootstrap_samples_gini_*.parquet",
            None,
        ),
        (
            "fig09_profit_comparison",
            build_fig09_profit_comparison,
            "Grouped bars: realized profit (M USD) at accuracy-optimal vs approve-all threshold, "
            "with 95% bootstrap CI. Percentage uplift annotated above each approve-all bar. "
            "Uplift increases monotonically: +14.7% (raw) to +58.2% (Gini~0.30).",
            "phase3/main_results_finegrid.json + phase4/bootstrap_ci_summary.json",
            None,
        ),
    ]

    results = []
    for name, builder, caption, source, note in figures:
        print(f"  Building {name} ...", end=" ", flush=True)
        try:
            fig = builder(data)
            save_figure(fig, name)
            status = "OK"
            print("OK")
        except Exception as exc:
            _log_error(name, exc)
            status = f"SKIPPED ({type(exc).__name__}: {exc})"

        results.append(dict(name=name, status=status,
                            caption=caption, source=source, note=note))

    # Write figure index
    write_figure_index(results)
    print()

    # Reproducibility hashes
    print("Computing PNG hashes ...", flush=True)
    hashes = compute_png_hashes()
    hash_path = FIG_DIR / "png_hashes.json"
    hash_path.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print(f"  {len(hashes)} hashes written -> {hash_path.name}")
    print()

    # Summary
    ok_n   = sum(1 for r in results if r["status"] == "OK")
    skip_n = len(results) - ok_n
    print("=" * 60)
    print(f"  Figures generated : {ok_n} / {len(results)}")
    if skip_n:
        print(f"  Skipped           : {skip_n}  (see error_log.txt)")
    print(f"  Output dir        : artifacts/phase4/figures/")
    print("=" * 60)
    print()

    # File listing
    print("Files in artifacts/phase4/figures/:")
    total_kb = 0.0
    for fp in sorted(FIG_DIR.iterdir()):
        kb = fp.stat().st_size / 1024
        total_kb += kb
        print(f"  {fp.name:<52}  {kb:>8.1f} KB")
    print(f"  {'TOTAL':<52}  {total_kb:>8.1f} KB")
    print()

    if skip_n == 0:
        print("All figures generated successfully.")
    else:
        print(f"WARNING: {skip_n} figure(s) skipped. Check error_log.txt.")
        sys.exit(1)


if __name__ == "__main__":
    main()
