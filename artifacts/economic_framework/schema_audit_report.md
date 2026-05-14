# Phase 3.0 — Economic Schema Audit Report

**Date**: 2026-05-08 02:23
**Inputs**: `modeling_abt.parquet` (534K × 2236), `modeling_feature_catalog.csv`,
`pd_scores.parquet`, `final_data_800d_60m_p00/{transactions,accounts,collection_actions}.csv`

**Goal**: Determine whether the current ABT supports tenor-aware Lifetime EL and
Lifetime Net Margin, and whether the existing ASB profit function (in
`scripts/enrich_thesis_abt.py`) is reusable for Phase 3.

**Result**: ✅ All required inputs are PRESENT or DERIVABLE. ASB profit function
is PARTIALLY REUSABLE as a single-period reference; Phase 3 must extend it for
tenor-aware lifetime calculations.

---
## Check 1 — Loan amount / exposure

**Selected**: `loan_amount`
- dtype: `int64`
- non-null count: 534,314 / 534,314
- mean: 4,856.3695, median: 3,816.0000, std: 3,503.8618
- min: 1,044, max: 34,236
- p1: 1,116.0000, p5: 1,332.0000, p25: 2,412.0000, p75: 6,120.0000, p95: 12,132.0000, p99: 17,348.8800
- `allowed_for_profit` in catalog: True
- Other present loan candidates: ['loan_amount']

**Decision**: PRESENT. Use `loan_amount` as principal exposure at origination.

## Check 2 — Tenor / installment count

**Selected**: `n_installments`
- dtype: `int64`, non-null: 534,314
- value counts:

  | tenor | n | % |
  |------:|--:|--:|
  | 12 | 298,346 | 55.84% |
  | 24 | 135,115 | 25.29% |
  | 36 | 100,853 | 18.88% |

- unique tenors: 3
- 12-month loans present: True (n=298,346)

**Decision**: tenor VARIES with 12, 24, 36 (or similar). Tenor-aware LT EL is meaningful.
- Other tenor candidates: ['n_installments']

## Check 3 — Installment + zero-interest

**Selected**: `installment`
- dtype: `int64`, non-null: 534,314
- mean: 248.2501, median: 223.0000, std: 120.5698
- min: 87, max: 1,113

**Zero-interest test**: `installment × n_installments / loan_amount` ratio:
- mean: 1.000000
- std:  0.000000
- min:  1.000000
- max:  1.000000
- p1:   1.000000
- p99:  1.000000

**Decision**: simulator is **ZERO-INTEREST** (ratio ≈ 1.0 with negligible variance).
Implied APR from amortization = 0%. No revenue field exists.

## Check 4 — APR / interest rate

**MISSING**: no apr/interest_rate/pricing field in ABT.

**Decision**: simulator has **NO explicit APR**. Must use exogenous APR for thesis economics.
Recommendation: use APR tiers by PD band (e.g., low-risk 12%, mid 18%, high 25%).

## Check 5 — EAD / outstanding balance

**Behavioral columns found**:
- `act_paid_installments_m1..m12`: 95 cols (one per month offset)
- `act_due_m1..m12`: 97 cols

**EAD derivation**: zero-interest simulator → at offset m, `EAD_m = loan_amount × (n_installments - act_paid_installments_m) / n_installments`

**Choices for Phase 3**:
- Origination EAD (default at month 1) = `loan_amount` (full principal)
- Default-horizon EAD (default at month 12) = `loan_amount × (n_installments - paid_at_m12) / n_installments`
- Average EAD over the target window (months 13-24) requires post-origination amortization

**ABT schema is rich enough to derive EAD at any month 1-12** from behavioral cols.
For target window (months 13-24), we'd need transactions.csv from the simulator OR an amortization assumption.

## Check 6 — LGD / recovery

**LGD candidates in ABT**: NONE

**Simulator `transactions.csv` columns**: ['period', 'aid', 'cid', 'fin_period', 'status', 'coll_status', 'due_installments', 'paid_installments', 'pay_days']
**Simulator `collection_actions.csv` columns**: ['period', 'aid', 'cid', 'action', 'coll_status']

