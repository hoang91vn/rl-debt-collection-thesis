# Phase 4.3 + 4.4 — Calibration Verification + Publication Visualization

**Date**: 2026-05-09
**Population**: OOT economics-eligible subset (n=64,027; base rate 1.916%)
**Wall time**: ~2 min total (calibration ~30 s + 9 figures ~90 s)

---

## Phase 4.3 — Calibration Verification

7 PD sources verified. (8th source `Scorecard full-F6E + Platt` was listed in the
spec but its row-level PD parquet was not generated in Phase 2B's optional
robustness run — only metrics + table exist. Excluded from row-level
calibration here; documented for future Phase 4.5 if needed.)

### Calibration summary on OOT (64,027 rows, base rate 1.916%)

| PD source | mean_pred | AUC | Gini | KS | Brier | ECE | mean_pred / obs |
|-----------|----------:|----:|-----:|---:|------:|----:|---------------:|
| **LightGBM Platt (PRIMARY)** | 0.939% | 0.9022 | **0.8044** | 0.6461 | 0.01721 | 0.0098 | **0.49** ⚠️ |
| LR full-F6E + Platt | 2.070% | 0.8640 | 0.7281 | 0.5595 | 0.01671 | **0.0026** | 1.08 |
| LR no-F6E + Platt | 2.076% | 0.8400 | 0.6800 | 0.5458 | 0.01703 | **0.0029** | 1.08 |
| Scorecard no-F6E + Platt | 0.918% | 0.8030 | 0.6061 | 0.4813 | 0.01794 | 0.0100 | **0.48** ⚠️ |
| Stressed Gini 0.60 | 1.916% | 0.8015 | 0.6030 | 0.4690 | 0.02039 | 0.0143 | 1.00 |
| Stressed Gini 0.45 | 1.916% | 0.7228 | 0.4456 | 0.3283 | 0.02418 | 0.0238 | 1.00 |
| Stressed Gini 0.30 | 1.916% | 0.6513 | 0.3027 | 0.2288 | 0.02868 | 0.0312 | 1.14 |

### Key calibration findings

1. **PRIMARY LightGBM under-predicts by ~50%** on the eco-pop OOT (mean predicted 0.94% vs base 1.92%). The Platt calibrator was fit on the calib slice (cohorts 202611-202612) which had a different base rate than the eco-OOT (cohorts 202701-202706 filtered to 24m+36m only).
2. **Same pattern for Scorecard no-F6E** — under-predicts by ~50%. Both stem from the same temporal calibration recipe (Platt fit on 202611-202612 train cohorts) being applied to a population (eco-OOT 24m+36m) whose base rate is ~2× the calib slice base rate.
3. **LR variants slightly over-predict** (1.08×) — Platt on LR scores happens to land closer to the eco-OOT base rate by coincidence of the LR score distribution shape.
4. **Stressed Gini variants are perfectly mean-calibrated by construction** (`perturb_to_target_gini` re-anchors mean to base rate per design).
5. **ECE rankings**: LR full-F6E (0.0026) and LR no-F6E (0.0029) are best calibrated. LightGBM (0.0098) and Scorecard (0.0100) are next. Stressed variants (0.014-0.031) degrade with discrimination loss.

### Implication for thesis

The mean-prediction bias in LightGBM and Scorecard is a real weakness of the
locked Platt-on-calib recipe at *this* eco-OOT subset. **The PD-multiplier
×2 / ×3 / ×5 in the locked anchor scenarios actually CORRECTS for this
under-prediction**: PD×2 raises LightGBM mean from 0.94% to 1.88% — within a
few bp of the OOT base rate 1.92%. Anchor `realistic_central_boundary`
(PD×2) is therefore approximately mean-calibrated; `moderate_interior` (PD×3)
slightly over-predicts; `adverse_stress` (PD×5) heavily over-predicts.

This is a useful methodological observation but does **not** invalidate any
upstream finding — the profit-vs-Youden hypothesis is computed at every
PD-multiplier and survives all of them.

### Phase 4.3 files produced

