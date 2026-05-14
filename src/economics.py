"""
Phase 3 economic formulas — IMPLEMENTATION OF `phase3_formula_lock.md`.

Source of truth: `phase3_formula_lock.md` at the repository root. Do not
modify the formulas here without re-locking that document. Every public
function below cites the section of the lock it implements.

PUBLIC API
  - amortization_schedule(loan_amount, n_installments, apr=0.0)
  - monthly_hazard_from_pd12(pd_12m)
  - marginal_pd_schedule(pd_12m, n_installments)
  - lifetime_expected_loss(pd_12m, loan_amount, n_installments, lgd,
                            apr_for_ead=0.0, discount_annual=0.0)
  - expected_interest_margin(pd_12m, loan_amount, n_installments, apr,
                              op_cost_annual=0.0, discount_annual=0.0)
  - expected_net_profit(pd_12m, loan_amount, n_installments, apr, lgd,
                         op_cost_annual=0.0, discount_annual=0.0)
  - apr_tier_lookup(pd_12m)
  - asb_one_period_profit_reference(pd_12m, loan_amount, apr, lgd)

CONVENTIONS
  - Time index t runs 1..n_installments.
  - End-of-month discount: discount_t = 1 / (1 + discount_annual / 12) ** t.
  - PD_12m is a single calibrated 12-month forward PD; the same monthly hazard
    `h` is applied across all months 1..n_installments (hazard extrapolation).
  - All monetary inputs in the same currency unit as `loan_amount` (no scaling).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


# =============================================================================
# Section 3 of the lock — amortization schedule
# =============================================================================

def amortization_schedule(
    loan_amount: float,
    n_installments: int,
    apr: float = 0.0,
) -> pd.DataFrame:
    """Build the per-month amortization schedule.

    Implements `phase3_formula_lock.md` Section 3.

    Parameters
    ----------
    loan_amount : float
        Principal at origination.
    n_installments : int
        Tenor in months. Must be >= 1.
    apr : float
        Annual percentage rate. 0 → zero-interest (simulator default).
        > 0 → standard French amortization with monthly rate `apr / 12`.

    Returns
    -------
    DataFrame with columns
        month, balance_begin_t, scheduled_payment_t, interest_t, principal_t,
        balance_end_t
    indexed 0..n_installments-1, with `month` 1..n_installments.
    """
    if n_installments < 1:
        raise ValueError("n_installments must be >= 1")
    if loan_amount < 0:
        raise ValueError("loan_amount must be >= 0")
    if apr < 0:
        raise ValueError("apr must be >= 0")

    n = int(n_installments)
    months = np.arange(1, n + 1)
    balance_begin = np.empty(n, dtype=np.float64)
    scheduled_payment = np.empty(n, dtype=np.float64)
    interest = np.empty(n, dtype=np.float64)
    principal = np.empty(n, dtype=np.float64)
    balance_end = np.empty(n, dtype=np.float64)

    if apr == 0.0:
        # Straight-line, zero interest
        pmt = loan_amount / n
        balance_begin[:] = loan_amount * (n - (months - 1)) / n
        scheduled_payment[:] = pmt
        interest[:] = 0.0
        principal[:] = pmt
        balance_end[:] = balance_begin - principal
    else:
        r = apr / 12.0
        # French annuity payment
        pmt = loan_amount * r * (1 + r) ** n / ((1 + r) ** n - 1)
        bb = loan_amount
        for i in range(n):
            balance_begin[i] = bb
            int_i = bb * r
            prin_i = pmt - int_i
            be_i = bb - prin_i
            interest[i] = int_i
            principal[i] = prin_i
            scheduled_payment[i] = pmt
            balance_end[i] = be_i
            bb = be_i

    return pd.DataFrame({
        "month": months,
        "balance_begin_t": balance_begin,
        "scheduled_payment_t": scheduled_payment,
        "interest_t": interest,
        "principal_t": principal,
        "balance_end_t": balance_end,
    })


# =============================================================================
# Section 1 — PD horizon conversion
# =============================================================================

def monthly_hazard_from_pd12(pd_12m: float) -> float:
    """Convert a calibrated 12-month forward PD into a monthly hazard rate.

    Implements `phase3_formula_lock.md` Section 1:
        h = 1 - (1 - PD_12m) ** (1/12)
    """
    if not (0.0 <= pd_12m < 1.0):
        if pd_12m == 1.0:
            return 1.0
        raise ValueError(f"pd_12m must be in [0, 1); got {pd_12m}")
    return 1.0 - (1.0 - pd_12m) ** (1.0 / 12.0)


# =============================================================================
# Section 2 — Marginal PD schedule
# =============================================================================

def marginal_pd_schedule(pd_12m: float, n_installments: int) -> pd.DataFrame:
    """Build the survival + marginal PD schedule across t=1..n_installments.

    Implements `phase3_formula_lock.md` Section 2:
        survival_begin_t = (1 - h) ** (t - 1)
        marginal_PD_t    = survival_begin_t * h

    For n_installments > 12, the same monthly hazard `h` is applied
    (hazard-extrapolation; see lock Section 1).
    """
    if n_installments < 1:
        raise ValueError("n_installments must be >= 1")
    h = monthly_hazard_from_pd12(pd_12m)
    n = int(n_installments)
    t = np.arange(1, n + 1)
    survival_begin = (1.0 - h) ** (t - 1)
    marginal_pd = survival_begin * h
    return pd.DataFrame({
        "month": t,
        "h": np.full(n, h),
        "survival_begin_t": survival_begin,
        "marginal_PD_t": marginal_pd,
    })


# =============================================================================
# Section 5 — Lifetime Expected Loss
# =============================================================================

def lifetime_expected_loss(
    pd_12m: float,
    loan_amount: float,
    n_installments: int,
    lgd: float,
    apr_for_ead: float = 0.0,
    discount_annual: float = 0.0,
) -> float:
    """Compute Lifetime Expected Loss (LT_EL).

    Implements `phase3_formula_lock.md` Section 5:
        LT_EL = sum_t marginal_PD_t * LGD * EAD_t * discount_t

    `EAD_t = balance_begin_t` (lock Section 4) from the amortization schedule
    using `apr_for_ead` (often 0 for zero-interest simulator scenarios; can
    be set to the chosen APR for an annuity-based EAD).

    `discount_t = 1 / (1 + discount_annual/12) ** t` (lock Section 8).
    """
    if not (0.0 <= lgd <= 1.0):
        raise ValueError(f"lgd must be in [0, 1]; got {lgd}")
    pd_sched = marginal_pd_schedule(pd_12m, n_installments)
    am = amortization_schedule(loan_amount, n_installments, apr=apr_for_ead)
    n = int(n_installments)
    t = np.arange(1, n + 1)
    discount_t = 1.0 / (1.0 + discount_annual / 12.0) ** t
    el_per_month = pd_sched["marginal_PD_t"].to_numpy() * lgd * am["balance_begin_t"].to_numpy() * discount_t
    return float(el_per_month.sum())


# =============================================================================
# Section 6 — Lifetime Margin (gross of credit loss)
# =============================================================================

def expected_interest_margin(
    pd_12m: float,
    loan_amount: float,
    n_installments: int,
    apr: float,
    op_cost_annual: float = 0.0,
    discount_annual: float = 0.0,
) -> float:
    """Compute Lifetime Margin (LT_margin), gross of credit loss.

    Implements `phase3_formula_lock.md` Section 6:
        interest_revenue_t  = balance_begin_t * apr / 12
        expected_interest_t = survival_begin_t * interest_revenue_t
        op_cost_t           = survival_begin_t * loan_amount * op_cost_annual / 12
        LT_margin           = sum_t (expected_interest_t - op_cost_t) * discount_t

    Note: `LT_margin` is gross of credit loss by construction. Use
    `expected_net_profit` to subtract LT_EL once.
    """
    if apr < 0:
        raise ValueError(f"apr must be >= 0; got {apr}")
    am = amortization_schedule(loan_amount, n_installments, apr=apr)
    pd_sched = marginal_pd_schedule(pd_12m, n_installments)
    n = int(n_installments)
    t = np.arange(1, n + 1)
    discount_t = 1.0 / (1.0 + discount_annual / 12.0) ** t

    interest_revenue_t = am["balance_begin_t"].to_numpy() * apr / 12.0
    survival_begin = pd_sched["survival_begin_t"].to_numpy()
    expected_interest = survival_begin * interest_revenue_t
    op_cost_t = survival_begin * loan_amount * op_cost_annual / 12.0
    lt_margin = float(((expected_interest - op_cost_t) * discount_t).sum())
    return lt_margin


# =============================================================================
# Section 7 — Expected Net Profit
# =============================================================================

def expected_net_profit(
    pd_12m: float,
    loan_amount: float,
    n_installments: int,
    apr: float,
    lgd: float,
    op_cost_annual: float = 0.0,
    discount_annual: float = 0.0,
) -> Dict[str, float]:
    """Compute Expected_Profit = LT_margin - LT_EL.

    Implements `phase3_formula_lock.md` Section 7. Returns a dict with the
    intermediate components for traceability.

    LT_margin is computed with the exogenous APR (Section 6).
    LT_EL is computed with the same APR for the amortization-based EAD
    schedule (Sections 3-5). This keeps EAD consistent between margin and
    EL — both reference the same outstanding balance schedule.
    """
    lt_margin = expected_interest_margin(
        pd_12m=pd_12m, loan_amount=loan_amount, n_installments=n_installments,
        apr=apr, op_cost_annual=op_cost_annual, discount_annual=discount_annual,
    )
    lt_el = lifetime_expected_loss(
        pd_12m=pd_12m, loan_amount=loan_amount, n_installments=n_installments,
        lgd=lgd, apr_for_ead=apr, discount_annual=discount_annual,
    )
    return {
        "LT_margin": lt_margin,
        "LT_EL": lt_el,
        "Expected_Profit": lt_margin - lt_el,
    }


# =============================================================================
# Section 10 — APR tier lookup
# =============================================================================

# Locked tier table (see lock Section 10). DO NOT modify here without re-lock.
_APR_TIERS = (
    # (upper_bound_exclusive, apr)
    (0.005, 0.12),  # Prime
    (0.010, 0.18),  # Near-prime
    (0.020, 0.22),  # Mainstream
    (0.050, 0.26),  # Subprime
    (1.001, 0.30),  # Deep-subprime (any PD >= 0.05)
)


def apr_tier_lookup(pd_12m: float) -> float:
    """Return the locked APR for a given calibrated PD_12m.

    Implements `phase3_formula_lock.md` Section 10. Vectorized via
    `apr_tier_lookup_vec` for arrays.
    """
    if not (0.0 <= pd_12m <= 1.0):
        raise ValueError(f"pd_12m must be in [0, 1]; got {pd_12m}")
    for ub, apr in _APR_TIERS:
        if pd_12m < ub:
            return apr
    return _APR_TIERS[-1][1]  # safety fallback


def apr_tier_lookup_vec(pd_12m_array: np.ndarray) -> np.ndarray:
    """Vectorized version of `apr_tier_lookup`. Returns same-length APR array."""
    out = np.empty(len(pd_12m_array), dtype=np.float64)
    for i, pd_v in enumerate(pd_12m_array):
        out[i] = apr_tier_lookup(float(pd_v))
    return out


# =============================================================================
# Section 11 — ASB benchmark (reference only)
# =============================================================================

def asb_one_period_profit_reference(
    pd_12m: float,
    loan_amount: float,
    apr: float,
    lgd: float,
) -> float:
    """ASB single-period profit benchmark (lock Section 11).

    profit_ASB = (1 - PD_12m) * loan_amount * apr
               - PD_12m       * loan_amount * lgd

    Provided for benchmarking against the locked Lifetime formula. NOT the
    main thesis formula.
    """
    return (1.0 - pd_12m) * loan_amount * apr - pd_12m * loan_amount * lgd


# =============================================================================
# Vectorized batch helpers (Phase 3.1B production)
# =============================================================================

def _balance_fraction_schedule(n_installments: int, apr: float) -> np.ndarray:
    """Return a length-n vector of balance_begin_t / loan_amount under
    `amortization_schedule(loan_amount, n_installments, apr)`. Used to build
    the per-tenor amortization template once per (n, apr) combination.
    """
    am = amortization_schedule(1.0, n_installments, apr=apr)
    return am["balance_begin_t"].to_numpy()


def batch_lifetime_economics(
    pd_12m: np.ndarray,
    loan_amount: np.ndarray,
    n_installments: np.ndarray,
    apr: np.ndarray,
    lgd: float,
    op_cost_annual: float = 0.0,
    discount_annual: float = 0.0,
    cost_of_funds_annual: float = 0.0,
    acquisition_cost: float = 0.0,
) -> dict:
    """Compute LT_EL, LT_margin, Expected_Profit for a population.

    Vectorized for speed over rows; iterates over distinct (tenor, apr)
    combinations to use a precomputed amortization template per combo.

    Inputs are 1-D arrays of length N. `apr` may be per-row (variable) or
    constant (broadcast). `lgd`, `op_cost_annual`, `discount_annual`,
    `cost_of_funds_annual`, `acquisition_cost` are scalars (per-cell).

    **Phase 3.2 extensions** (preserve back-compat at zero):

    - `cost_of_funds_annual`: subtracted from APR before computing
      interest revenue. Net interest formula:
          net_interest_t = balance_begin_t * max(APR - COF, 0) / 12
      `LT_margin` becomes net of funding cost.

    - `acquisition_cost`: one-time fixed cost at origination (no discount,
      no survival weighting; treated as paid at t=0 regardless of outcome).
      Subtracted from final Expected_Profit per loan.

    Returns dict with arrays of length N:
        LT_EL, LT_margin (net of COF, op_cost), Expected_Profit (net of all costs)
    """
    pd_12m = np.asarray(pd_12m, dtype=np.float64)
    L = np.asarray(loan_amount, dtype=np.float64)
    n_arr = np.asarray(n_installments, dtype=int)
    apr = np.asarray(apr, dtype=np.float64) if np.ndim(apr) else np.full_like(L, apr, dtype=np.float64)

    if not (0.0 <= lgd <= 1.0):
        raise ValueError(f"lgd must be in [0, 1]; got {lgd}")
    if cost_of_funds_annual < 0:
        raise ValueError(f"cost_of_funds_annual must be >= 0; got {cost_of_funds_annual}")
    if acquisition_cost < 0:
        raise ValueError(f"acquisition_cost must be >= 0; got {acquisition_cost}")

    # Net APR after funding cost, floored at 0
    apr_net = np.maximum(apr - cost_of_funds_annual, 0.0)

    N = len(L)
    LT_EL = np.zeros(N, dtype=np.float64)
    LT_margin = np.zeros(N, dtype=np.float64)

    h = 1.0 - (1.0 - pd_12m) ** (1.0 / 12.0)
    # Group by (tenor, apr_gross, apr_net) — gross drives EAD via amort, net drives revenue
    unique_pairs = pd.DataFrame({
        "n": n_arr,
        "a": np.round(apr, 6),
        "an": np.round(apr_net, 6),
    }).drop_duplicates()

    for _, (n, a, an) in unique_pairs.iterrows():
        n = int(n); a = float(a); an = float(an)
        mask = (
            (n_arr == n)
            & (np.round(apr, 6) == a)
            & (np.round(apr_net, 6) == an)
        )
        if not mask.any():
            continue
        idx = np.flatnonzero(mask)
        bal_frac = _balance_fraction_schedule(n, a)  # uses gross APR for amortization
        t_arr = np.arange(1, n + 1)
        discount_t = 1.0 / (1.0 + discount_annual / 12.0) ** t_arr
        h_sub = h[idx]
        L_sub = L[idx]
        log1mh = np.log1p(-h_sub)
        survival_begin = np.exp(np.outer(log1mh, t_arr - 1))
        marginal_pd = survival_begin * h_sub[:, None]
        balance_begin = np.outer(L_sub, bal_frac)

        # LT_EL: uses gross-APR EAD (consistent with amortization schedule)
        el_per_month = marginal_pd * lgd * balance_begin * discount_t[None, :]
        LT_EL[idx] = el_per_month.sum(axis=1)

        # Net interest revenue uses APR_net
        net_interest = balance_begin * (an / 12.0)
        op_cost_t = survival_begin * L_sub[:, None] * (op_cost_annual / 12.0)
        margin_per_month = (survival_begin * net_interest - op_cost_t) * discount_t[None, :]
        LT_margin[idx] = margin_per_month.sum(axis=1)

    profit = LT_margin - LT_EL - acquisition_cost
    return {
        "LT_EL": LT_EL,
        "LT_margin": LT_margin,
        "Expected_Profit": profit,
    }


def apr_tier_lookup_capped(pd_12m: float, cap: float | None = None) -> float:
    """Return locked tier APR clipped at `cap`. `cap=None` → uncapped (locked)."""
    a = apr_tier_lookup(pd_12m)
    return min(a, cap) if cap is not None else a


def apr_tier_lookup_capped_vec(pd_12m_arr: np.ndarray, cap: float | None = None) -> np.ndarray:
    """Vectorized capped tier lookup."""
    a = apr_tier_lookup_vec(pd_12m_arr)
    return np.minimum(a, cap) if cap is not None else a


def asb_one_period_profit_reference_vec(
    pd_12m: np.ndarray,
    loan_amount: np.ndarray,
    apr: np.ndarray,
    lgd: float,
) -> np.ndarray:
    """Vectorized ASB benchmark profit (lock Section 11). Same formula:
    `(1 - pd) * L * apr - pd * L * lgd`."""
    pd_12m = np.asarray(pd_12m, dtype=np.float64)
    L = np.asarray(loan_amount, dtype=np.float64)
    apr = np.asarray(apr, dtype=np.float64) if np.ndim(apr) else np.full_like(L, apr, dtype=np.float64)
    return (1.0 - pd_12m) * L * apr - pd_12m * L * lgd
