"""Phase 3.1A unit / sanity tests for `src/economics.py`.

Run as a script (`uv run python tests/test_economics.py`) or with pytest.
The script-mode runner exits non-zero on any failure and prints a per-test
summary table.

All tests reference `phase3_formula_lock.md` sections so failures are easy to
trace back to the locked formula.
"""
from __future__ import annotations
import math
import sys
from pathlib import Path

# Allow running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.economics import (
    amortization_schedule,
    monthly_hazard_from_pd12,
    marginal_pd_schedule,
    lifetime_expected_loss,
    expected_interest_margin,
    expected_net_profit,
    apr_tier_lookup,
    asb_one_period_profit_reference,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RESULTS = []


def _record(name, ok, detail=""):
    _RESULTS.append({"test": name, "pass": bool(ok), "detail": detail})


def assert_close(a, b, tol=1e-6, label=""):
    return abs(a - b) <= tol, f"{label}: {a} vs {b} (tol {tol})"


# ---------------------------------------------------------------------------
# 1. APR=0 amortization: total principal repaid equals loan_amount
# ---------------------------------------------------------------------------

def test_amort_zero_apr_principal_sums_to_loan():
    am = amortization_schedule(10000.0, 24, apr=0.0)
    total_principal = float(am["principal_t"].sum())
    final_balance = float(am["balance_end_t"].iloc[-1])
    ok = math.isclose(total_principal, 10000.0, rel_tol=1e-9, abs_tol=1e-6) and abs(final_balance) < 1e-6
    _record("1. APR=0 sum(principal)==loan_amount AND final_balance≈0",
            ok, f"sum={total_principal:.6f}, final_bal={final_balance:.6e}")
    return ok


# ---------------------------------------------------------------------------
# 2. APR>0 amortization: final balance ≈ 0
# ---------------------------------------------------------------------------

def test_amort_apr_positive_terminal_balance_zero():
    am = amortization_schedule(15000.0, 36, apr=0.18)
    final_balance = float(am["balance_end_t"].iloc[-1])
    ok = abs(final_balance) < 1e-3  # ~$0.001 tolerance for float roundoff
    _record("2. APR>0 final balance ≈ 0", ok, f"final_bal={final_balance:.6e}")
    return ok


# ---------------------------------------------------------------------------
# 3. Sum of marginal_PD_t over 12 months ≈ PD_12m
# ---------------------------------------------------------------------------

def test_marginal_pd_sum_12_months_equals_pd12():
    failures = []
    for pd12 in [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2]:
        sched = marginal_pd_schedule(pd12, 12)
        s = float(sched["marginal_PD_t"].sum())
        if abs(s - pd12) > 1e-9:
            failures.append((pd12, s))
    ok = not failures
    detail = "all match PD_12m within 1e-9" if ok else f"failures: {failures}"
    _record("3. sum(marginal_PD_t over 12 months) == PD_12m", ok, detail)
    return ok


# ---------------------------------------------------------------------------
# 4. LT_EL increases with PD, LGD, and loan_amount
# ---------------------------------------------------------------------------

def test_ltel_monotonic_in_pd_lgd_loanamt():
    # Vary PD
    el_lo_pd = lifetime_expected_loss(0.005, 10_000, 24, 0.65)
    el_hi_pd = lifetime_expected_loss(0.050, 10_000, 24, 0.65)
    pd_ok = el_hi_pd > el_lo_pd

    # Vary LGD
    el_lo_lgd = lifetime_expected_loss(0.02, 10_000, 24, 0.45)
    el_hi_lgd = lifetime_expected_loss(0.02, 10_000, 24, 0.85)
    lgd_ok = el_hi_lgd > el_lo_lgd

    # Vary loan_amount
    el_lo_la = lifetime_expected_loss(0.02, 5_000, 24, 0.65)
    el_hi_la = lifetime_expected_loss(0.02, 20_000, 24, 0.65)
    la_ok = el_hi_la > el_lo_la

    ok = pd_ok and lgd_ok and la_ok
    detail = (f"PD↑: {el_lo_pd:.2f}->{el_hi_pd:.2f} ({'OK' if pd_ok else 'FAIL'}); "
              f"LGD↑: {el_lo_lgd:.2f}->{el_hi_lgd:.2f} ({'OK' if lgd_ok else 'FAIL'}); "
              f"L↑: {el_lo_la:.2f}->{el_hi_la:.2f} ({'OK' if la_ok else 'FAIL'})")
    _record("4. LT_EL increases with PD, LGD, loan_amount", ok, detail)
    return ok


# ---------------------------------------------------------------------------
# 5. Expected profit increases with APR
# ---------------------------------------------------------------------------

