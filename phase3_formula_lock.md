# Phase 3 Formula Lock

**Status**: LOCKED. Source of truth for `src/economics.py`. Formulas are not
to be invented or modified without an explicit re-lock.

**Origin**: This document memorialises the locked decisions stated explicitly
in the user's Phase 3.1A task prompt (2026-05-08). Sections 1-9 quote
verbatim or paraphrase the prompt; Section 10 fills in concrete tier values
that match the Phase 3.0 audit recommendations the user accepted.

---

## 1. PD horizon

PD scores are **calibrated 12-month forward PDs**, not lifetime PDs.
Conversion to monthly hazard:

```
h = 1 - (1 - PD_12m) ** (1/12)
```

For loans with `n_installments > 12`, the same monthly hazard `h` is applied
across all months 1..n_installments. This is the conservative
*hazard-extrapolation* choice (alternative would be to cap at 12 months).
Validation Step 3 (tenor diagnostic) checks whether this is empirically
supportable; results inform whether 24- and 36-month loans are kept in the
economics population.

## 2. Marginal PD schedule

```
survival_begin_t = (1 - h) ** (t - 1)        for t = 1, 2, ..., n_installments
marginal_PD_t    = survival_begin_t * h
```

By construction `sum_{t=1..12} marginal_PD_t == PD_12m` (within float
tolerance). Validation Step 2 unit-tests this identity.

## 3. Amortization (zero-interest simulator; APR exogenous)

The simulator is **zero-interest** (Phase 3.0 schema audit Check 3:
`installment * n_installments / loan_amount` ratio = 1.000000 ± 0.000000).
APR is therefore exogenous to the simulator and applied in the economic
formulas only.

For `apr = 0`:
```
balance_begin_t      = loan_amount * (n_installments - (t - 1)) / n_installments
scheduled_payment_t  = loan_amount / n_installments
interest_t           = 0
principal_t          = scheduled_payment_t
balance_end_t        = balance_begin_t - principal_t
```

For `apr > 0` (standard French amortization, monthly rate `r = apr / 12`):
```
M = loan_amount * r * (1 + r) ** n / ((1 + r) ** n - 1)
balance_begin_1 = loan_amount
for t = 1..n:
    interest_t      = balance_begin_t * r
    principal_t     = M - interest_t
    balance_end_t   = balance_begin_t - principal_t
    balance_begin_(t+1) = balance_end_t
```

`balance_end_n` should be ≈ 0 (validation Step 2 unit-tests this).

## 4. EAD

```
EAD_t = balance_begin_t
```

Locked. EAD at default in month t is the **beginning-of-month outstanding
balance** of month t. (For a zero-APR loan, this is the strictly decreasing
straight-line schedule; for APR > 0, it follows the French amortization
schedule.)

## 5. Lifetime Expected Loss

```
LT_EL = sum_{t=1..n_installments} marginal_PD_t * LGD * EAD_t * discount_t
```

Where `discount_t` is defined in Section 8.

## 6. Lifetime Margin (gross of credit loss)

```
interest_revenue_t   = balance_begin_t * apr / 12
expected_interest_t  = survival_begin_t * interest_revenue_t
op_cost_t            = survival_begin_t * loan_amount * op_cost_annual / 12
LT_margin            = sum_{t=1..n_installments} (expected_interest_t - op_cost_t) * discount_t
```

`LT_margin` is **gross of credit loss** by construction. The credit loss is
deducted exactly once in Section 7.

## 7. Expected Net Profit

```
Expected_Profit = LT_margin - LT_EL
```

**Do NOT subtract LT_EL twice.** `LT_margin` already excludes credit loss
(it is gross of it); subtracting `LT_EL` once gives net expected profit.

## 8. Discount factor convention

Cash flows in month `t` are discounted as:

```
discount_t = 1 / (1 + discount_annual / 12) ** t
```

End-of-month convention (cash flow occurs at end of month t; t=1 is the first
month after origination, hence discounted by one month at month 1).

For `discount_annual = 0`, all `discount_t = 1` (base case).

## 9. Base case parameters

```
op_cost_annual   = 0.00
discount_annual  = 0.00
lgd              = 0.65   (recommended base from Phase 3.0 audit;
                            Phase 3.1B sensitivity grid: {0.45, 0.55, 0.65, 0.75, 0.85})
```

Sensitivity grids on `apr`, `lgd`, `op_cost_annual`, `discount_annual` are
declared separately in Phase 3.1B and 3.2 specs.

## 10. APR tier table (locked)

Risk-priced tiers based on calibrated PD_12m (5 tiers, monotonic):

| Band | Condition on PD_12m | APR |
|:----:|:--------------------|----:|
| Prime | `PD_12m < 0.005` | **0.12** |
| Near-prime | `0.005 <= PD_12m < 0.010` | **0.18** |
| Mainstream | `0.010 <= PD_12m < 0.020` | **0.22** |
| Subprime | `0.020 <= PD_12m < 0.050` | **0.26** |
| Deep-subprime | `PD_12m >= 0.050` | **0.30** |

Function: `apr_tier_lookup(pd_12m) -> apr` returns the locked APR for that
PD bucket. Phase 3.1B will add a flat-APR sensitivity (e.g., 18% / 22% across
the whole portfolio) as an alternative regime.

## 11. ASB benchmark formula (reference only — NOT the main thesis formula)

```
profit_ASB = (1 - default_flag_12m) * loan_amount * apr
           - default_flag_12m       * loan_amount * lgd
```

Single-period; no tenor; no marginal PD schedule. Used only as a benchmark
in validation reports. The main thesis formula is `Expected_Profit` from
Section 7.

## 12. Pinning summary

| Concept | Locked value |
|---------|--------------|
| PD-to-hazard | `h = 1 - (1 - PD_12m) ** (1/12)` |
| Marginal PD at month t | `(1 - h) ** (t - 1) * h` |
| EAD at month t | `balance_begin_t` |
| Interest revenue at month t | `balance_begin_t * apr / 12` |
| LT_EL | `sum marginal_PD_t * LGD * EAD_t * discount_t` |
| LT_margin | `sum survival_begin_t * (interest_revenue_t - op_cost_t) * discount_t` |
| Expected_Profit | `LT_margin - LT_EL` |
| Base op_cost_annual | 0.00 |
| Base discount_annual | 0.00 |
| Base LGD | 0.65 |
| APR scheme | tiered (Section 10) |
