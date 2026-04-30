"""
Phase 3 -- Fine-Grid Re-Sweep
===============================
Re-derives optimal thresholds from existing predictions_gini_*.parquet
using an adaptive per-Gini grid (200 steps, 0 to 1.05 * max(prob)).

Motiviation: original fixed 0.01 step leaves only 2 non-trivial
thresholds for Gini 0.30 and 7 for Gini 0.45, giving insufficient
resolution for thesis-quality uplift claims.

Outputs (no original files overwritten):
  artifacts/phase3/threshold_sweep_finegrid_gini_{level}.parquet  x4
  artifacts/phase3/main_results_finegrid.json
  artifacts/phase3/resweep_comparison_report.txt

IMPORTS: reuses compute_threshold_row + find_optimal_thresholds from
  phase3_profit_analysis.py -- profit formula is identical.

Run:
    python scripts/phase3_resweep_finegrid.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
P3_DIR    = REPO_ROOT / "artifacts" / "phase3"
SCRIPTS   = REPO_ROOT / "scripts"

# ---------------------------------------------------------------------------
# Import production functions -- profit formula MUST be identical
# ---------------------------------------------------------------------------
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

try:
    from phase3_profit_analysis import compute_threshold_row, find_optimal_thresholds
except ImportError as e:
    sys.exit(f"ERROR: cannot import from phase3_profit_analysis: {e}")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APR_BASE   = 0.20
LGD_BASE   = 0.75
N_STEPS    = 200
PAD_FACTOR = 1.05   # grid extends to 1.05 * max(prob) to capture approve-all
LEVELS     = ["raw", "0.60", "0.45", "0.30"]

# Original grid for comparison
ORIG_START = 0.01
ORIG_STOP  = 0.99
ORIG_STEP  = 0.01
ORIG_N     = 99


# ---------------------------------------------------------------------------
# Fine-grid sweep
# ---------------------------------------------------------------------------

def build_finegrid(df: pd.DataFrame) -> tuple[np.ndarray, float, float]:
    """Return (thresholds, step_min, step_max) for this Gini level."""
    max_p = float(df["prob_calibrated"].max())
    upper = max_p * PAD_FACTOR
    thresholds = np.linspace(0.0, upper, N_STEPS)
    steps = np.diff(thresholds)
    return thresholds, float(steps.min()), float(steps.max())


def sweep_finegrid(df: pd.DataFrame, thresholds: np.ndarray) -> pd.DataFrame:
    """Run compute_threshold_row for every threshold; return DataFrame."""
    rows = [compute_threshold_row(df, float(t), APR_BASE, LGD_BASE)
            for t in thresholds]
    return pd.DataFrame(rows).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def orig_thresholds_in_range(max_p: float) -> int:
    """Count original 0.01-step thresholds strictly within [0, max_p]."""
    ts = np.arange(ORIG_START, ORIG_STOP + ORIG_STEP / 2, ORIG_STEP)
    return int((ts <= max_p).sum())


def fmt_pct(v: float | None) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/A"
    return f"{v:+.4f}%"


def fmt_thresh(v: float) -> str:
    return f"{v:.6f}"


def fmt_profit(v: float) -> str:
    return f"{v:,.0f}"


def uplift_pct(rp_prof: float, rp_acc: float) -> float | None:
    if abs(rp_acc) < 1e-9:
        return None
    return (rp_prof - rp_acc) / abs(rp_acc) * 100.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Load original results for comparison
    orig_mr_path = P3_DIR / "main_results.json"
    if not orig_mr_path.exists():
        sys.exit("ERROR: main_results.json not found. Run phase3_profit_analysis.py first.")
    orig_mr = json.loads(orig_mr_path.read_text())

    report_lines: list[str] = []

    def emit(line: str = ""):
        report_lines.append(line)
        try:
            print(line)
        except UnicodeEncodeError:
            print(line.encode("ascii", errors="replace").decode("ascii"))

    def hr(c="=", w=72): return c * w

    emit("=== PHASE 3 RE-SWEEP COMPARISON (FINE GRID vs ORIGINAL) ===")
    emit()

    # -----------------------------------------------------------------------
    # GRID INFO
    # -----------------------------------------------------------------------
    emit(hr())
    emit("--- GRID INFO ---")
    emit(hr())
    emit()
    emit(f"  Original: step={ORIG_STEP}  range=[{ORIG_START},{ORIG_STOP}]  "
         f"n_thresholds={ORIG_N}")
    emit(f"  Fine:     linspace(0, max_p*{PAD_FACTOR}, {N_STEPS})  per Gini level")
    emit()
    emit(f"  {'Gini':<6}  {'max(prob)':>10}  {'orig_in_range':>14}  "
         f"{'fine_upper':>12}  {'fine_step':>12}  {'fine_in_range':>14}")
    emit(f"  {'-'*6}  {'-'*10}  {'-'*14}  {'-'*12}  {'-'*12}  {'-'*14}")

    level_data: dict = {}

    for level in LEVELS:
        pred_path = P3_DIR / f"predictions_gini_{level}.parquet"
        if not pred_path.exists():
            sys.exit(f"ERROR: {pred_path} not found.")
        df        = pd.read_parquet(pred_path)
        max_p     = float(df["prob_calibrated"].max())
        thresholds, step_min, step_max = build_finegrid(df)
        upper     = float(thresholds[-1])
        orig_in   = orig_thresholds_in_range(max_p)
        fine_step = (upper - 0.0) / (N_STEPS - 1)
        fine_in   = int((thresholds <= max_p).sum())
        emit(f"  {level:<6}  {max_p:>10.6f}  {orig_in:>14d}  "
             f"{upper:>12.6f}  {fine_step:>12.8f}  {fine_in:>14d}")
        level_data[level] = {
            "df": df, "thresholds": thresholds,
            "max_p": max_p, "upper": upper,
            "step_min": step_min, "step_max": step_max,
            "orig_in_range": orig_in, "fine_in_range": fine_in,
        }

    # -----------------------------------------------------------------------
    # SWEEPS
    # -----------------------------------------------------------------------
    emit()
    emit(hr())
    emit("--- COMPUTING FINE-GRID SWEEPS ---")
    emit(hr())

    finegrid_results: dict = {}

    for level in LEVELS:
        ld = level_data[level]
        emit(f"\n  [{level}] sweeping {N_STEPS} thresholds ...")
        sweep = sweep_finegrid(ld["df"], ld["thresholds"])

        acc_thresh, prof_thresh, acc_idx, prof_idx = find_optimal_thresholds(sweep)

        rp_acc  = float(sweep.loc[acc_idx,  "realized_profit"])
        rp_prof = float(sweep.loc[prof_idx, "realized_profit"])
        ep_prof = float(sweep.loc[prof_idx, "expected_profit"])
        ep_acc  = float(sweep.loc[acc_idx,  "expected_profit"])
        up      = uplift_pct(rp_prof, rp_acc)

        # argmax(realized) for argmax shift check
        real_idx       = int(sweep["realized_profit"].idxmax())
        real_prof_thresh = float(sweep.loc[real_idx, "threshold"])
        exp_real_gap   = round(prof_thresh - real_prof_thresh, 8)

        emit(f"    acc-opt  thresh={acc_thresh:.6f}  realized={rp_acc:,.0f}")
        emit(f"    prof-opt thresh={prof_thresh:.6f}  realized={rp_prof:,.0f}")
        emit(f"    uplift={up:+.4f}%")
        emit(f"    argmax(expected)={prof_thresh:.6f}  "
             f"argmax(realized)={real_prof_thresh:.6f}  "
             f"gap={exp_real_gap:+.8f}")

        sweep_path = P3_DIR / f"threshold_sweep_finegrid_gini_{level}.parquet"
        sweep.to_parquet(sweep_path, index=False)
        emit(f"    saved: {sweep_path.name}")

        finegrid_results[level] = {
            "accuracy_optimal_threshold":      acc_thresh,
            "profit_optimal_threshold":        prof_thresh,
            "realized_profit_at_acc_optimal":  round(rp_acc, 2),
            "realized_profit_at_prof_optimal": round(rp_prof, 2),
            "expected_profit_at_acc_optimal":  round(ep_acc, 2),
            "expected_profit_at_prof_optimal": round(ep_prof, 2),
            "profit_uplift_pct":               round(up, 6) if up is not None else None,
            "n_approved_at_acc_optimal":
                int(sweep.loc[acc_idx, "n_approved"]),
            "n_approved_at_prof_optimal":
                int(sweep.loc[prof_idx, "n_approved"]),
            "approval_rate_at_acc_optimal":
                round(float(sweep.loc[acc_idx, "approval_rate"]), 6),
            "approval_rate_at_prof_optimal":
                round(float(sweep.loc[prof_idx, "approval_rate"]), 6),
            "argmax_realized_threshold": real_prof_thresh,
            "expected_vs_realized_argmax_gap": exp_real_gap,
            "grid_info": {
                "n_steps":         N_STEPS,
                "max_threshold":   round(ld["upper"], 8),
                "step_size_min":   round(ld["step_min"], 8),
                "step_size_max":   round(ld["step_max"], 8),
                "thresholds_in_distribution_range": ld["fine_in_range"],
            },
        }

    # Save main_results_finegrid.json
    mr_out = P3_DIR / "main_results_finegrid.json"
    mr_out.write_text(json.dumps(finegrid_results, indent=2), encoding="utf-8")
    emit(f"\n  main_results_finegrid.json saved")

    # -----------------------------------------------------------------------
    # OPTIMAL THRESHOLDS COMPARISON TABLE
    # -----------------------------------------------------------------------
    emit()
    emit(hr())
    emit("--- OPTIMAL THRESHOLDS COMPARISON ---")
    emit(hr())
    emit()

    col_h = f"  {'Gini':<6}  {'Metric':<36}  {'Original':>18}  {'Fine grid':>18}  {'Delta':>14}"
    emit(col_h)
    emit("  " + "-" * (len(col_h) - 2))

    for level in LEVELS:
        fg = finegrid_results[level]
        og = orig_mr.get(level, {})

        og_prof_t   = float(og.get("profit_optimal_threshold", float("nan")))
        og_acc_t    = float(og.get("accuracy_optimal_threshold", float("nan")))
        og_rp_prof  = float(og.get("realized_profit_at_prof_optimal", float("nan")))
        og_rp_acc   = float(og.get("realized_profit_at_acc_optimal", float("nan")))
        og_up       = float(og.get("profit_uplift_pct", float("nan")))

        fg_prof_t   = fg["profit_optimal_threshold"]
        fg_acc_t    = fg["accuracy_optimal_threshold"]
        fg_rp_prof  = fg["realized_profit_at_prof_optimal"]
        fg_rp_acc   = fg["realized_profit_at_acc_optimal"]
        fg_up       = fg["profit_uplift_pct"] if fg["profit_uplift_pct"] is not None else float("nan")

        rows = [
            ("prof-opt threshold",          f"{og_prof_t:.4f}",        f"{fg_prof_t:.6f}",       f"{fg_prof_t-og_prof_t:+.6f}"),
            ("acc-opt threshold",           f"{og_acc_t:.4f}",         f"{fg_acc_t:.6f}",        f"{fg_acc_t-og_acc_t:+.6f}"),
            ("realized @ prof-opt",         f"{og_rp_prof:,.0f}",      f"{fg_rp_prof:,.0f}",     f"{fg_rp_prof-og_rp_prof:+,.0f}"),
            ("realized @ acc-opt",          f"{og_rp_acc:,.0f}",       f"{fg_rp_acc:,.0f}",      f"{fg_rp_acc-og_rp_acc:+,.0f}"),
            ("uplift %",                    f"{og_up:+.4f}%",          f"{fg_up:+.4f}%",         f"{fg_up-og_up:+.4f}pp"),
        ]
        for i, (metric, orig_v, fine_v, delta) in enumerate(rows):
            prefix = f"  {level:<6}" if i == 0 else f"  {'':6}"
            emit(f"{prefix}  {metric:<36}  {orig_v:>18}  {fine_v:>18}  {delta:>14}")
        emit()

    # -----------------------------------------------------------------------
    # KEY METRICS DELTA
    # -----------------------------------------------------------------------
    emit(hr())
    emit("--- KEY METRICS DELTA ---")
    emit(hr())
    emit()

    stability_results: dict = {}

    for level in LEVELS:
        fg = finegrid_results[level]
        og = orig_mr.get(level, {})
        og_up  = float(og.get("profit_uplift_pct", float("nan")))
        fg_up  = fg["profit_uplift_pct"] if fg["profit_uplift_pct"] is not None else float("nan")
        d_up   = fg_up - og_up if not (np.isnan(fg_up) or np.isnan(og_up)) else float("nan")

        og_pt  = float(og.get("profit_optimal_threshold",  float("nan")))
        og_at  = float(og.get("accuracy_optimal_threshold", float("nan")))
        fg_pt  = fg["profit_optimal_threshold"]
        fg_at  = fg["accuracy_optimal_threshold"]

        og_rp  = float(og.get("realized_profit_at_prof_optimal", float("nan")))
        og_ra  = float(og.get("realized_profit_at_acc_optimal",  float("nan")))
        fg_rp  = fg["realized_profit_at_prof_optimal"]
        fg_ra  = fg["realized_profit_at_acc_optimal"]

        emit(f"  [{level}]")
        emit(f"    D(prof-opt thresh)  : {fg_pt-og_pt:+.6f}")
        emit(f"    D(acc-opt thresh)   : {fg_at-og_at:+.6f}")
        emit(f"    D(uplift %)         : {d_up:+.4f}pp  *** THESIS CRITICAL ***")
        emit(f"    D(realized@prof-opt): {fg_rp-og_rp:+,.0f}")
        emit(f"    D(realized@acc-opt) : {fg_ra-og_ra:+,.0f}")

        # Stability classification
        if np.isnan(d_up):
            stab = "UNKNOWN"
        elif abs(d_up) < 2.0:
            stab = "STABLE"
        elif abs(d_up) < 10.0:
            stab = "SHIFTED"
        else:
            stab = "UNSTABLE"
        stability_results[level] = {"d_uplift": d_up, "stability": stab,
                                    "fg_up": fg_up, "og_up": og_up}
        emit(f"    Stability           : {stab}  (|D uplift|={abs(d_up):.4f}pp)")
        emit()

    # -----------------------------------------------------------------------
    # STABILITY ASSESSMENT SUMMARY
    # -----------------------------------------------------------------------
    emit(hr())
    emit("--- STABILITY ASSESSMENT ---")
    emit(hr())
    emit()
    emit(f"  {'Gini':<6}  {'Orig uplift':>12}  {'Fine uplift':>12}  "
         f"{'Delta (pp)':>12}  {'Verdict':>10}")
    emit(f"  {'-'*6}  {'-'*12}  {'-'*12}  {'-'*12}  {'-'*10}")
    for level in LEVELS:
        s = stability_results[level]
        emit(f"  {level:<6}  {s['og_up']:>12.4f}%  {s['fg_up']:>12.4f}%  "
             f"  {s['d_uplift']:>+10.4f}pp  {s['stability']:>10}")
    emit()

    # Pattern check
    emit("  Pattern check: uplift widens monotonically as Gini drops?")
    fg_uplifts = [stability_results[l]["fg_up"] for l in LEVELS]
    og_uplifts = [stability_results[l]["og_up"] for l in LEVELS]

    def is_monotone_increasing(seq):
        return all(b >= a for a, b in zip(seq, seq[1:]))

    orig_mono = is_monotone_increasing(og_uplifts)
    fine_mono = is_monotone_increasing(fg_uplifts)

    emit(f"    Original uplifts : " + "  ".join(f"{v:+.4f}%" for v in og_uplifts))
    emit(f"    Fine-grid uplifts: " + "  ".join(f"{v:+.4f}%" for v in fg_uplifts))
    emit(f"    Original monotone increasing: {orig_mono}")
    emit(f"    Fine-grid monotone increasing: {fine_mono}")
    emit()

    # Pattern verdict
    all_stable   = all(s["stability"] == "STABLE"  for s in stability_results.values())
    all_shifted  = all(s["stability"] in ("STABLE", "SHIFTED") for s in stability_results.values())
    any_unstable = any(s["stability"] == "UNSTABLE" for s in stability_results.values())
    max_delta    = max(abs(s["d_uplift"]) for s in stability_results.values())

    if not fine_mono:
        verdict = "FINDING_COLLAPSED"
        verdict_reason = ("Fine-grid uplift is NOT monotonically increasing as Gini "
                          "decreases. Pattern broken.")
    elif all_stable and max_delta < 5.0:
        verdict = "FINDING_ROBUST"
        verdict_reason = (f"Pattern preserved. All |D uplift| < 2pp. "
                          f"Max delta = {max_delta:.4f}pp < 5pp.")
    elif all_shifted and max_delta < 10.0:
        verdict = "FINDING_SHIFTED"
        verdict_reason = (f"Pattern preserved but magnitudes shifted >5pp. "
                          f"Max |D uplift| = {max_delta:.4f}pp. "
                          f"Fine-grid numbers supersede originals.")
    elif all_shifted:
        verdict = "FINDING_SHIFTED"
        verdict_reason = (f"Pattern preserved but magnitudes shifted. "
                          f"Max |D uplift| = {max_delta:.4f}pp.")
    else:
        verdict = "FINDING_COLLAPSED"
        verdict_reason = (f"One or more Gini levels UNSTABLE (|D uplift| >= 10pp). "
                          f"Max delta = {max_delta:.4f}pp.")

    # -----------------------------------------------------------------------
    # ARGMAX SHIFT CHECK
    # -----------------------------------------------------------------------
    emit(hr())
    emit("--- PROFIT-OPT ARGMAX SHIFT CHECK (expected vs realized) ---")
    emit(hr())
    emit()
    emit(f"  {'Gini':<6}  {'argmax(exp)':>14}  {'argmax(real)':>14}  "
         f"{'gap (fine)':>12}  {'gap (orig)':>12}  {'gap change':>12}")
    emit(f"  {'-'*6}  {'-'*14}  {'-'*14}  {'-'*12}  {'-'*12}  {'-'*12}")

    # Original gaps from audit (hardcoded from sweep_audit results)
    orig_gaps = {
        "raw":  0.31 - 0.28,   # argmax(exp)=0.31  argmax(real)=0.28
        "0.60": 0.24 - 0.23,   # argmax(exp)=0.24  argmax(real)=0.23
        "0.45": 0.08 - 0.08,   # same
        "0.30": 0.03 - 0.03,   # same
    }

    for level in LEVELS:
        fg    = finegrid_results[level]
        f_gap = fg["expected_vs_realized_argmax_gap"]
        o_gap = orig_gaps.get(level, float("nan"))
        d_gap = f_gap - o_gap
        emit(f"  {level:<6}  {fg['profit_optimal_threshold']:>14.6f}  "
             f"{fg['argmax_realized_threshold']:>14.6f}  "
             f"{f_gap:>+12.6f}  {o_gap:>+12.6f}  {d_gap:>+12.6f}")
    emit()
    emit("  Interpretation:")
    emit("    A positive gap = argmax(exp) picks a higher threshold than argmax(real).")
    emit("    Model OVERESTIMATES expected profit vs. realized for the marginal customers.")
    emit("    A shrinking gap with finer grid = original 0.01 step caused threshold")
    emit("    rounding artifacts. A stable gap = genuine model calibration effect.")

    # -----------------------------------------------------------------------
    # DISTRIBUTION DENSITY CHECK
    # -----------------------------------------------------------------------
    emit()
    emit(hr())
    emit("--- DISTRIBUTION DENSITY CHECK ---")
    emit(hr())
    emit()
    emit(f"  {'Gini':<6}  {'max(prob)':>10}  {'orig in range':>14}  "
         f"{'fine in range':>14}  {'resolution gain':>16}")
    emit(f"  {'-'*6}  {'-'*10}  {'-'*14}  {'-'*14}  {'-'*16}")
    for level in LEVELS:
        ld   = level_data[level]
        o_in = ld["orig_in_range"]
        f_in = ld["fine_in_range"]
        gain = f_in / o_in if o_in > 0 else float("inf")
        emit(f"  {level:<6}  {ld['max_p']:>10.6f}  {o_in:>14d}  "
             f"{f_in:>14d}  {gain:>15.1f}x")

    # -----------------------------------------------------------------------
    # CRITICAL PATTERN SUMMARY + VERDICT
    # -----------------------------------------------------------------------
    emit()
    emit(hr("="))
    emit("--- CRITICAL OUTPUT: PATTERN PRESERVATION ---")
    emit(hr("="))
    emit()
    emit(f"  Original pattern: uplift widens monotonically as Gini drops")
    emit(f"    " + "  ->  ".join(f"{l} {stability_results[l]['og_up']:+.2f}%" for l in LEVELS))
    emit(f"  Fine-grid pattern:")
    emit(f"    " + "  ->  ".join(f"{l} {stability_results[l]['fg_up']:+.2f}%" for l in LEVELS))
    emit()
    emit(f"  Direction preserved (monotone increasing): {fine_mono}")
    emit(f"  Max |D uplift| across all Gini levels    : {max_delta:.4f}pp")
    emit()

    emit(hr())
    emit("--- VERDICT ---")
    emit(hr())
    emit()
    emit(f"  [{verdict}]")
    emit()
    emit(f"  {verdict_reason}")
    emit()

    if verdict == "FINDING_ROBUST":
        emit("  -> Proceed to Phase 4 with fine-grid numbers.")
        emit("     Fine-grid numbers are preferred for thesis reporting.")
        emit("     Original results remain valid as cross-check.")
    elif verdict == "FINDING_SHIFTED":
        emit("  -> Proceed to Phase 4 with fine-grid numbers.")
        emit("     Original numbers deprecated for thesis reporting.")
        emit("     Document adaptive grid choice in methodology section.")
        emit("     Fine-grid uplift figures should be used for all tables and claims.")
    else:  # COLLAPSED
        emit("  -> STOP. Do not proceed to Phase 4.")
        emit("     Surface to human for review before continuing.")

    emit()
    emit(hr())

    # -----------------------------------------------------------------------
    # Save report
    # -----------------------------------------------------------------------
    report_path = P3_DIR / "resweep_comparison_report.txt"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n[resweep] report saved: {report_path}")
    print("[resweep] DONE")


if __name__ == "__main__":
    main()
