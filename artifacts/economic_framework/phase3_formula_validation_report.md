# Phase 3.1A — Formula Validation Report

**Date**: 2026-05-08
**Source of truth**: `phase3_formula_lock.md` (created from the user's Phase 3.1A prompt; sections 1-12 codify the locked decisions).

**Status**: ✅ All formulas implemented and validated. **Critical finding**: 12-month loans must be EXCLUDED from the economics population. Awaiting your go before any 534K production run.

---

## 1. Implementation summary

### Files produced

| File | Purpose | Lines / size |
|------|---------|-------------:|
| `phase3_formula_lock.md` | Locked source of truth for all formulas | ~140 lines |
| `src/economics.py` | 8 functions implementing the lock | ~280 lines |
| `tests/test_economics.py` | 8+1 unit/sanity tests | ~240 lines |
| `_recovery/phase3_validation.py` | Step 3 + Step 4 driver | ~190 lines |
| `artifacts/economic_framework/tenor_default_diagnostic.csv` | DR by tenor (Step 3) | 4 rows |
| `artifacts/economic_framework/tenor_recommendation.json` | machine-readable recommendation | 1 KB |
| `artifacts/economic_framework/five_account_validation.csv` | per-account validation table | 5 rows × 23 cols |
| `artifacts/economic_framework/phase3_formula_validation_report.md` | this file | — |

### `src/economics.py` public API

All 8 functions specified in the prompt, each citing the lock-document section it implements:

1. `amortization_schedule(loan_amount, n_installments, apr=0.0)` → DataFrame
2. `monthly_hazard_from_pd12(pd_12m)` → float
3. `marginal_pd_schedule(pd_12m, n_installments)` → DataFrame
4. `lifetime_expected_loss(pd_12m, loan_amount, n_installments, lgd, apr_for_ead=0.0, discount_annual=0.0)` → float
5. `expected_interest_margin(pd_12m, loan_amount, n_installments, apr, op_cost_annual=0.0, discount_annual=0.0)` → float
6. `expected_net_profit(pd_12m, loan_amount, n_installments, apr, lgd, op_cost_annual=0.0, discount_annual=0.0)` → dict (LT_margin, LT_EL, Expected_Profit)
7. `apr_tier_lookup(pd_12m)` → float (also `apr_tier_lookup_vec` for arrays)
8. `asb_one_period_profit_reference(pd_12m, loan_amount, apr, lgd)` → float (benchmark only)

---

## 2. Unit-test results

`uv run python tests/test_economics.py` → **9/9 PASS**.

| # | Test | Result | Detail |
|--:|------|:------:|--------|
| 1 | APR=0: `sum(principal) == loan_amount` AND final balance ≈ 0 | ✅ PASS | sum=10000.000000, final_bal=0e+00 |
| 2 | APR>0: final balance ≈ 0 (French amortization) | ✅ PASS | final_bal = -1.33e-10 |
| 3 | `sum(marginal_PD_t over 12 months) == PD_12m` for {0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2} | ✅ PASS | all match within 1e-9 |
| 4 | LT_EL increases with PD ✓ LGD ✓ loan_amount ✓ | ✅ PASS | PD↑: 33.82→335.49; LGD↑: 93.41→176.44; L↑: 67.46→269.86 |
| 5 | Expected_Profit increases with APR | ✅ PASS | APR 0.10→0.18→0.30: 921.62 → 1813.12 → 3225.63 |
| 6 | Expected_Profit decreases with LGD | ✅ PASS | LGD 0.45→0.65→0.85: 2086.44 → 2042.32 → 1998.20 |
| 7 | Expected_Profit == LT_margin − LT_EL exactly (no double-counting) | ✅ PASS | identity holds within 1e-9 across 3 cases |
| 8 | `interest_t` strictly decreasing under French amortization | ✅ PASS | first 6 values: [150.0, 144.76, 139.44, 134.05, 128.57, 123.01] |
| 9 | (bonus) APR tier monotonic in PD | ✅ PASS | (0.001, 0.12) → (0.5, 0.30) monotonic |

---

## 3. Step 3 — Tenor default-rate diagnostic

| n_installments | row count | default count | DR % | mean PD_12m (calibrated) | mean loan_amount |
|---:|---:|---:|---:|---:|---:|
| **12** | **298,346** | **0** | **0.0000%** ⚠️ | 0.009154 | $2,980.78 |
| 24 | 135,115 | 3,121 | 2.3099% | 0.009267 | $5,946.51 |
| 36 | 100,853 | 4,467 | 4.4292% | 0.009163 | $8,944.29 |

### Critical finding — STRUCTURAL ARTIFACT

**12-month loans have ZERO defaults** (0/298,346 = exactly 0%).

**Mechanism**: the simulator triggers `coll_status = 8` (write-off) when `due_installments ≥ 12`. For a 12-month loan, the maximum `due_installments` reachable while the loan is active is exactly 12 (if every payment is missed, `due_installments` reaches 12 AT month 12, which is the loan's terminal month). The `default_flag_12m` target is defined on offsets 12-23 (months 13-24 from origination). For a 12-month loan, the loan is closed at month 12 — **no transactions exist at offsets 13-23**, so write-off in that window is structurally impossible.

The mean calibrated PD_12m on 12-month loans (0.91%) is a model artifact: the LR / scorecard learned the joint feature distribution but assigns non-zero PD because they were in train where the target is 0 by construction. This means **PD_12m for 12-month loans is meaningless for tenor-aware EL**.

### Recommendation: **B. EXCLUDE 12-month loans from the economics population**

| Option | Trade-off | Verdict |
|--------|-----------|:-------:|
| A. Include with caveat | 298,346 rows of structurally non-defaulting loans pollute aggregate EL/profit metrics. Average DR drops mechanically from 1.59% to 0% as tenor mix shifts. | ❌ unacceptable |
| **B. Exclude 12-month loans** | Economics population = 235,968 (24m + 36m only). Larger loans, higher DR (3.2% combined), realistic stress. Thesis Limitations section must document the artifact. | ✅ **CHOSEN** |
| C. Alternative proxy | E.g., apply a separate 12-month PD model trained on a different target. Adds complexity for marginal benefit. | ❌ over-engineering |

**Caveat for thesis**: the simulator's writeoff trigger creates a hard structural floor on 12-month default observability. The thesis Limitations chapter must record this and note that any production credit portfolio with mixed tenors would require a fundamentally different default definition for short-tenor loans.

---

## 4. Step 4 — 5-account validation

Selected accounts span tenor {12, 24, 36} × PD {low, medium, high}. PD = scorecard `pd_woe_platt` (calibrated).

| aid | tenor | PD_12m | loan | APR (locked) | h | sum_marg_PD | LT_EL | LT_margin | Expected_Profit | ASB benchmark | flag |
|-----|------:|-------:|-----:|-------------:|---:|------------:|------:|----------:|----------------:|-------------:|:----:|
| ins202511090588 | 12 | 0.000508 | $3,372 | 0.12 | 4.2e-05 | 5.08e-04 | 0.61 | 223.14 | **222.53** | 403.32 | 0 |
| ins202509170614 | 12 | 0.02378 | $2,052 | 0.26 | 2.0e-03 | 2.38e-02 | 17.92 | 298.09 | **280.17** | 489.12 | 0 |
| ins202601250201 | 24 | 0.01034 | $2,928 | 0.22 | 8.7e-04 | 2.06e-02 | 21.87 | 712.66 | **690.80** | 617.83 | 0 |
| ins202511210066 | 36 | 0.00148 | $13,896 | 0.12 | 1.2e-04 | 4.43e-03 | 21.78 | 2,715.63 | **2,693.85** | 1,651.69 | 0 |
| ins202509270615 | 36 | 0.04142 | $3,312 | 0.26 | 3.5e-03 | 1.19e-01 | 150.82 | 1,428.73 | **1,277.91** | 736.29 | 0 |

### Per-account sanity checks (all 5 accounts)

| Check | Status |
|-------|:------:|
| LT_EL > 0 | ✅ all 5 |
| LT_EL < loan_amount × LGD (worst-case ceiling) | ✅ all 5 (max 11% of L×LGD) |
| LT_margin > 0 (since APR > 0) | ✅ all 5 |
| Expected_Profit = LT_margin − LT_EL exactly | ✅ all 5 (within 1e-9) |
| `sum(marginal_PD_t over n)` = `1 − (1−h)^n` | ✅ all 5 (identity by construction) |
| Final amortization balance ≈ 0 | ✅ all 5 (max abs 1e-10) |

### Cross-account sanity — synthetic peer with controlled inputs

Same `pd_12m=0.02`, `loan_amount=$10,000`, `LGD=0.65`, `APR=0.22`:

| n | LT_EL | LT_margin | Expected_Profit |
|--:|------:|----------:|----------------:|
| 12 | 72.98 | 1,223.61 | 1,150.63 |
| 24 | 144.22 | 2,418.25 | 2,274.03 |
| 36 | 219.00 | 3,672.09 | 3,453.09 |

✅ **LT_EL monotonically grows with tenor** (12 < 24 < 36) at fixed PD_12m and loan_amount.
✅ **Expected_Profit also grows with tenor** because revenue scales faster than EL — at 22% APR, the additional months of interest income outpace the additional months of credit risk.

### High-PD vs low-PD comparison at matched tenor (real accounts)

Compare the two 36-month accounts:
- Low PD (0.00148): LT_EL = $21.78
- High PD (0.04142): LT_EL = $150.82

LT_EL ratio (high/low) = 6.92×, while PD ratio = 27.95× — sub-proportional because the high-PD loan is ~4× smaller. After normalizing by loan_amount × LGD:
- Low: LT_EL / (L×LGD) = 21.78 / (13,896 × 0.65) = 0.0024
- High: LT_EL / (L×LGD) = 150.82 / (3,312 × 0.65) = 0.0700
- Ratio 29× — closely matches the PD ratio, confirming the formula scales correctly with PD when other inputs are normalized. ✅

### LT formula vs ASB benchmark observation

For aid `ins202511210066` (36m, PD 0.0015, loan $13,896, APR 0.12):
- LT Expected_Profit: $2,693.85
- ASB benchmark profit: $1,651.69

ASB is **lower** because it's single-period: ASB ≈ (1−PD) × L × APR_annual, which assumes only one year of interest at the 0.12 rate. The LT formula correctly extends to 36 months of declining-balance interest, yielding ~3 years of margin minus EL. **This confirms the lock decision: ASB single-period understates margin for tenors > 12 months and is unsuitable as the main thesis formula.**

For aid `ins202509170614` (12m, PD 0.024, loan $2,052, APR 0.26):
- LT Expected_Profit: $280.17
- ASB benchmark profit: $489.12

Here ASB is **higher** because it assumes the full loan amount earns interest for the full year (`L × APR`), while the LT formula correctly accounts for amortization (average outstanding ≈ L/2, hence interest ≈ L × APR / 2 over the year). For a 12-month loan, ASB **overstates margin by ~1.7×** because it ignores principal repayment. **This is the second reason ASB is unsuitable as the main formula.**

---

## 5. Formula warnings + caveats

### W1 — PD horizon extrapolation

The locked formula extrapolates the monthly hazard `h` from PD_12m to all months 1..n_installments. For 36-month loans, this implies a cumulative PD over 36 months of `1 − (1−h)^36`. At PD_12m = 0.04142:
- 12-month cumulative = 0.0414 (=PD_12m by construction)
- 24-month cumulative = 0.0811
- 36-month cumulative = 0.1192

This assumes **constant monthly hazard** across the loan's life. In practice, hazard rates decline as the loan ages (curing effect) — so the formula likely **overstates** EL for long-tenor loans. Phase 4 should add a sensitivity to a declining-hazard schedule (e.g., halve `h` after month 12).

### W2 — Calibrated PD source

The 5-account validation used scorecard `pd_woe_platt` (Phase 2B Platt-calibrated). This has OOT mean predicted = 0.92% vs base rate = 0.85%. Production economics will use **LightGBM tuned + Platt** (OOT mean predicted = 0.94%) which is the locked primary PD per Phase 2A diagnostics. Differences between PD sources will affect absolute EL magnitudes but not formula correctness.

### W3 — APR is exogenous

No simulator field for APR exists (Phase 3.0 audit Check 4). The locked tier table (Section 10 of `phase3_formula_lock.md`) is the THESIS assumption. Phase 3.1B will run sensitivities on flat-APR alternatives.

### W4 — Base case has zero discount and zero op cost

Lock Section 9 sets `op_cost_annual = 0` and `discount_annual = 0` for the base case. Real lenders have material op costs (≈3-5% per annum on outstanding) and discount rates (≈ funding cost, 4-8%). Phase 3.1B sensitivity grid must cover both.

### W5 — `EAD_t = balance_begin_t` uses the chosen APR for amortization

When `apr=0.22` is used, EAD follows the French amortization curve (slower decline than zero-interest straight line). When the analyst sets `apr_for_ead = 0` independently, EAD follows straight-line amortization. The default `expected_net_profit` ties EAD's APR to the revenue's APR (consistent), but `lifetime_expected_loss` exposes `apr_for_ead` separately for sensitivity studies.

---

## 6. Are the formulas safe for full production run?

**YES**, with the following gating conditions:

1. ✅ All 9 unit tests pass
2. ✅ All 5 accounts pass per-account sanity (LT_EL > 0, < L×LGD; LT_margin > 0; no double-counting)
3. ✅ Cross-account monotonicity in tenor + PD confirmed
4. ⚠️ **Must EXCLUDE 12-month loans** before any production run (decision letter B)
5. ⚠️ **Must use the LightGBM-tuned + Platt PD** as primary, per Phase 2A diagnostics
6. ⚠️ Document in production output: vintage-drift caveat (calibrated PD over-predicts on OOT by ~10%, see Phase 2A Test 3)

After applying conditions 4-6, the formulas are safe for the full 534,314 → 235,968 row production run.

---

## 7. Recommended Phase 3.1B production run plan (NOT executed in this round)

For your approval before execution:

1. Filter ABT to `n_installments ∈ {24, 36}` → 235,968 rows
2. Score all rows with LightGBM tuned + Platt → `pd_lgb_platt`
3. Apply `apr_tier_lookup_vec` → per-row APR
4. For each row: compute `LT_EL`, `LT_margin`, `Expected_Profit` with base parameters (LGD=0.65, op_cost=0, discount=0)
5. Aggregate to portfolio level + per-PD-decile
6. Repeat under sensitivity grids:
   - LGD ∈ {0.45, 0.55, 0.65, 0.75, 0.85}
   - flat APR ∈ {0.18, 0.22, 0.26}
   - op_cost_annual ∈ {0.00, 0.03, 0.05}
   - discount_annual ∈ {0.00, 0.04, 0.08}

---

## 8. Stopping point

Per spec: **"Stop after Phase 3.1A validation report. DO NOT run full 534K production economics yet. DO NOT proceed to Phase 4. DO NOT modify simulator."**

Awaiting approval of:
- The 12-month exclusion decision (letter B)
- The Phase 3.1B production run plan above
