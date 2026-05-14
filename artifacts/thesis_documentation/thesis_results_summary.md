# Thesis Results Summary

**Purpose**: Single-source consolidation of every numerical result that may
appear in the thesis. All numbers reflect corrected values (post Phase 4.3
calibration check, post Phase 5 review).

---

## 1. Population overview

| Population | Rows | Default rate | Source |
|------------|-----:|-------------:|--------|
| Full modeling pop | 534,314 | 1.65% (target) | `artifacts/phase2_rerun_v2/modeling_abt.parquet` |
| Train_for_model (eco) | 150,476 | — | cohorts 202509-202610 |
| Calib slice (eco) | 21,465 | ~0.85% | cohorts 202611-202612 |
| Economic analysis pop | **235,968** | 1.92% | 24m + 36m only |
| OOT economics bootstrap pop | **64,027** | 1.916% | cohorts 202701-202706 (24m + 36m) |
| 12m loans in eco pop | 0 (excluded) | n/a | structural artifact |

## 2. Phase 2 — PD model comparison (OOT, base scenario, post-Platt)

| Model | OOT AUC | OOT Gini | OOT KS | OOT Brier (Platt) | OOT ECE (Platt) |
|-------|--------:|---------:|-------:|------------------:|----------------:|
| LR no-F6E (7 features) | 0.836 | 0.672 | 0.540 | 0.0082 | ~0.008 |
| LR full-F6E (22 features) | 0.859 | 0.718 | 0.548 | 0.0080 | 0.0011 |
| **LightGBM tuned (PRIMARY)** | **0.898** | **0.795** | **0.638** | **0.0079** | **0.0012** |
| Scorecard no-F6E (7 features) | 0.803 | 0.606 | 0.481 | 0.0179 | 0.0100 |

Source: `artifacts/phase2_rerun_v2/model_metrics.json`,
`artifacts/pd_model/lightgbm_tuning_results.json`,
`artifacts/scorecard/scorecard_metrics.json`,
`artifacts/calibration_verification/calibration_summary.csv`.

## 3. Scorecard result table (Phase 2B, no-F6E primary)

| Property | Value |
|----------|------:|
| Features (7) | app_nom_job_code, act_age_log1p, mean_cars_by_job_code, app_nom_marital_status, median_income_by_job_code, app_nom_branch, app_nom_city |
| Total bins | (see scorecard_table.csv) |
| Score factor | 20 / log(2) ≈ 28.85 |
| Base score | 300 |
| PDO | 20 |
| OOT AUC | 0.803 |
| OOT Gini | 0.606 |
| OOT KS | 0.481 |

Source: `artifacts/scorecard/scorecard_metrics.json`,
`artifacts/scorecard/scorecard_table.csv`.

## 4. Phase 3.1B economic base result (eco pop, primary PD, base scenario)

Base scenario: tiered APR (locked), LGD = 0.65, discount = 0, op_cost = 0,
PD multiplier = 1 (raw LightGBM Platt).

| Metric | Value |
|--------|------:|
| Mean LT_EL | $62.95 |
| Mean LT_margin | $1,556.02 |
| Mean Expected_Profit | **$1,493.07** |
| Total Expected_Profit (full eco pop) | **$352.3M** |
| Share of accounts with Profit > 0 | **100.000%** |
| Worst-case account profit | +$264.30 (still positive) |
| Tenor 24m mean profit | $965.25 |
| Tenor 36m mean profit | $2,200.20 |
| 36m share of total profit | 63% (vs 43% of count) |

Source: `artifacts/economic_framework/economics_per_account.parquet`,
`artifacts/economic_framework/profit_framework_report.md`.

## 5. Phase 3.2 stress grid summary (576 cells, op_cost held at 0)

| Category | Cells | Share |
|----------|------:|------:|
| approve_all (k\* ≥ 99%) | 220 | 38.2% |
| **interior** (50% ≤ k\* < 99%) | **356** | **61.8%** |
| reject_most (k\* < 50%) | 0 | 0.0% |

| k\* statistic | Value |
|---------------|------:|
| min | **84.73%** (adverse anchor) |
| median | 98.24% |
| max | 100.00% |

| cutoff_gap (profit k\* − Youden k) | Value |
|--------------------------------------|------:|
| min | +5.33 pp |
| median | +18.83 pp |
| max | +20.59 pp |
| Cells with profit > Youden | **576/576** |

Driver hierarchy (single-dim spread on k\*): PD multiplier 3.54 pp;
APR strategy 2.32 pp; LGD 1.28 pp; acquisition_cost 0.43 pp; cost_of_funds
0.43 pp.