**Empirical LGD derivation paths**:
- For accounts that hit `coll_status==8` (write-off in target window):
  - Track post-default `paid_installments` from transactions.csv
  - LGD = (loan_amount - principal_recovered) / loan_amount
  - principal_recovered = (paid_installments_at_terminal - paid_at_default) × installment
- For non-defaulters: LGD = 0 (full repayment)

**Computation cost**: 1.55 GB transactions.csv with 29M rows; LGD per defaulter requires joining each writeoff aid to its post-default repayment trace. Feasible but ~5-10 min compute.

**Alternative**: exogenous LGD assumption. ASB profit function used a pre-computed `lgd` column. Industry baseline: LGD ≈ 0.45-0.75 for unsecured consumer with informal collections.

**Decision**: empirical LGD is DERIVABLE but expensive. Recommend exogenous baseline for Phase 3 with empirical LGD as a robustness check in Phase 4.

## Check 7 — Existing economics fields

**Economics fields in current ABT**: NONE

**Old thesis_abt directory exists**: ['thesis_abt_report.txt']

**Existing scaffold** (from `scripts/enrich_thesis_abt.py`, ASB profit function):
```
profit = (1 - default_flag) × loan_amount × r
       - default_flag × ead × lgd
```
- `r` exogenous (5/8/10/12/15% sensitivity, base 10%)
- Single-period (no tenor adjustment)
- Requires pre-computed `ead` and `lgd` columns

**Reusability**:
- ✅ Formula structure is reusable as a baseline
- ⚠️ Single-period profit is **not** Lifetime Net Margin — needs extension
- ⚠️ EAD assumed = loan_amount; tenor-aware EAD requires amortization curve
- ⚠️ The script overwrites a `lgd` column; current ABT has no `lgd` — must add or derive

**Decision**: ASB profit function is **PARTIALLY REUSABLE as reference**. Phase 3 must:
1. Re-introduce `ead` and `lgd` columns (derivable)
2. Extend to tenor-aware Lifetime EL: `LT_EL = sum_{t=1..T} EAD_t × PD_t × LGD_t × discount_t`
3. Net Margin = Lifetime revenue (n_installments × installment × spread) − LT_EL − costs

## Check 8 — PD score availability

**PD score files / sources**:

### LR full-F6E (Phase 2A initial)
- path: `artifacts\phase2_rerun_v2\pd_scores.parquet`
- columns: ['aid', 'split', 'default_flag_12m', 'pd_score']
- rows: 534,314
- `pd_score` mean: 0.016313 (uncalibrated — naive OOT calib)

### Scorecard LR no-F6E (Phase 2B, raw + Platt)
- path: `artifacts\scorecard\woe_transformed_abt.parquet`
- columns: aid, fin_period, pd_woe_raw, pd_woe_platt + WoE features
- rows: 534,314
- `pd_woe_platt` mean: 0.009184 (Platt-calibrated)

### LightGBM tuned (Phase 2A retune)
- model file: `artifacts\pd_model\lightgbm_tuned_model.pkl`
- saved with: booster, best_params, Platt + isotonic calibrators, feature_list
- **Predictions NOT pre-saved** to parquet — Phase 3 must score the ABT inline.
- `lightgbm_tuning_results.json` has OOT metrics: AUC=0.898, Gini=0.795

### LR no-F6E (Phase 2A Test 1, raw)
- predictions NOT saved (only metrics)
- model can be refit in seconds from the 7 features list in `test1_f6e_ablation.json`

### LR full-F6E + Platt (Phase 2A Test 3, leak-free calib)
- calibrator file: `artifacts\phase2_rerun_v2\diagnostics\calibrators.pkl`
- has both Platt and isotonic; final_model.pkl in `phase2_rerun_v2/`
- **Predictions NOT pre-saved** — Phase 3 must score the ABT inline.


**Join key alignment with `modeling_abt.parquet`** (534,314 rows):
- Primary key everywhere: `aid` (string)
- Secondary: `fin_period`, `split` for cohort/temporal joins
- All PD score sources align row-for-row with the ABT (same Phase 2 filter)

