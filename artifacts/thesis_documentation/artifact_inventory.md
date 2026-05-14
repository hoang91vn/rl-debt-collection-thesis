# Artifact Inventory

**Purpose**: Complete catalog of every analysis artifact, with file size,
purpose, thesis chapter usage, and status (required / optional / archive).

**Verification**: All paths below were confirmed to exist as of 2026-05-09.

---

## A. Thesis-required artifacts (must commit, must keep stable)

### A1. Phase 1.5 Feature Factory

| Path | Size | Purpose | Used in chapter |
|------|-----:|---------|-----------------|
| `artifacts/phase1_5_feature_factory/feature_catalog.csv` | 480 KB | 14-field governance per generated column (2,236 rows) | Methodology — features |
| `artifacts/phase1_5_feature_factory/feature_family_summary.txt` | 2.5 KB | Per-family count + per-level count | Methodology — features |
| `artifacts/phase1_5_feature_factory/phase1_5_report.md` | 4.8 KB | Generation summary | Methodology |
| `artifacts/phase1_5_feature_factory/run_config.json` | 1.9 KB | Runtime config + seed | Reproducibility |
| `artifacts/phase1_5_feature_factory/thesis_wide_abt_expanded.parquet` | **2.4 GB** | The expanded ABT (534K × 2,236) | LARGE — gitignored |

### A2. Phase 2 PD modeling

| Path | Size | Purpose | Used in chapter |
|------|-----:|---------|-----------------|
| `artifacts/phase2_rerun_v2/modeling_abt.parquet` | **2.4 GB** | Renamed input ABT (synth_credit_score_* → synth_bureau_score_*) | LARGE — gitignored |
| `artifacts/phase2_rerun_v2/modeling_feature_catalog.csv` | 480 KB | Renamed catalog | Methodology — features |
| `artifacts/phase2_rerun_v2/final_model.pkl` | **207 MB** | LR full-F6E saved model | LARGE — gitignored, refit at runtime |
| `artifacts/phase2_rerun_v2/final_feature_set.csv` | 549 B | LR full-F6E final 22 features | Results — model |
| `artifacts/phase2_rerun_v2/final_coefficients.csv` | 2 KB | LR full-F6E coefficients + p-values | Results — model interpretation |
| `artifacts/phase2_rerun_v2/model_metrics.json` | 303 B | LR full-F6E OOT metrics | Results — model performance |
| `artifacts/phase2_rerun_v2/calibration_metrics.csv` | 683 B | OOT calibration deciles for LR full-F6E | Methodology — calibration |
| `artifacts/phase2_rerun_v2/pd_scores.parquet` | 6.9 MB | LR full-F6E PD scores per row | Results — score distribution |
| `artifacts/phase2_rerun_v2/stage1_selected_features.csv` | 10 KB | Stage 1 prescreening survivors | Methodology — feature selection |
| `artifacts/phase2_rerun_v2/stage2_selected_features.csv` | 1.6 KB | Stage 2 Lasso survivors | Methodology — feature selection |
| `artifacts/phase2_rerun_v2/phase2_modeling_report.md` | 13 KB | Phase 2 narrative | Methodology — feature selection |
| `artifacts/phase2_rerun_v2/exported_notebook_script.py` | 14 KB | Auto-exported notebook | Reproducibility |
| `artifacts/phase2_rerun_v2/diagnostics/test1_f6e_ablation.json` | 1.2 KB | F6E ablation result | Methodology — F6E ablation |
| `artifacts/phase2_rerun_v2/diagnostics/test2_lasso_stability.json` | 3.4 KB | 9 (C, seed) Lasso stability runs | Methodology — Lasso stability |
| `artifacts/phase2_rerun_v2/diagnostics/test3_calibration.json` | 1.3 KB | Leak-free calibration result (Platt + isotonic) | Methodology — calibration |
| `artifacts/phase2_rerun_v2/diagnostics/test4_lightgbm.json` | 3.6 KB | Pre-retune LightGBM diagnostic | Methodology |
| `artifacts/phase2_rerun_v2/diagnostics/test5_stress_test_design.json` | 0.8 KB | Stress test plan + sanity check | Methodology |
| `artifacts/phase2_rerun_v2/diagnostics/calibrators.pkl` | 3 KB | Platt + isotonic for LR full-F6E | Reproducibility |

Status: **REQUIRED** (excluding the 2.4 GB parquet and 207 MB pkl which are
LARGE and gitignored).

### A3. Phase 2A LightGBM tuned (PRIMARY model)