Source: `artifacts/economic_framework/economic_stress_grid.parquet`,
`phase3_2_stress_report.md`.

## 6. Anchor scenario definitions (4 LOCKED)

| Anchor | PD mult | COF | Acq | LGD | APR | op_cost |
|--------|--------:|----:|----:|----:|-----|--------:|
| optimistic_base | 1.0 | 0.00 | $0 | 0.55 | tiered_uncapped | 0.00 |
| realistic_central_boundary | 2.0 | 0.03 | $250 | 0.65 | tiered_cap_24 | 0.00 |
| moderate_interior | 3.0 | 0.03 | $250 | 0.65 | flat_18 | 0.00 |
| adverse_stress | 5.0 | 0.06 | $500 | 0.85 | flat_18 | 0.00 |

Source: `artifacts/economic_framework/anchor_scenarios_v2.json`.

## 7. Phase 4.1 bootstrap CI table (1,000 stratified resamples × 4 anchors, OOT n=64,027)

| Anchor | k\* approve % (95% CI) | cutoff_gap (95% CI, pp) | profit_uplift (95% CI) | uplift % |
|--------|-----------------------:|-------------------------:|------------------------:|---------:|
| optimistic_base | 100.00 [100.00, 100.00] | +20.41 [+20.10, +20.71] | $30.75M [$30.17M, $31.31M] | 47.05% |
| realistic_central_boundary | 99.25 [99.16, 99.36] | +19.66 [+19.36, +19.97] | $17.75M [$17.39M, $18.13M] | 38.37% |
| moderate_interior | 95.31 [94.99, 95.50] | +15.72 [+15.35, +16.02] | $5.46M [$5.29M, $5.63M] | 11.16% |
| adverse_stress | 84.83 [84.31, 85.27] | +5.24 [+4.79, +5.64] | $0.46M [$0.41M, $0.51M] | 1.51% |

Categorical resample frequencies:

| Anchor | approve_all (N/1000) | interior (N/1000) | reject_most (N/1000) |
|--------|---------------------:|------------------:|---------------------:|
| optimistic_base | 1000 | 0 | 0 |
| realistic_central_boundary | 1000 | 0 | 0 |
| moderate_interior | 0 | 1000 | 0 |
| adverse_stress | 0 | 1000 | 0 |

Across all 4,000 (anchor × resample) combinations: profit cutoff > Youden in
4,000/4,000; profit uplift > 0 in 4,000/4,000.

Source: `artifacts/economic_framework/bootstrap_anchor_results.parquet`,
`bootstrap_ci_summary.csv`, `phase4_1_bootstrap_report.md`.

## 8. Phase 4.2 PART A — PD-quality stress (16 cells, profit_uplift > 0 in all)

Mean cutoff_gap by Gini level:

| PD variant | Achieved Gini | Mean cutoff_gap (pp) | profit > Youden cells |
|------------|--------------:|---------------------:|----------------------:|
| raw | 0.804 | +15.5 | 4/4 |
| stressed Gini 0.60 | 0.603 | +21.2 | 4/4 |
| stressed Gini 0.45 | 0.446 | +30.8 | 4/4 |
| stressed Gini 0.30 | 0.303 | +35.7 | 4/4 |

Source: `artifacts/pd_quality_stress/cutoffs_by_gini.csv`.

## 9. Phase 4.2 PART B — op_cost robustness (12 cells)

| Anchor | op_cost | k\* | mean profit | category |
|--------|--------:|----:|------------:|---------|
| realistic_central_boundary | 0.00 | 99.26% | $998 | approve_all |
| realistic_central_boundary | 0.01 | 98.94% | $819 | interior |
| realistic_central_boundary | 0.02 | 98.74% | $640 | interior |
| realistic_central_boundary | 0.04 | 97.74% | $283 | interior |
| moderate_interior | 0.00 | 96.33% | $1,061 | interior |
| moderate_interior | 0.04 | 90.97% | $355 | interior |
| adverse_stress | 0.00 | 84.90% | $305 | interior |
| adverse_stress | 0.02 | 74.72% | -$41 | interior (loss-making) |
| **adverse_stress** | **0.04** | **0.31%** | **-$387** | **REJECT-MOST** |

Op_cost tipping points:
- realistic_central_boundary: k\* drops < 99% at op_cost = 0.01; never < 50%
- moderate_interior: already < 99% at op_cost = 0; never < 50%
- adverse_stress: < 99% at op_cost = 0; **< 50% at op_cost = 0.04**

Source: `artifacts/op_cost_robustness/cutoffs_by_op_cost.csv`.

## 10. Phase 4.2 PART C — Combined stress mini-grid (36 cells)