```
artifacts/calibration_verification/
  calibration_summary.csv      (1.4 KB — 7 PD sources × 9 metrics)
  o_to_e_by_decile.csv         (1.6 KB — observed:expected per decile)
  reliability_data.csv         (6.2 KB — bin-level mean_pred/obs_rate)
notebooks/06_calibration_verification.ipynb
```

---

## Phase 4.4 — Publication Visualization

9 figures, each saved as **PDF (300 DPI vector) + PNG (150 DPI raster)** with
color-blind-safe palette and source-line attribution. All saved to
`artifacts/figures/`.

### Figure inventory

| # | File | Purpose | Source data |
|--:|------|---------|-------------|
| 1 | `fig1_profit_curves.{pdf,png}` | Cumulative profit vs accepted percentile, 4 anchor lines + k* and Youden markers | `economics_per_account.parquet` (OOT) |
| 2 | `fig2_cutoff_gap_vs_gini.{pdf,png}` | "Profit framework value WIDENS with weaker PD models" | `pd_quality_stress/cutoffs_by_gini.csv` |
| 3 | `fig3_op_cost_vs_kstar.{pdf,png}` | op_cost drives k* downward; reject-most annotation at adverse + 4% | `op_cost_robustness/cutoffs_by_op_cost.csv` |
| 4 | `fig4_asb_vs_lifetime.{pdf,png}` | ASB single-period UNDERESTIMATES by ~40% on 36m | `asb_comparison.csv` |
| 5 | `fig5_bootstrap_ci_density.{pdf,png}` | 4-panel bootstrap density of profit_uplift with 2.5/50/97.5 markers | `bootstrap_anchor_results.parquet` |
| 6 | `fig6_reliability_diagrams.{pdf,png}` | 4-panel reliability diagrams for the 4 main PD models | `calibration_verification/reliability_data.csv` |
| 7 | `fig7_feature_importance.{pdf,png}` | LightGBM gain (top 20) vs LR signed coefficients (top 20) | `lightgbm_feature_importance.csv` + `final_coefficients.csv` |
| 8 | `fig8_stress_heatmap.{pdf,png}` | 3-panel heatmap of profit uplift by scenario × Gini × op_cost | `phase4_2_combined_grid.csv` |
| 9 | `fig9_sensitivity_hierarchy.{pdf,png}` | Bar chart of parameter spread on k* | Phase 3.2 driver analysis |

### Visualization issues / observations

- **Fig 1**: profit curves for adverse_stress dip below zero late in the curve (loss-making approvals at high PD). Profit-optimal `k*` (circle marker) sits at the peak; Youden threshold (× marker) sits to the left. Visual confirms profit-driven cutoff is more permissive than Youden in 3/4 anchors at base op_cost.
- **Fig 2**: clear monotonic widening of cutoff gap as Gini falls — strongest visual support of the "profit framework value WIDENS" finding.
- **Fig 3**: adverse_stress curve plunges from 84.9% (op=0%) to 0.31% (op=4%); the reject-most annotation arrow makes the regime change explicit.
- **Fig 4**: ASB bars consistently below LT bars; the +/-% labels above ASB bars show the relative bias (-9% for 24m, -40% for 36m).
- **Fig 5**: bootstrap densities are tight (low std), confirming the bootstrap-CI evidence is statistically robust. The 2.5%-CI dashed line stays clearly above $0 in all 4 panels.
- **Fig 6**: visual confirmation of the calibration finding from Phase 4.3 — LightGBM and Scorecard reliability curves sit BELOW the diagonal (under-prediction); LR variants hug or sit slightly above.
- **Fig 7**: LightGBM dominated by `job_code_x_income` (F4 interaction). LR dominated by `app_nom_job_code`, `synth_seg_*`, `marital_x_n_children`. Different feature mixes — the two models capture overlapping but non-identical signal.
- **Fig 8**: 3 op_cost panels show profit uplift growing as Gini falls (left → right colours warmer green) and shrinking as scenario severity grows (top → bottom rows). At op=4% adverse cells, uplift remains positive (red would indicate negative — there are no red cells).
- **Fig 9**: PD multiplier bar (3.54 pp) and APR strategy bar (2.32 pp) clearly dominate the lower bars (LGD 1.28, Acquisition 0.43, COF 0.43).

