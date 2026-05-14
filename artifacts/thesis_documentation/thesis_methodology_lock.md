# Thesis Methodology Lock

**Purpose**: A single source-of-truth document for every locked methodology decision. Use this when writing the thesis Methodology chapter so phrasing stays consistent and no claim drifts beyond what was tested.

**Wording rules** (enforced throughout the thesis):
- Use "across N bootstrap resamples" or "in K of K stress cells" — NOT "true probability".
- Use "within the tested scenario space" / "within the locked stress grid" — NOT "in general" or "always".
- Use "supports the hypothesis" — NOT "proves".

---

## 1. Population definitions (LOCKED)

| Population | Rows | Definition |
|------------|-----:|------------|
| Full modeling population | 534,314 | Phase 2 wide ABT after Phase 2 cohort filter (`MIN_FIN_PERIOD=202509`, `OOT_FIN_PERIOD_MAX=202706`) |
| Economic analysis population | **235,968** | Modeling pop filtered to `n_installments ∈ {24, 36}` |
| OOT economics bootstrap population | **64,027** | Eco pop filtered to `split_new == 'oot'` (cohorts 202701-202706) |
| 12-month loans in eco pop | **0** (excluded) | Excluded due to structural zero-default artifact (Phase 3.1A) |
| Train_for_model | 150,476 | Eco pop with cohorts 202509-202610 |
| Calibration slice | 21,465 | Eco pop with cohorts 202611-202612 (Platt fit slice) |

**Note**: H1 hard requirement (≥500K modeling rows) is satisfied at the full
modeling level (534,314). The economic analysis is intentionally a subset; the
exclusion is documented in Limitations.

## 2. Target

`default_flag_12m`: writeoff (`coll_status == 8`) within target window
`offset ∈ [12, 23]` from origination (months 13-24 after origination).
Computed by `scripts/build_wide_abt.py:build_target` (lock spec section: see
`phase3_formula_lock.md` Section 1).

## 3. PD models used (4 base + 3 stressed variants)

| # | Model | Source | Calibration |
|--:|-------|--------|-------------|
| 1 | **LightGBM tuned (PRIMARY)** | `artifacts/pd_model/lightgbm_tuned_model.pkl` | Platt on 202611-202612 |
| 2 | LR full-F6E | `artifacts/phase2_rerun_v2/final_model.pkl` (refit on train_for_model) | Platt on 202611-202612 |
| 3 | LR no-F6E | refit at runtime on train_for_model from 7 features in `test1_f6e_ablation.json` | Platt on 202611-202612 |
| 4 | Scorecard no-F6E | `artifacts/scorecard/woe_transformed_abt.parquet` | Platt on 202611-202612 |
| 5-7 | Stressed Gini variants (0.30, 0.45, 0.60) | `src/calibration.py:perturb_to_target_gini` applied to model #1 | re-anchored to OOT base rate |

**Excluded** (out of scope for Phase 4): Scorecard full-F6E robustness — exists
as metrics + table only (`artifacts/scorecard/robustness_full_f6e/`); no
row-level PD parquet was generated in Phase 2B's optional run.

**Primary model**: LightGBM tuned + Platt-calibrated. Used everywhere as
"primary PD"; LR variants and scorecard are used for triangulation /
robustness in Phase 4.3 and Phase 2 multi-model comparison.

## 4. Calibration design (leak-free)

- **Train_for_model**: cohorts 202509-202610 (used to fit the PD model)
- **Calib slice**: cohorts 202611-202612 (used to fit Platt scaling on PD scores from train_for_model)
- **OOT**: cohorts 202701-202706 (NEVER used in calibration; only evaluation)

Implemented in `src/calibration.py:make_calibration_split`. Asserts that the
calib slice cohorts are NOT in the original `split == 'oot'`.

**Calibration caveat**: The Platt calibrator was fit on the calib slice base
rate (~0.85%). The economics-OOT subset (24m + 36m only, base rate 1.92%) has
~2× higher base rate because the 0%-DR 12m loans are excluded. The PRIMARY
LightGBM and the Scorecard therefore under-predict mean PD by ~50% on the
economics-OOT subset. Phase 3 anchor scenarios apply PD multipliers
{1, 2, 3, 5} which approximately bracket this calibration drift.