| Path | Size | Purpose | Used in chapter |
|------|-----:|---------|-----------------|
| `artifacts/pd_model/lightgbm_tuned_model.pkl` | 375 KB | Tuned booster + Platt + isotonic + feature_list | REQUIRED — primary PD |
| `artifacts/pd_model/lightgbm_tuning_results.json` | 16 KB | 30 Optuna trials + best params + verification gates | Methodology — LightGBM |
| `artifacts/pd_model/lightgbm_feature_importance.csv` | 16 KB | Per-feature gain + split count | Results — feature importance |
| `artifacts/pd_model/lightgbm_retune_report.md` | 11 KB | Retune narrative | Methodology — LightGBM |
| `artifacts/pd_model/lightgbm_model.pkl` | 42 KB | Pre-retune model (broken; archive) | ARCHIVE only |

Status: **REQUIRED** (except the pre-retune pkl which is archive).

### A4. Phase 2B Scorecard

| Path | Size | Purpose | Used in chapter |
|------|-----:|---------|-----------------|
| `artifacts/scorecard/woe_transformed_abt.parquet` | 5.6 MB | Scorecard ABT + per-row PD | REQUIRED for replication |
| `artifacts/scorecard/scorecard_table.csv` | 3.7 KB | 7 features × bins × WoE × beta × points | Results — scorecard |
| `artifacts/scorecard/scorecard_metrics.json` | 4.8 KB | Scorecard OOT metrics | Results — scorecard |
| `artifacts/scorecard/scorecard_summary.xlsx` | 9.3 KB | 1-page Excel summary | Appendix |
| `artifacts/scorecard/optbin_definitions.json` | 6 KB | OptBinning bin definitions | Reproducibility |
| `artifacts/scorecard/phase2b_scorecard_report.md` | 14 KB | Scorecard narrative | Results — scorecard |
| `artifacts/scorecard/exported_notebook_script.py` | 20 KB | Auto-exported | Reproducibility |
| `artifacts/scorecard/robustness_full_f6e/scorecard_table.csv` | 28 KB | Full-F6E scorecard (NO row-level PD) | Optional — not used |
| `artifacts/scorecard/robustness_full_f6e/scorecard_metrics.json` | 3.7 KB | Full-F6E metrics only | Optional |

Status: REQUIRED for the no-F6E primary scorecard. The full-F6E robustness
folder is optional (no row-level PD generated).

### A5. Phase 3 + 4 Economic framework

| Path | Size | Purpose | Used in chapter |
|------|-----:|---------|-----------------|
| `artifacts/economic_framework/economics_per_account.parquet` | 15 MB | Per-account base economics + 4 PD scores | REQUIRED |
| `artifacts/economic_framework/sensitivity_grid.parquet` | 11 KB | 150-cell Phase 3.1B grid | Results — sensitivity |
| `artifacts/economic_framework/economic_stress_grid.parquet` | 39 KB | 576-cell Phase 3.2 grid | Results — stress |
| `artifacts/economic_framework/cutoff_results.csv` | 19 KB | 200 threshold rows (Phase 3.1B) | Results — cut-off |
| `artifacts/economic_framework/optimal_cutoffs.json` | 5.3 KB | k\* per (PD model, APR scenario) | Results — cut-off |
| `artifacts/economic_framework/anchor_scenarios.json` | 2.2 KB | Initial 3 anchors | ARCHIVE |
| `artifacts/economic_framework/anchor_scenarios_v2.json` | 2.3 KB | Final 4 anchors + Youden + special probs | REQUIRED |
| `artifacts/economic_framework/asb_comparison.csv` | 0.6 KB | ASB vs Lifetime per tenor | Results — ASB |
| `artifacts/economic_framework/tenor_economics.csv` | 0.5 KB | Per-tenor mean/total profit | Results — tenor split |
| `artifacts/economic_framework/multi_pd_base_scenario.json` | 1.1 KB | 4-PD base comparison | Results — multi-model |
| `artifacts/economic_framework/bootstrap_anchor_results.parquet` | 215 KB | 4,000 bootstrap × anchor rows | Results — bootstrap |
| `artifacts/economic_framework/bootstrap_ci_summary.csv` | 4.1 KB | 32 metric × CI rows | Results — bootstrap |
| `artifacts/economic_framework/bootstrap_cutoff_distributions.csv` | 2.3 KB | Decile-level cutoff distributions | Optional |
| `artifacts/economic_framework/op_cost_ablation.csv` | 1.1 KB | 8-cell op_cost spotlight | Results — op_cost |
| `artifacts/economic_framework/phase4_2_combined_grid.csv` | 9.2 KB | 36-cell combined Gini × op × scenario | Results — combined stress |
| `artifacts/economic_framework/stress_cutoff_results.csv` | 75 KB | 576 cells with cut-off metrics | Optional |
| `artifacts/economic_framework/schema_audit_summary.csv` | 1.3 KB | Phase 3.0 schema audit | Methodology — schema |
| `artifacts/economic_framework/tenor_default_diagnostic.csv` | 0.2 KB | Phase 3.1A 12m exclusion data | Limitations — 12m |
| `artifacts/economic_framework/tenor_recommendation.json` | 1.2 KB | 12m recommendation | Limitations — 12m |
| `artifacts/economic_framework/five_account_validation.csv` | 1.7 KB | 5-account formula validation | Methodology — formula |
| `artifacts/economic_framework/profit_framework_report.md` | 12 KB | Phase 3.1B narrative | Results |
| `artifacts/economic_framework/phase3_2_stress_report.md` | 7.7 KB | Phase 3.2 narrative | Results |
| `artifacts/economic_framework/phase4_1_bootstrap_report.md` | 11 KB | Phase 4.1 narrative | Results |
| `artifacts/economic_framework/phase4_2_report.md` | 13 KB | Phase 4.2 narrative | Results |
| `artifacts/economic_framework/phase4_3_4_report.md` | 10 KB | Phase 4.3+4.4 narrative | Results |
| `artifacts/economic_framework/phase3_formula_validation_report.md` | 13 KB | Phase 3.1A narrative | Methodology — formula |
| `artifacts/economic_framework/schema_audit_report.md` | 11 KB | Phase 3.0 narrative | Methodology — schema |
| `artifacts/economic_framework/exported_notebook_script.py` | 20 KB | 02 nb auto-export | Reproducibility |
| `artifacts/economic_framework/exported_bootstrap_script.py` | 16 KB | 04 nb auto-export | Reproducibility |
| `artifacts/economic_framework/exported_pd_quality_stress_script.py` | 13 KB | 05 nb auto-export | Reproducibility |