**Decision**: 5 PD score variants are accessible. Only 2 are saved as parquet (`pd_scores.parquet` for LR full-F6E naive, and `woe_transformed_abt.parquet` for scorecard). The other 3 (LightGBM tuned, LR full-F6E+Platt, LR no-F6E) require runtime scoring.


## Decision Questions

### Q1. Can we compute LT EL = f(PD, EAD, LGD, tenor)?

**YES**, but requires assumptions:
- **PD**: AVAILABLE (5 calibrated PD scores from Phase 2). Note: PD is currently 12-month
  forward (`default_flag_12m`). For tenor-aware LT EL on a 24-month or 36-month loan, we
  need either (a) extrapolated marginal PDs by month or (b) treat `default_flag_12m` as a
  proxy for full-tenor PD (conservative for >12m loans).
- **EAD**: DERIVABLE from `loan_amount + n_installments + act_paid_installments_m*` for
  months 1-12 within the target window. For months 13-tenor, requires amortization assumption
  or simulator-side post-origination repayment trace.
- **LGD**: DERIVABLE empirically (5-10 min compute on transactions.csv) or
  EXOGENOUS assumption (recommended for thesis baseline).
- **Tenor**: AVAILABLE in `n_installments` (3 levels: 12, 24, 36).

### Q2. Is APR explicit, implied, or absent?

**ABSENT.** Simulator is zero-interest (Check 3 confirms `installment × n_installments / loan_amount ≈ 1.0`).
APR must be EXOGENOUS. ASB scaffold used 5/8/10/12/15% sensitivity grid with 10% base.

### Q3. Is the ASB profit function directly reusable, partially reusable, or not reusable?

**PARTIALLY REUSABLE** as a single-period reference.

- ✅ Same conditional structure (`(1−d) × revenue − d × loss`) is a valid baseline
- ⚠️ Single-period; lacks tenor scaling
- ⚠️ Requires pre-computed `ead` and `lgd` columns (current ABT has neither)

**Phase 3 must extend** to:

```
LT_EL  = Σ_{t=1..T} EAD_t × PD_t × LGD_t × discount_t
LT_NM  = Σ_{t=1..T} (installment × spread - operational_cost) × survival_t × discount_t
profit = LT_NM - LT_EL
```

### Q4. Phase 3 APR strategy

**Recommendation: Option B — APR tiers by score/PD band.**

| PD band | APR | Rationale |
|---------|----:|-----------|
| Top decile (lowest PD) | 12% | Prime borrowers, competitive pricing |
| Deciles 2-5 | 18% | Standard mainstream |
| Deciles 6-9 | 22-26% | Risk-priced subprime |
| Bottom decile (highest PD) | 30% | Risk-priced or rejected |

Plus Option A (fixed 18% / 22%) as a **sensitivity check** to compare flat vs risk-priced.

Ignore Option C (explicit simulator APR) — none exists.

### Q5. LGD strategy

**Recommendation: EXOGENOUS in Phase 3 base case; empirical in Phase 4 robustness.**

Base assumption: `LGD = 0.65` (industry baseline for unsecured consumer with informal collections).
Sensitivity grid: `{0.45, 0.55, 0.65, 0.75, 0.85}` for Phase 3 stress-test.

Empirical LGD computation (Phase 4):
1. For each `default_flag_12m == 1` aid, find the writeoff period from transactions.csv
2. Sum `paid_installments × installment` from origination to terminal period
3. LGD = max(0, (loan_amount − principal_recovered) / loan_amount)

### Q6. EAD strategy

**Recommendation: tenor-aware EAD with two regimes.**

- **Regime A (point-in-time EAD at default)**: `EAD = loan_amount × (1 - paid_fraction_at_default_horizon)`. The horizon is the midpoint of the 12-month target window for `default_flag_12m`.
- **Regime B (origination EAD, conservative)**: `EAD = loan_amount`. Matches the ASB scaffold; serves as worst-case-loss baseline.

Phase 3 should compute LT EL under BOTH regimes and report sensitivity.