## 5. Locked formulas (from `phase3_formula_lock.md`)

### 5.1 Monthly hazard from PD_12m
```
h = 1 - (1 - PD_12m) ** (1/12)
```

### 5.2 Marginal PD schedule
```
survival_begin_t = (1 - h) ** (t-1),  for t = 1..n_installments
marginal_PD_t    = survival_begin_t * h
```

### 5.3 Lifetime EL
```
LT_EL = sum_{t=1..n_installments} marginal_PD_t * LGD * EAD_t * discount_t
EAD_t = balance_begin_t (from amortization schedule)
```

### 5.4 Lifetime margin (gross of credit loss)
```
net_interest_t       = balance_begin_t * max(APR - cost_of_funds, 0) / 12
expected_interest_t  = survival_begin_t * net_interest_t
op_cost_t            = survival_begin_t * loan_amount * op_cost_annual / 12
LT_margin            = sum_t (expected_interest_t - op_cost_t) * discount_t
```

### 5.5 Expected profit (LT_EL deducted ONCE; no double-counting)
```
Expected_Profit = LT_margin - LT_EL - acquisition_cost
```

### 5.6 Discount factor
```
discount_t = 1 / (1 + discount_annual / 12) ** t
```

### 5.7 ASB benchmark (reference only)
```
profit_ASB = (1 - PD_12m) * loan_amount * APR
           - PD_12m       * loan_amount * LGD
```

## 6. APR scheme (LOCKED tier table)

| Band | Condition on PD_12m | APR |
|------|--------------------|----:|
| Prime | PD < 0.005 | 0.12 |
| Near-prime | 0.005 ≤ PD < 0.010 | 0.18 |
| Mainstream | 0.010 ≤ PD < 0.020 | 0.22 |
| Subprime | 0.020 ≤ PD < 0.050 | 0.26 |
| Deep-subprime | PD ≥ 0.050 | 0.30 |

**Source of tier values**: Phase 3.0 schema audit recommendation, accepted by
the user before Phase 3.1A. Real market APR ranges may differ — see "Do Not
Claim" Section 11.

**Sensitivity APR strategies tested**: tiered_uncapped, tiered_cap_24,
tiered_cap_18, flat_12, flat_18, flat_24, flat_30.

## 7. LGD assumption

- **Base case**: LGD = 0.65 (Phase 3.0 audit baseline for unsecured consumer
  with informal collections)
- **Sensitivity grid**: {0.45, 0.55, 0.65, 0.75, 0.85}
- **Empirical LGD**: derivable from `transactions.csv` post-default repayment
  trace but NOT computed for the thesis (deferred to future work)

## 8. Stress grid design (Phase 3.2 + Phase 4.2)

### Phase 3.2 grid (576 cells, op_cost held at 0)
- PD multiplier: {1, 2, 3, 5}
- cost_of_funds_annual: {0.00, 0.03, 0.06}
- acquisition_cost: {$0, $250, $500}
- LGD: {0.55, 0.65, 0.75, 0.85}
- APR strategy: {tiered_uncapped, tiered_cap_24, flat_18, flat_24}

### Phase 4.2 PARTS A/B/C (PD-quality + op_cost stress)
- A: 4 PD variants (raw + Gini 0.30/0.45/0.60) × 4 anchors = 16 cells
- B: 3 anchors × op_cost {0.00, 0.01, 0.02, 0.04} = 12 cells
- C: 4 PD variants × 3 op_cost × 3 anchors = 36 cells
- **Total: 64 stress cells**

## 9. Bootstrap design (Phase 4.1)

- N_bootstrap = 1,000
- Population: OOT economics subset (64,027 rows)
- Stratification: by `n_installments` (24m vs 36m)
- Resample with replacement, `random_state=42`
- Per resample × anchor: profit_at_kstar, k_star_approve_pct, cutoff_pd_star,
  profit_at_youden, approve_pct_youden, cutoff_gap, profit_uplift,
  profit_uplift_pct
