# Phase 1.5 Feature Factory Report

## 1. Purpose
Expand raw variable universe to >= 2000 raw features (excl. ID/target/split) with governance metadata for every column.

## 2. Input
- Cleaned wide ABT: 534,314 rows x 190 cols
- Schema aliases detected: {'age': 'act_age', 'loan_amount': 'loan_amount', 'n_installments': 'n_installments', 'installment': 'installment', 'split': 'split'}
- Duplicate-column check: {'app_loan_amount_vs_loan_amount': 'perfect_equality', 'app_n_installments_vs_n_installments': 'perfect_equality'}
- Dropped duplicates: ['app_loan_amount', 'app_n_installments']

## 3. Methodology
Six families generated with auto-flagged governance via Rule Precedence (most restrictive level wins). Source-based restrictions override family-based defaults.

- F1 Rolling stats: mean/std/min/max/median/last over {3m,6m,9m,12m} per behavioral series + first/last endpoints.
- F2 Trend: slope/intercept/r2 over {3m,6m,12m} per series.
- F3 Ratio: domain ratios with source-inherit governance.
- F4 Interactions: products + polynomials, source-inherit.
- F5A: app-only TRAIN-ONLY group statistics with global-train fallback.
- F5B: loan-term group stats (level E inheritance).
- F6A/B/C: rank/bin/noisy transforms with source-inherit governance.
- F6D: pure random negative controls (level H, allowed for PD).
- F6E: synthetic bureau-like from safe app + noise ONLY.

## 4. Output Summary

### 4.1 Original column classification

| Original family | Count |
|---|---|
| ORIGINAL_APP | 11 |
| ORIGINAL_BEHAVIORAL | 169 |
| ORIGINAL_ID | 4 |
| ORIGINAL_LOAN | 3 |
| ORIGINAL_OTHER | 1 |
| ORIGINAL_SPLIT | 1 |
| ORIGINAL_TARGET | 1 |

### 4.2 Generated family breakdown

| Family | Count |
|---|---|
| F1 | 338 |
| F2 | 117 |
| F3 | 12 |
| F4 | 9 |
| F5A | 37 |
| F5B | 15 |
| F6A | 885 |
| F6B | 156 |
| F6C | 177 |
| F6D | 100 |
| F6E | 200 |

### 4.3 Combined catalog summary

| Metric | Count |
|---|---|
| Total ABT columns | 2236 |
| Original columns | 190 |
| Generated columns | 2046 |
| raw_feature_count (excl ID/target/split/meta) | 2229 |

### 4.4 Governance breakdown

| Metric | Count |
|---|---|
| allowed_for_origination_pd_true | 435 |
| allowed_for_behavioral_pd_true | 850 |
| allowed_for_profit_true | 77 |
| leakage_low | 441 |
| leakage_medium | 492 |
| leakage_high | 1303 |
| uses_target_true | 1 |
| uses_future_behavior_true | 1719 |

### 4.5 Rule Precedence verification (5 examples per level)


**Level A**: ['default_flag_12m']

**Level B**: ['aid', 'cid', 'fin_period', 'observation_status', 'split']

**Level C**: ['act_due_m4', 'act_due_m5', 'act_due_m6', 'act_due_m7', 'act_due_m8']

**Level D**: ['max_due', 'max_coll_status', 'trend_due', 'months_ever_due', 'months_coll_2plus']

**Level E**: ['loan_amount_to_income', 'installment_to_income', 'loan_amount_to_age', 'tenor_in_years', 'act_due_m2_to_loan_amount']

**Level F**: ['act_due_m2', 'act_due_m3', 'act_paid_installments_m2', 'act_paid_installments_m3', 'act_utl_m2']

**Level G**: ['app_income', 'app_nom_branch', 'app_nom_gender', 'app_nom_job_code', 'app_number_of_children']

**Level H**: ['random_uniform_1', 'random_uniform_2', 'random_uniform_3', 'random_uniform_4', 'random_uniform_5']

### 4.6 Family 5A unseen-group fallback report

- F5A features generated: 37
- Avg OOT fallback rate: 0.0000%
- Max OOT fallback rate: 0.0000% (in feature `mean_income_by_job_code`)

## 5. Validation Checks

- row_count_unchanged: PASS
- no_infinities: PASS
- catalog_completeness: PASS
- uses_target_count: PASS
- Storage format: **parquet**
- Memory size: 5020 MB
- Top 10 sparse features (>50% NaN, sampled):
  - `act_cus_utl_r2_3m`: 97.57%
  - `act_cus_utl_r2_6m`: 94.47%
  - `coll_status_r2_3m`: 82.62%
  - `act_dueutl_r2_3m`: 81.77%
  - `act_due_r2_3m`: 81.77%
  - `act_cc_r2_3m`: 70.95%
  - `act_loaninc_r2_3m`: 70.02%
  - `act_cus_dueutl_r2_3m`: 69.93%
  - `coll_status_r2_6m`: 56.04%
  - `act_dueutl_r2_6m`: 54.03%

## 6. Limitations

- Family 5 target-encoding excluded by design.
- Linear amortization assumption in some ratios.
- Some rolling stats undefined for short-history series (act_cus_seniority m2-m6 only) -> NaN-heavy in 9m/12m windows.
- F6E synthetic bureau features are NOT calibrated to target. Any predictive association arises indirectly via app-variable signal already in the simulator.

## 7. Next Steps (DO NOT EXECUTE YET)

- User reviews catalog.
- Phase 2 rerun MUST filter via:
  ```python
  catalog['allowed_for_origination_pd'] == True
  AND catalog['leakage_risk'] != 'high'
  AND catalog['uses_target'] == False
  AND catalog['uses_future_behavior'] == False
  ```
- Phase 2 should verify F6D random controls are NOT selected by Lasso (selection sanity check).
