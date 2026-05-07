"""
Phase 3 -- Profit Analysis
============================
Dual cut-off optimisation (accuracy-optimal vs profit-optimal) for each
Gini level, plus APR x LGD sensitivity analysis.

For each Gini level:
  - Sweep threshold grid 0.01..0.99 step 0.01
  - Compute: classification metrics (Youden's J), realized profit,
    expected profit
  - Find accuracy-optimal (max Youden's J) and profit-optimal (max
    expected profit) thresholds
  - Save full sweep as threshold_sweep_gini_{level}.parquet

Sensitivity grid: base case APR x LGD combinations.

Run:
    python scripts/phase3_profit_analysis.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

REPO_ROOT   = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "artifacts" / "phase3" / "run_config.json"
P3_DIR      = REPO_ROOT / "artifacts" / "phase3"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config():
    if not CONFIG_PATH.exists():
        sys.exit("ERROR: run_config.json not found.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def gini_from_predictions(y_true, y_score):
    return 2.0 * roc_auc_score(y_true, y_score) - 1.0


def compute_threshold_row(df, threshold, apr, lgd):
    """
    Compute profit + classification metrics at a single threshold.
    'approved' = predicted non-default = prob_calibrated < threshold.
    """
    n_total = len(df)
    y       = df["y_true"].values
    p       = df["prob_calibrated"].values
    loans   = df["loan_amount"].values.astype(float)
    n_inst  = df["n_installments"].values.astype(float)

    approved = p < threshold
    n_approved = int(approved.sum())

    # Classification metrics (default = positive class)
    # Positive = default (y=1); rejected when prob >= threshold
    y_pred_positive = (~approved).astype(int)   # reject = classify as default
    tp = int(((y == 1) & (y_pred_positive == 1)).sum())
    fp = int(((y == 0) & (y_pred_positive == 1)).sum())
    fn = int(((y == 1) & (y_pred_positive == 0)).sum())
    tn = int(((y == 0) & (y_pred_positive == 0)).sum())

    n_pos = int(y.sum())
    n_neg = n_total - n_pos
    tpr   = tp / n_pos if n_pos > 0 else 0.0
    fpr   = fp / n_neg if n_neg > 0 else 0.0
    youden_j = tpr - fpr

    if n_approved == 0:
        return {
            "threshold":             threshold,
            "n_approved":            0,
            "approval_rate":         0.0,
            "default_rate_approved": float("nan"),
            "tpr":                   tpr,
            "fpr":                   fpr,
            "youden_j":              youden_j,
            "realized_profit":       0.0,
            "expected_profit":       0.0,
        }

    mask  = approved
    y_ap  = y[mask]
    p_ap  = p[mask]
    ln_ap = loans[mask]
    ni_ap = n_inst[mask]
    dur   = ni_ap / 12.0      # duration in years

    # Realized profit (actual outcomes)
    revenue_realized = (1 - y_ap)  * apr * ln_ap * dur
    loss_realized    = y_ap        * lgd * ln_ap
    realized_profit  = float((revenue_realized - loss_realized).sum())

    # Expected profit (using predicted PD)
    revenue_exp = (1 - p_ap) * apr * ln_ap * dur
    loss_exp    = p_ap       * lgd * ln_ap
    expected_profit = float((revenue_exp - loss_exp).sum())

    return {
        "threshold":             threshold,
        "n_approved":            n_approved,
        "approval_rate":         n_approved / n_total,
        "default_rate_approved": float(y_ap.mean()),
        "tpr":                   tpr,
        "fpr":                   fpr,
        "youden_j":              youden_j,
        "realized_profit":       realized_profit,
        "expected_profit":       expected_profit,
    }


def sweep_thresholds(df, apr, lgd, grid_cfg):
    """Return a DataFrame with one row per threshold."""
    start = grid_cfg["start"]
    stop  = grid_cfg["stop"]
    step  = grid_cfg["step"]
    thresholds = np.arange(start, stop + step / 2, step)
    thresholds = np.round(thresholds, 4)
    rows = [compute_threshold_row(df, t, apr, lgd) for t in thresholds]
    return pd.DataFrame(rows)


def find_optimal_thresholds(sweep_df):
    """Return (acc_opt_thresh, profit_opt_thresh) from sweep DataFrame."""
    # Accuracy-optimal: argmax Youden's J
    acc_idx  = sweep_df["youden_j"].idxmax()
    # Profit-optimal: argmax expected_profit
    prof_idx = sweep_df["expected_profit"].idxmax()
    return (
        float(sweep_df.loc[acc_idx,  "threshold"]),
        float(sweep_df.loc[prof_idx, "threshold"]),
        int(acc_idx),
        int(prof_idx),
    )


def gini_label_to_str(label):
    """'raw' -> 'raw', 0.6 -> '0.60', etc."""
    if label == "raw":
        return "raw"
    return f"{float(label):.2f}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cfg      = load_config()
    np.random.seed(cfg["reproducibility"]["global_seed"])

    grid_cfg = cfg["cutoff_optimization"]["threshold_grid"]
    targets  = cfg["score_calibration_experiment"]["target_ginis"]
    apr_base = cfg["profit"]["apr"]["base"]
    lgd_base = cfg["profit"]["lgd"]["base"]
    apr_sens = cfg["profit"]["apr"]["sensitivity"]
    lgd_sens = cfg["profit"]["lgd"]["sensitivity"]

    main_results    = {}
    sensitivity_rows = []

    for target in targets:
        label = gini_label_to_str(target)
        parq  = P3_DIR / f"predictions_gini_{label}.parquet"
        if not parq.exists():
            sys.exit(f"ERROR: {parq} not found. Run phase3_score_calibration.py first.")

        df = pd.read_parquet(parq)
        y  = df["y_true"].values.astype(int)
        p  = df["prob_calibrated"].values

        achieved_gini = gini_from_predictions(y, p)
        print(f"\n[profit] Gini level={label}  "
              f"achieved Gini={achieved_gini:.4f}  rows={len(df):,}")

        # ----- Base-case sweep ----------------------------------------
        sweep = sweep_thresholds(df, apr_base, lgd_base, grid_cfg)
        sweep["gini_level"] = label

        acc_thresh, prof_thresh, acc_idx, prof_idx = find_optimal_thresholds(sweep)

        rp_acc  = float(sweep.loc[acc_idx,  "realized_profit"])
        rp_prof = float(sweep.loc[prof_idx, "realized_profit"])

        uplift_pct = (
            (rp_prof - rp_acc) / abs(rp_acc) * 100
            if abs(rp_acc) > 0 else float("nan")
        )
        divergence = round(prof_thresh - acc_thresh, 4)

        print(f"  acc-optimal  thresh={acc_thresh:.2f}  "
              f"realized_profit={rp_acc:,.0f}")
        print(f"  prof-optimal thresh={prof_thresh:.2f}  "
              f"realized_profit={rp_prof:,.0f}")
        print(f"  divergence={divergence:+.4f}  "
              f"profit_uplift={uplift_pct:+.2f}%")

        sweep.to_parquet(
            P3_DIR / f"threshold_sweep_gini_{label}.parquet", index=False
        )

        main_results[label] = {
            "achieved_gini":                    round(achieved_gini, 6),
            "accuracy_optimal_threshold":       acc_thresh,
            "profit_optimal_threshold":         prof_thresh,
            "threshold_divergence":             divergence,
            "realized_profit_at_acc_optimal":   round(rp_acc,  2),
            "realized_profit_at_prof_optimal":  round(rp_prof, 2),
            "profit_uplift_pct":                round(uplift_pct, 4)
                                                if uplift_pct == uplift_pct
                                                else None,
            "n_approved_at_acc_optimal":
                int(sweep.loc[acc_idx,  "n_approved"]),
            "n_approved_at_prof_optimal":
                int(sweep.loc[prof_idx, "n_approved"]),
            "approval_rate_at_acc_optimal":
                round(float(sweep.loc[acc_idx,  "approval_rate"]), 4),
            "approval_rate_at_prof_optimal":
                round(float(sweep.loc[prof_idx, "approval_rate"]), 4),
        }

        # ----- Sensitivity grid: APR x LGD ----------------------------
        for apr in apr_sens:
            for lgd in lgd_sens:
                sw = sweep_thresholds(df, apr, lgd, grid_cfg)
                _, pt, _, pi = find_optimal_thresholds(sw)
                row = {
                    "gini_level":             label,
                    "apr":                    apr,
                    "lgd":                    lgd,
                    "profit_optimal_threshold": pt,
                    "realized_profit":        round(float(sw.loc[pi, "realized_profit"]), 2),
                    "approval_rate":          round(float(sw.loc[pi, "approval_rate"]), 4),
                }
                sensitivity_rows.append(row)

    # Save results
    (P3_DIR / "main_results.json").write_text(
        json.dumps(main_results, indent=2), encoding="utf-8"
    )
    print(f"\n[profit] main_results.json saved")

    sens_df = pd.DataFrame(sensitivity_rows)
    sens_df.to_parquet(P3_DIR / "sensitivity_apr_lgd.parquet", index=False)
    print(f"[profit] sensitivity_apr_lgd.parquet saved "
          f"({len(sens_df)} rows)")
    print("[profit] DONE")


if __name__ == "__main__":
    main()
