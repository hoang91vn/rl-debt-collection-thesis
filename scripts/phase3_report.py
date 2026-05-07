"""
Phase 3 -- Report Generator
=============================
Reads all Phase 3 artifacts and writes artifacts/phase3/phase3_report.txt.

Sections:
  1. Configuration summary
  2. PD model validation
  3. Score calibration experiment
  4. Main results (base APR=0.20, LGD=0.75)
  5. Sensitivity analysis
  6. Thesis-ready observation block
  7. Known limitations

Run:
    python scripts/phase3_report.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT   = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "artifacts" / "phase3" / "run_config.json"
P3_DIR      = REPO_ROOT / "artifacts" / "phase3"
OUT_PATH    = P3_DIR / "phase3_report.txt"


def load_json(path):
    if not path.exists():
        sys.exit(f"ERROR: required file not found: {path}")
    with open(path) as f:
        return json.load(f)


def _hr(char="=", width=70):
    return char * width


def _section(title, char="="):
    return f"\n{_hr(char)}\n{title}\n{_hr(char)}"


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def section_config(cfg):
    d    = cfg["data"]
    feat = cfg["features"]
    pdm  = cfg["pd_model"]
    cal  = cfg["calibration"]
    sc   = cfg["score_calibration_experiment"]
    pr   = cfg["profit"]
    co   = cfg["cutoff_optimization"]

    lines = [_section("SECTION 1 -- CONFIGURATION SUMMARY")]
    lines.append(f"ABT path     : {d['abt_path']}")
    lines.append(f"Population   : {d['population_filter']}")
    lines.append(f"Train months : {d['train_months'][0]} .. "
                 f"{d['train_months'][-1]} "
                 f"({len(d['train_months'])} periods)")
    lines.append(f"OOT months   : {d['oot_months'][0]} .. "
                 f"{d['oot_months'][-1]} "
                 f"({len(d['oot_months'])} periods)")
    lines.append("")
    lines.append(f"Numeric features  : {', '.join(feat['numeric'])}")
    lines.append(f"Categorical feat  : {', '.join(feat['categorical'])}")
    lines.append("")
    lines.append(f"PD model          : {pdm['algorithm']}")
    lines.append(f"  params          : {pdm['params']}")
    lines.append(f"  imputation      : {pdm['imputation']}")
    lines.append(f"Calibration       : {cal['method']}  "
                 f"holdout={cal['holdout_fraction']}")
    lines.append("")
    lines.append(f"Noise method      : {sc['method']}")
    lines.append(f"Target Ginis      : {sc['target_ginis']}")
    lines.append(f"Sigma search      : {sc['sigma_search']}")
    lines.append("")
    lines.append(f"APR base / sens   : {pr['apr']['base']} / "
                 f"{pr['apr']['sensitivity']}")
    lines.append(f"LGD base / sens   : {pr['lgd']['base']} / "
                 f"{pr['lgd']['sensitivity']}")
    lines.append(f"Threshold grid    : {co['threshold_grid']}")
    lines.append(f"Accuracy crit     : {co['accuracy_criterion']}")
    lines.append(f"Profit crit       : {co['profit_criterion']}")
    return "\n".join(lines)


def section_pd_validation(v):
    lines = [_section("SECTION 2 -- PD MODEL VALIDATION")]
    lines.append(f"OOT rows             : {v['n_oot_rows']:,}")
    lines.append(f"Train default rate   : {v['train_default_rate']*100:.4f}%")
    lines.append(f"OOT default rate     : {v['oot_default_rate']*100:.4f}%")
    lines.append("")
    lines.append(f"Gini OOT (raw)       : {v['gini_oot_raw']:.4f}")
    lines.append(f"Gini OOT (calibrated): {v['gini_oot_calibrated']:.4f}")
    lines.append(f"Gini shift           : {v['gini_shift']:+.4f}")
    lines.append("")
    lines.append(f"Mean predicted (cal) : {v['mean_predicted_cal']:.6f}")
    lines.append(f"Mean actual OOT      : {v['mean_actual_oot']:.6f}")
    lines.append(f"Calibration dev (pp) : {v['calibration_deviation_pp']:.4f}pp")
    lines.append("")
    lines.append(f"Brier score          : {v['brier_score']:.6f}")
    lines.append(f"Platt coef / intercept: {v['platt_coef']:.4f} / "
                 f"{v['platt_intercept']:.4f}")
    if v.get("warnings"):
        lines.append("")
        lines.append("Warnings:")
        for w in v["warnings"]:
            lines.append(f"  ! {w}")
    return "\n".join(lines)


def section_calibration(log):
    lines = [_section("SECTION 3 -- SCORE CALIBRATION EXPERIMENT")]
    # Header
    header = (
        f"{'Gini level':<12} {'Target':>8} {'Achieved':>10} "
        f"{'Sigma':>8} {'Mean Pred':>10} {'Mean Actual':>12}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    order = ["raw", "0.60", "0.45", "0.30"]
    for k in order:
        e = log.get(k)
        if e is None:
            continue
        tgt   = "raw" if e["target_gini"] == "raw" else f"{e['target_gini']:.2f}"
        ach   = f"{e['achieved_gini']:.4f}"
        sig   = f"{e['sigma']:.4f}"
        mpred = f"{e['mean_pred']:.6f}"
        mact  = f"{e['mean_actual']:.6f}"
        lines.append(
            f"{k:<12} {tgt:>8} {ach:>10} {sig:>8} {mpred:>10} {mact:>12}"
        )
        if e.get("warnings"):
            for w in e["warnings"]:
                lines.append(f"    ! {w}")
    return "\n".join(lines)


def section_main_results(mr):
    lines = [
        _section("SECTION 4 -- MAIN RESULTS "
                 "(base case APR=0.20, LGD=0.75)")
    ]
    col_w = [8, 16, 16, 12, 15, 14]
    header = (
        f"{'Gini':<{col_w[0]}} {'Acc-Opt Thresh':>{col_w[1]}} "
        f"{'Prof-Opt Thresh':>{col_w[2]}} {'Divergence':>{col_w[3]}} "
        f"{'Profit Uplift':>{col_w[4]}} {'Approval Rate':>{col_w[5]}}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for level in ["raw", "0.60", "0.45", "0.30"]:
        r = mr.get(level)
        if r is None:
            continue
        uplift = (f"{r['profit_uplift_pct']:+.2f}%"
                  if r.get("profit_uplift_pct") is not None else "N/A")
        row = (
            f"{level:<{col_w[0]}} "
            f"{r['accuracy_optimal_threshold']:>{col_w[1]}.4f} "
            f"{r['profit_optimal_threshold']:>{col_w[2]}.4f} "
            f"{r['threshold_divergence']:>+{col_w[3]}.4f} "
            f"{uplift:>{col_w[4]}} "
            f"{r['approval_rate_at_prof_optimal']:>{col_w[5]}.2%}"
        )
        lines.append(row)

    lines.append("")
    lines.append("Realized profit at optimal thresholds:")
    for level in ["raw", "0.60", "0.45", "0.30"]:
        r = mr.get(level)
        if r is None:
            continue
        lines.append(
            f"  [{level}] acc-opt: {r['realized_profit_at_acc_optimal']:>12,.0f}"
            f"   prof-opt: {r['realized_profit_at_prof_optimal']:>12,.0f}"
        )
    return "\n".join(lines)


def section_sensitivity(sens_df, mr):
    lines = [_section("SECTION 5 -- SENSITIVITY ANALYSIS")]
    lines.append("Profit-optimal threshold across APR x LGD grid:")

    for level in ["raw", "0.60", "0.45", "0.30"]:
        sub = sens_df[sens_df["gini_level"] == level]
        if sub.empty:
            continue
        lines.append(f"\n  Gini level = {level}")
        aprs = sorted(sub["apr"].unique())
        lgds = sorted(sub["lgd"].unique())

        # Header row
        hdr = f"  {'LGD':>6} | " + " | ".join(f"APR={a:.0%}" for a in aprs)
        lines.append(hdr)
        lines.append("  " + "-" * (len(hdr) - 2))
        for lgd in lgds:
            vals = []
            for apr in aprs:
                cell = sub[(sub["apr"] == apr) & (sub["lgd"] == lgd)]
                if not cell.empty:
                    t = float(cell["profit_optimal_threshold"].iloc[0])
                    vals.append(f"{t:.2f}")
                else:
                    vals.append("N/A")
            lines.append(f"  {lgd:.2f}   | " + " | ".join(
                f"  {v:<8}" for v in vals
            ))
    return "\n".join(lines)


def section_observations(mr, log):
    lines = [_section("SECTION 6 -- THESIS-READY OBSERVATIONS")]
    lines.append("(Descriptive summary only; no interpretive claims.)")
    lines.append("")

    # Divergence magnitude
    lines.append("6.1  Threshold divergence (profit-optimal minus accuracy-optimal):")
    for level in ["raw", "0.60", "0.45", "0.30"]:
        r = mr.get(level)
        if r is None:
            continue
        div = r["threshold_divergence"]
        lines.append(f"  [{level}] {div:+.4f}  "
                     f"(acc={r['accuracy_optimal_threshold']:.4f}, "
                     f"prof={r['profit_optimal_threshold']:.4f})")

    lines.append("")

    # Direction of divergence as Gini decreases
    levels = ["raw", "0.60", "0.45", "0.30"]
    divs = [mr[l]["threshold_divergence"] for l in levels if l in mr]
    if len(divs) >= 2:
        first, last = divs[0], divs[-1]
        if last > first:
            direction = "INCREASES (profit-optimal shifts looser relative to acc-optimal)"
        elif last < first:
            direction = "DECREASES (profit-optimal converges toward acc-optimal)"
        else:
            direction = "UNCHANGED"
        lines.append("6.2  Direction of divergence as Gini decreases:")
        lines.append(f"     {direction}")
        lines.append(f"     Divergence at raw Gini:  {divs[0]:+.4f}")
        lines.append(f"     Divergence at Gini 0.30: {divs[-1]:+.4f}")

    lines.append("")

    # Profit uplift magnitude
    lines.append("6.3  Profit uplift at profit-optimal vs accuracy-optimal threshold:")
    for level in ["raw", "0.60", "0.45", "0.30"]:
        r = mr.get(level)
        if r is None:
            continue
        uplift = r.get("profit_uplift_pct")
        if uplift is not None:
            lines.append(f"  [{level}] {uplift:+.2f}%")
        else:
            lines.append(f"  [{level}] N/A")

    return "\n".join(lines)


def section_limitations():
    lines = [_section("SECTION 7 -- KNOWN LIMITATIONS")]
    items = [
        ("L1", "Simulator produces deterministic demographic->default mapping. "
               "Raw Gini ~0.80 is higher than real-world consumer credit (0.30-0.50)."),
        ("L2", "Profit formula assumes full-interest revenue over loan duration; "
               "ignores amortization and early repayment."),
        ("L3", "Zero-interest simulator: loan_amount = installment x n_installments. "
               "loan_amount and installment are perfectly collinear within any "
               "fixed-duration group."),
        ("L4", "n_installments=12 group excluded (structural default impossibility "
               "under write-off rule due_installments==12). Population restricted "
               "to 24-month and 36-month loans."),
        ("L5", "Target window: default in months 13-24 only. Longer-horizon defaults "
               "not modeled."),
        ("L6", "Platt re-calibration in score calibration experiment uses OOT data "
               "for fitting (80% subsample). Calibrated probabilities for those rows "
               "are partially in-sample."),
        ("L7", "Score calibration via Gaussian logit noise is an approximation. "
               "Achieved Gini may deviate slightly from target."),
        ("L8", "Sensitivity analysis covers APR in [0.15, 0.30] and LGD in "
               "[0.60, 0.90]. Results outside this range are extrapolated."),
    ]
    for code, text in items:
        lines.append(f"  {code}: {text}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cfg      = load_json(CONFIG_PATH)
    valid    = load_json(P3_DIR / "pd_model_validation.json")
    cal_log  = load_json(P3_DIR / "calibration_experiment_log.json")
    mr       = load_json(P3_DIR / "main_results.json")

    sens_path = P3_DIR / "sensitivity_apr_lgd.parquet"
    if not sens_path.exists():
        sys.exit(f"ERROR: {sens_path} not found.")
    sens_df = pd.read_parquet(sens_path)

    sections = [
        f"=== PHASE 3 REPORT ===",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        section_config(cfg),
        "",
        section_pd_validation(valid),
        "",
        section_calibration(cal_log),
        "",
        section_main_results(mr),
        "",
        section_sensitivity(sens_df, mr),
        "",
        section_observations(mr, cal_log),
        "",
        section_limitations(),
        "",
    ]
    report = "\n".join(sections)

    P3_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(f"[report] saved: {OUT_PATH}")
    print()
    print(report)


if __name__ == "__main__":
    main()