Status: REQUIRED.

### A6. PD-quality stress + op_cost robustness

| Path | Size | Purpose | Used in chapter |
|------|-----:|---------|-----------------|
| `artifacts/pd_quality_stress/pd_variants.parquet` | 3 MB | PD scores for raw + 3 stressed Gini variants | Results — PD stress |
| `artifacts/pd_quality_stress/cutoffs_by_gini.csv` | 4 KB | 16-cell PART A grid | Results — PD stress |
| `artifacts/op_cost_robustness/cutoffs_by_op_cost.csv` | 3 KB | 12-cell PART B grid | Results — op_cost |

Status: REQUIRED.

### A7. Calibration verification

| Path | Size | Purpose | Used in chapter |
|------|-----:|---------|-----------------|
| `artifacts/calibration_verification/calibration_summary.csv` | 1.4 KB | 7-source calibration metrics | Methodology + Results — calibration |
| `artifacts/calibration_verification/o_to_e_by_decile.csv` | 1.5 KB | Observed:expected per decile | Results — calibration |
| `artifacts/calibration_verification/reliability_data.csv` | 6.2 KB | Bin-level data for Fig 6 | Used in Fig 6 |

Status: REQUIRED.

### A8. Figures (Phase 4.4)

| Path | Size | Used in chapter |
|------|-----:|-----------------|
| `artifacts/figures/fig1_profit_curves.{pdf,png}` | 41 + 111 KB | Results — profit framework |
| `artifacts/figures/fig2_cutoff_gap_vs_gini.{pdf,png}` | 22 + 97 KB | Results — PD-quality stress |
| `artifacts/figures/fig3_op_cost_vs_kstar.{pdf,png}` | 25 + 88 KB | Results — cost stress |
| `artifacts/figures/fig4_asb_vs_lifetime.{pdf,png}` | 21 + 52 KB | Methodology — formula choice |
| `artifacts/figures/fig5_bootstrap_ci_density.{pdf,png}` | 34 + 129 KB | Results — statistical robustness |
| `artifacts/figures/fig6_reliability_diagrams.{pdf,png}` | 24 + 175 KB | Methodology — calibration |
| `artifacts/figures/fig7_feature_importance.{pdf,png}` | 22 + 173 KB | Methodology — model interpretation |
| `artifacts/figures/fig8_stress_heatmap.{pdf,png}` | 36 + 97 KB | Results — combined stress |
| `artifacts/figures/fig9_sensitivity_hierarchy.{pdf,png}` | 17 + 46 KB | Discussion — drivers |

Status: REQUIRED.

## B. Thesis-required source code