def test_profit_increases_with_apr():
    base = dict(pd_12m=0.02, loan_amount=10_000, n_installments=24, lgd=0.65)
    p_lo = expected_net_profit(**base, apr=0.10)["Expected_Profit"]
    p_md = expected_net_profit(**base, apr=0.18)["Expected_Profit"]
    p_hi = expected_net_profit(**base, apr=0.30)["Expected_Profit"]
    ok = p_lo < p_md < p_hi
    _record("5. Expected_Profit increases with APR", ok,
            f"APR 0.10→0.18→0.30: {p_lo:.2f} → {p_md:.2f} → {p_hi:.2f}")
    return ok


# ---------------------------------------------------------------------------
# 6. Expected profit decreases with LGD
# ---------------------------------------------------------------------------

def test_profit_decreases_with_lgd():
    base = dict(pd_12m=0.02, loan_amount=10_000, n_installments=24, apr=0.20)
    p_lo_lgd = expected_net_profit(**base, lgd=0.45)["Expected_Profit"]
    p_md_lgd = expected_net_profit(**base, lgd=0.65)["Expected_Profit"]
    p_hi_lgd = expected_net_profit(**base, lgd=0.85)["Expected_Profit"]
    ok = p_lo_lgd > p_md_lgd > p_hi_lgd
    _record("6. Expected_Profit decreases with LGD", ok,
            f"LGD 0.45→0.65→0.85: {p_lo_lgd:.2f} → {p_md_lgd:.2f} → {p_hi_lgd:.2f}")
    return ok


# ---------------------------------------------------------------------------
# 7. Expected_Profit = LT_margin - LT_EL exactly (no double-counting)
# ---------------------------------------------------------------------------

def test_no_double_counting_of_ltel():
    cases = [
        dict(pd_12m=0.005, loan_amount=5_000, n_installments=12, apr=0.12, lgd=0.65),
        dict(pd_12m=0.020, loan_amount=10_000, n_installments=24, apr=0.22, lgd=0.65),
        dict(pd_12m=0.050, loan_amount=15_000, n_installments=36, apr=0.30, lgd=0.85),
    ]
    failures = []
    for c in cases:
        out = expected_net_profit(**c)
        diff = (out["LT_margin"] - out["LT_EL"]) - out["Expected_Profit"]
        if abs(diff) > 1e-9:
            failures.append((c, diff))
    ok = not failures
    _record("7. Expected_Profit == LT_margin - LT_EL exactly", ok,
            "all 3 cases identity holds within 1e-9" if ok else f"failures: {failures}")
    return ok


# ---------------------------------------------------------------------------
# 8. Revenue declines over time for an amortizing loan when APR > 0
# ---------------------------------------------------------------------------

def test_interest_revenue_declines_for_amortizing_loan():
    am = amortization_schedule(10_000.0, 24, apr=0.18)
    # interest_t should be strictly decreasing across months for French amortization
    diffs = np.diff(am["interest_t"].to_numpy())
    ok = bool((diffs < 0).all())
    _record("8. interest_t is strictly decreasing under French amortization", ok,
            f"first 6 interest values: {am['interest_t'].head(6).round(4).tolist()}")
    return ok


# ---------------------------------------------------------------------------
# Bonus: APR tier table monotonic
# ---------------------------------------------------------------------------

def test_apr_tier_monotonic():
    test_pds = [0.001, 0.0049, 0.005, 0.0099, 0.01, 0.019, 0.02, 0.049, 0.05, 0.5]
    aprs = [apr_tier_lookup(p) for p in test_pds]
    ok = all(aprs[i] <= aprs[i + 1] for i in range(len(aprs) - 1))
    _record("9. (bonus) APR tier monotonic in PD", ok,
            f"PD→APR: {list(zip(test_pds, aprs))}")
    return ok


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

def run_all():
    tests = [
        test_amort_zero_apr_principal_sums_to_loan,
        test_amort_apr_positive_terminal_balance_zero,
        test_marginal_pd_sum_12_months_equals_pd12,
        test_ltel_monotonic_in_pd_lgd_loanamt,
        test_profit_increases_with_apr,
        test_profit_decreases_with_lgd,
        test_no_double_counting_of_ltel,
        test_interest_revenue_declines_for_amortizing_loan,
        test_apr_tier_monotonic,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            _record(t.__name__, False, f"EXCEPTION: {type(e).__name__}: {e}")

    n_pass = sum(1 for r in _RESULTS if r["pass"])
    n_total = len(_RESULTS)
    print("\n" + "=" * 90)
    print("PHASE 3.1A — UNIT TESTS")
    print("=" * 90)
    for r in _RESULTS:
        mark = "PASS" if r["pass"] else "FAIL"
        print(f"  [{mark}] {r['test']}")
        if r["detail"]:
            print(f"         {r['detail']}")
    print("=" * 90)
    print(f"  {n_pass} / {n_total} tests passed")
    return n_pass == n_total


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