Distribution by category:
- approve_all: 1
- interior: 31
- reject_most: 4 (all adverse_stress + op_cost = 0.04, regardless of Gini)

Distribution by direction:
- profit_cutoff > Youden: 31/36
- profit_cutoff < Youden: 5/36 (all adverse_stress + op_cost ∈ {2%, 4%})
- **profit_uplift > 0: 36/36** (positive even when cutoff is less permissive)

Source: `artifacts/economic_framework/phase4_2_combined_grid.csv`.

## 11. Calibration verification summary (Phase 4.3, 7 PD sources, OOT n=64,027)

| PD source | mean_pred | AUC | Gini | KS | Brier | ECE | mean_pred / observed |
|-----------|----------:|----:|-----:|---:|------:|----:|--------------------:|
| LightGBM Platt (PRIMARY) | 0.94% | 0.902 | 0.804 | 0.646 | 0.0172 | 0.0098 | **0.49** ⚠️ |
| LR full-F6E + Platt | 2.07% | 0.864 | 0.728 | 0.559 | 0.0167 | **0.0026** | 1.08 |
| LR no-F6E + Platt | 2.08% | 0.840 | 0.680 | 0.546 | 0.0170 | **0.0029** | 1.08 |
| Scorecard no-F6E + Platt | 0.92% | 0.803 | 0.606 | 0.481 | 0.0179 | 0.0100 | **0.48** ⚠️ |
| Stressed Gini 0.60 | 1.92% | 0.802 | 0.603 | 0.469 | 0.0204 | 0.0143 | 1.00 |
| Stressed Gini 0.45 | 1.92% | 0.723 | 0.446 | 0.328 | 0.0242 | 0.0238 | 1.00 |
| Stressed Gini 0.30 | 1.92% | 0.651 | 0.303 | 0.229 | 0.0287 | 0.0312 | 1.14 |

OOT base rate: 1.916%.

Source: `artifacts/calibration_verification/calibration_summary.csv`.

## 12. ASB vs Lifetime profit by tenor (Phase 3.1B)

| Tenor | n | Mean LT profit | Mean ASB profit | ASB / LT total ratio |
|-------|--:|---------------:|----------------:|---------------------:|
| 24m | 135,115 | $965.25 | $873.99 | 0.91 (-9%) |
| **36m** | 100,853 | $2,200.20 | $1,317.71 | **0.60 (-40%)** |
| 24m + 36m | 235,968 | $1,493.07 | $1,063.64 | 0.71 (-29%) |

Source: `artifacts/economic_framework/asb_comparison.csv`.

## 13. Figure index (9 figures, both PDF + PNG)

| # | File | One-line interpretation |
|--:|------|-------------------------|
| 1 | `fig1_profit_curves` | Cumulative profit per anchor; profit-optimal k\* (○) vs Youden (×) markers — 4 anchors visualised |
| 2 | `fig2_cutoff_gap_vs_gini` | Cutoff gap WIDENS monotonically as PD Gini falls 0.80 → 0.30 |
| 3 | `fig3_op_cost_vs_kstar` | op_cost drives k\* downward; reject-most regime annotated for adverse + 4% |
| 4 | `fig4_asb_vs_lifetime` | ASB single-period UNDERESTIMATES lifetime profit, especially for 36m |
| 5 | `fig5_bootstrap_ci_density` | 4-panel bootstrap density of profit_uplift; all CIs strictly above $0 |
| 6 | `fig6_reliability_diagrams` | LightGBM and Scorecard reliability curves sit BELOW diagonal (under-prediction) |
| 7 | `fig7_feature_importance` | Top 20 features: LightGBM (gain) vs LR (signed coefficient) |
| 8 | `fig8_stress_heatmap` | 3-panel heatmap of profit uplift; positive (green) in all 36 cells |
| 9 | `fig9_sensitivity_hierarchy` | PD multiplier (3.54 pp) and APR strategy (2.32 pp) dominate cutoff variation |

Source: `artifacts/figures/`.

## 14. Strategic narrative (one-paragraph thesis sell)

> *Across the tested simulator scenarios, profit-driven cutoff selection
> outperforms Youden's J in dollar terms in every one of 64 stress cells and
> 4,000 (anchor × bootstrap) combinations. The advantage widens as PD
> discrimination weakens, holds in light and adverse stress regimes, and
> survives PD-quality, LGD, APR, funding-cost, and acquisition-cost stress.
> A reject-most regime appears only when adverse stress is combined with high
> operating cost (≥ 4%). The locked tenor-aware Lifetime formula
> systematically corrects the ~40% understatement that the simpler ASB
> single-period benchmark would produce on 36-month loans.*