| Path | Lines / size | Purpose |
|------|-------------:|---------|
| `src/economics.py` | ~430 lines, 17 KB | Locked Phase 3 formulas + vectorized batch helpers |
| `src/calibration.py` | ~240 lines, 9 KB | Temporal split, Platt, isotonic, perturb_to_target_gini |
| `src/governance.py` | ~120 lines, 4 KB | filter_pd_eligible, validate_no_score_columns, etc. |
| `src/modeling.py` | ~270 lines, 9.5 KB | Stage 1, Lasso (single-fit + CV), statsmodels logit, VIF |
| `src/evaluation.py` | ~120 lines, 4 KB | Gini, KS, Brier, calibration metrics, PSI |
| `src/scorecard.py` | ~480 lines, 17 KB | OptBinning + WoE + scorecard build |
| `src/__init__.py` | 0 bytes | package marker |
| `tests/test_economics.py` | ~240 lines, 9 KB | 9 unit tests on locked formulas |

Status: REQUIRED.

## C. Notebooks (one per analysis phase)

| Path | Cells | Status |
|------|------:|--------|
| `notebooks/01_phase2_feature_selection.ipynb` | ~24 | REQUIRED |
| `notebooks/01a_phase2_diagnostics.ipynb` | 26 | REQUIRED |
| `notebooks/01b_phase2_lightgbm_retune.ipynb` | 15 | REQUIRED |
| `notebooks/01c_scorecard.ipynb` | (varies) | REQUIRED |
| `notebooks/02_economic_framework.ipynb` | 22 | REQUIRED |
| `notebooks/03_economic_stress_test.ipynb` | (varies) | REQUIRED |
| `notebooks/04_bootstrap_cutoff_ci.ipynb` | (varies) | REQUIRED |
| `notebooks/05_pd_quality_opcost_stress.ipynb` | (varies) | REQUIRED |
| `notebooks/06_calibration_verification.ipynb` | 4 | REQUIRED |
| `notebooks/07_visualization.ipynb` | 20 | REQUIRED |

Status: REQUIRED.

## D. Optional / archive artifacts

| Path | Status | Reason |
|------|--------|--------|
| `artifacts/scorecard/robustness_full_f6e/` | OPTIONAL | No row-level PD parquet; used only for spot-check |
| `artifacts/economic_framework/anchor_scenarios.json` | ARCHIVE | Superseded by `anchor_scenarios_v2.json` |
| `artifacts/pd_model/lightgbm_model.pkl` | ARCHIVE | Pre-retune broken model |
| `artifacts/economic_framework/cutoff_results.csv` | OPTIONAL | Phase 3.1B threshold sweep; superseded by stress grid |
| `artifacts/economic_framework/stress_cutoff_results.csv` | OPTIONAL | Compact view of `economic_stress_grid.parquet` |
| `_recovery/` (entire dir) | OPTIONAL — local dev | Diagnostic / dev scripts; gitignored |

## E. Large files (gitignored, regenerable from notebooks)

| Path | Size | Regeneration cost |
|------|-----:|-------------------|
| `artifacts/phase1_5_feature_factory/thesis_wide_abt_expanded.parquet` | 2.4 GB | ~2 min via `notebooks/...` |
| `artifacts/phase2_rerun_v2/modeling_abt.parquet` | 2.4 GB | ~30 s rename script |
| `artifacts/phase2_rerun_v2/final_model.pkl` | 207 MB | ~30 s LR refit |
| `artifacts/thesis_wide_abt_800d_60m_p00/thesis_wide_abt.csv` | 889 MB | ~6 min via `build_wide_abt.py` |
| `artifacts/final_data_800d_60m_p00/transactions.csv` | 1.55 GB | ~13 h simulator rerun (NOT recommended) |
| `artifacts/final_data_800d_60m_p00/collection_actions.csv` | 1.05 GB | same |
| `artifacts/final_data_800d_60m_p00/summary_abt_*.csv` (60 files) | ~28 GB total | same |

Status: All gitignored. Code + small artifacts in the repo are sufficient
to regenerate everything from the simulator output (which itself is the
expensive bit to regenerate).

## F. Missing artifacts (gaps documented)

| Item | Why missing | Workaround |
|------|-------------|------------|
| Scorecard full-F6E + Platt row-level PD | Phase 2B optional run produced metrics + table but not parquet | Documented as out-of-scope; thesis claims "4 PD models + 3 stressed variants" |
| Empirical LGD per default | Computational cost + scope discipline | Future Work F1 in `thesis_limitations.md` |
| Multi-seed bootstrap | Single-seed only | Future Work F6 |
| Real-data replication | Out of thesis scope | Future Work F2 + F7 |

No critical gaps. The thesis can be written without any further runs.