- 4 anchors × 1,000 resamples = 4,000 bootstrap × anchor combinations

## 10. Anchor scenario definitions (4 LOCKED)

| Anchor | PD mult | COF | Acq | LGD | APR | op_cost |
|--------|--------:|----:|----:|----:|-----|--------:|
| optimistic_base | 1.0 | 0.00 | $0 | 0.55 | tiered_uncapped | 0.00 |
| realistic_central_boundary | 2.0 | 0.03 | $250 | 0.65 | tiered_cap_24 | 0.00 |
| moderate_interior | 3.0 | 0.03 | $250 | 0.65 | flat_18 | 0.00 |
| adverse_stress | 5.0 | 0.06 | $500 | 0.85 | flat_18 | 0.00 |

## 11. Do Not Claim (negative locks)

The thesis MUST NOT claim any of the following, even informally:

1. **Do NOT claim universal real-world generalization.** The simulator is
   synthetic; the conclusions hold "within the tested simulator + scenario
   space".
2. **Do NOT claim APR tiers are market-validated.** The locked APR tier
   table (Section 6) is an exogenous methodological assumption; real markets
   may price differently.
3. **Do NOT claim 12m loans are risk-free.** The 0% DR observed for 12m
   loans is a simulator artifact (writeoff trigger timing); real 12m loans
   have non-zero default risk.
4. **Do NOT claim LightGBM is perfectly calibrated on the economics-OOT
   subset.** The Phase 4.3 calibration analysis shows mean predicted PD
   under-predicts the eco-OOT base rate by ~50%. The PD-multiplier scenarios
   span this gap, but the under-prediction is real on the unscaled model.
5. **Do NOT describe bootstrap empirical frequency as true probability.**
   Use phrasing "across 1,000 bootstrap resamples, the result held in N/1000
   resamples" rather than "P(...) = N/1000".
6. **Do NOT claim ASB single-period is wrong.** It is a different (simpler)
   formula that systematically underestimates lifetime profit by ~9% (24m)
   and ~40% (36m); both formulas are internally consistent for their own
   definitions.
7. **Do NOT claim profit cutoff is universally more permissive than Youden.**
   In 5 of 36 combined-stress cells (adverse_stress + op_cost ≥ 2%), profit
   cutoff is LESS permissive than Youden (while still beating it on dollar
   uplift).
8. **Do NOT claim multi-simulator robustness.** All results are based on a
   single simulator configuration (seed=42, p_positive=0.00, 800 clients/day,
   60 periods). Cross-seed / cross-config robustness is future work.
9. **Do NOT claim empirical LGD validation.** LGD is exogenous (0.65 base);
   empirical recovery from `transactions.csv` is future work.
10. **Do NOT claim model risk is fully quantified.** The bootstrap captures
    sampling uncertainty within OOT only; PD model uncertainty, calibration
    drift, and assumption uncertainty are not bootstrapped.

## 12. Figure list (LOCKED, used in thesis)

| # | File | Chapter |
|--:|------|---------|
| 1 | `fig1_profit_curves.{pdf,png}` | Results — Profit framework |
| 2 | `fig2_cutoff_gap_vs_gini.{pdf,png}` | Results — PD-quality stress |
| 3 | `fig3_op_cost_vs_kstar.{pdf,png}` | Results — Cost stress |
| 4 | `fig4_asb_vs_lifetime.{pdf,png}` | Methodology — Formula choice |
| 5 | `fig5_bootstrap_ci_density.{pdf,png}` | Results — Statistical robustness |
| 6 | `fig6_reliability_diagrams.{pdf,png}` | Methodology — PD calibration |
| 7 | `fig7_feature_importance.{pdf,png}` | Methodology — PD model interpretation |
| 8 | `fig8_stress_heatmap.{pdf,png}` | Results — Combined stress |
| 9 | `fig9_sensitivity_hierarchy.{pdf,png}` | Discussion — Driver analysis |