No technical visualization issues encountered. All figures rendered cleanly at first try.

### Phase 4.4 files produced

```
artifacts/figures/
  fig1_profit_curves.pdf            41 KB
  fig1_profit_curves.png           111 KB
  fig2_cutoff_gap_vs_gini.pdf       22 KB
  fig2_cutoff_gap_vs_gini.png       97 KB
  fig3_op_cost_vs_kstar.pdf         25 KB
  fig3_op_cost_vs_kstar.png         88 KB
  fig4_asb_vs_lifetime.pdf          21 KB
  fig4_asb_vs_lifetime.png          52 KB
  fig5_bootstrap_ci_density.pdf     34 KB
  fig5_bootstrap_ci_density.png    129 KB
  fig6_reliability_diagrams.pdf     24 KB
  fig6_reliability_diagrams.png    175 KB
  fig7_feature_importance.pdf       22 KB
  fig7_feature_importance.png      173 KB
  fig8_stress_heatmap.pdf           36 KB
  fig8_stress_heatmap.png           97 KB
  fig9_sensitivity_hierarchy.pdf    17 KB
  fig9_sensitivity_hierarchy.png    46 KB
notebooks/07_visualization.ipynb
```

Total: 9 PDF + 9 PNG = **18 figure files**, 1.2 MB combined.

---

## Combined Phase 4.3 + 4.4 wall time

| Step | Wall |
|------|-----:|
| Phase 4.3 calibration (7 sources × ECE/Brier/KS/reliability) | ~30 s |
| Phase 4.4 figures 1-9 generation | ~90 s |
| **Total** | **~2 min** |

Far under the 1-2 day estimate in the spec — vectorized helpers + pre-computed
artifacts from Phases 3-4.2 made everything fast.

---

## Recommendation: ready for thesis writing?

**YES**, with two caveats:

1. **Document the LightGBM mean-PD under-prediction** in the thesis Methodology
   chapter. Frame it as: "the locked Platt calibration on cohorts
   202611-202612 is mean-anchored to the calib slice's base rate (~0.85%);
   the 24m+36m subset has a higher OOT base rate (1.92%), so applying the
   calibrator there produces under-predicted PD by ~2×. The Phase 3
   PD-multiplier scenarios (×2, ×3, ×5) span this gap and the
   profit-vs-Youden finding survives every multiplier."

2. **The Scorecard full-F6E robustness PD parquet was not generated** in
   Phase 2B's optional run. If the thesis claims to compare 5 PD models,
   either add a quick Phase 4.5 to score the full-F6E scorecard, or restrict
   the claim to "4 PD models + 3 stressed variants". Recommend the latter
   for scope discipline.

### Empirical evidence map for thesis chapters

| Thesis chapter | Empirical evidence available |
|----------------|------------------------------|
| Methodology — PD model comparison | calibration_summary.csv + Fig 6, Fig 7 |
| Results — Profit framework | Fig 1 (profit curves), Fig 4 (ASB benchmark), profit_framework_report.md |
| Results — Cut-off finding | bootstrap_ci_summary.csv + Fig 5 (CIs), Fig 1 (markers) |
| Results — PD-quality stress | Fig 2, phase4_2_combined_grid.csv |
| Results — Cost stress | Fig 3, op_cost_ablation.csv |
| Results — Combined stress | Fig 8 |
| Discussion — Driver analysis | Fig 9, Phase 3.2 driver analysis |
| Limitations | 12-month exclusion finding (Phase 3.1A), LightGBM under-prediction (Phase 4.3), op_cost sensitivity (Phase 4.2 PART B) |

---

## Stopping point

Per spec: **"Stop after Phase 4.4 figures complete."**

All deliverables in place:
- Calibration verification (Phase 4.3) ✓
- 9 publication figures (Phase 4.4) ✓
- Notebooks 06 and 07 executed clean ✓
- Combined report (this file) ✓

Awaiting your decision on next phase (thesis writing, Phase 4.5
scorecard-full-F6E PD generation, or other).
