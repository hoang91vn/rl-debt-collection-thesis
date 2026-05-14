# Thesis Evidence Map

**Purpose**: Maps every major thesis claim to its supporting artifact, figure, key numerical value, and methodological caveat. Each claim uses cautious wording per the locked phrasing rule ("within tested scenario space" / "across bootstrap resamples", not universal proof).

**Population shorthand used below**:
- *Modeling pop* = 534,314 rows (full Phase 2 wide ABT)
- *Economic pop* = 235,968 rows (24m + 36m only)
- *OOT economic pop* = 64,027 rows (cohorts 202701-202706, 24m + 36m only)

---

## Claim 1 — Profit-driven cutoffs outperform Youden in expected dollar profit

**Wording**: *"Within the tested anchor scenario space and across the 1,000 OOT bootstrap resamples, the profit-driven cutoff produces strictly higher total Expected Profit than the Youden's J (TPR-FPR) cutoff."*

| Element | Value |
|---------|-------|
| Supporting artifact | `artifacts/economic_framework/bootstrap_anchor_results.parquet` |
| Supporting figure | `artifacts/figures/fig5_bootstrap_ci_density.{pdf,png}` |
| Supporting table | `artifacts/economic_framework/bootstrap_ci_summary.csv` |
| Key numerical value | `profit_uplift > 0` in **4,000 / 4,000** (1000 resamples × 4 anchors) |
| Caveat | Holds within tested PD-multiplier × LGD × COF × acquisition × APR space and within OOT subset (n=64,027). Not a universal claim about all credit portfolios. |

---

## Claim 2 — Profit cutoff may be more permissive OR less permissive than Youden depending on stress

**Wording**: *"In light-stress scenarios the profit-driven cutoff is more permissive (higher k\*); in adverse-stress scenarios with high op_cost it can become less permissive than Youden, while still producing higher dollar profit."*

| Element | Value |
|---------|-------|
| Supporting artifact | `artifacts/economic_framework/phase4_2_combined_grid.csv` |
| Supporting figure | `artifacts/figures/fig8_stress_heatmap.{pdf,png}` |
| Key numerical value | Across the 36-cell combined Gini × op_cost × scenario grid: profit cutoff > Youden in **31/36 cells** (cutoff_gap > 0); < Youden in 5/36 cells (all in adverse_stress at op_cost ≥ 2%); profit_uplift > 0 in **36/36 cells** regardless of cutoff direction. |
| Caveat | "More permissive vs less permissive" is direction; "higher dollar profit" is outcome. The two need not align — being less permissive can still beat Youden if Youden's accepted set contains loss-making loans. |

---

## Claim 3 — Across tested stress cells, profit uplift over Youden remains positive

**Wording**: *"Across all 64 tested stress cells (Phase 4.2 PARTS A + C; combined PD-quality and op_cost stress), the dollar profit uplift of the profit-driven cutoff over Youden's J is strictly positive."*

| Element | Value |
|---------|-------|
| Supporting artifacts | `artifacts/pd_quality_stress/cutoffs_by_gini.csv` (16 cells), `artifacts/op_cost_robustness/cutoffs_by_op_cost.csv` (12 cells), `artifacts/economic_framework/phase4_2_combined_grid.csv` (36 cells) |
| Supporting figures | Fig 2 (gap vs Gini), Fig 3 (op_cost vs k*), Fig 8 (heatmap) |
| Key numerical value | profit_uplift > 0 in **16/16 + 12/12 + 36/36 = 64/64** stress cells |
| Caveat | Counted within the tested grid. The minimum uplift (adverse_stress + Gini 0.30 + op_cost 4%) is small ($0.50M) but positive. |

---

## Claim 4 — The value of profit-driven cutoff selection widens as PD discrimination weakens

**Wording**: *"In the tested PD-quality stress, the cutoff gap (profit k\* − Youden k) widens monotonically as the PD model's Gini falls from 0.80 (raw LightGBM) to 0.30 (heavily perturbed)."*

| Element | Value |
|---------|-------|
| Supporting artifact | `artifacts/pd_quality_stress/cutoffs_by_gini.csv` |
| Supporting figure | `artifacts/figures/fig2_cutoff_gap_vs_gini.{pdf,png}` |
| Key numerical value | Mean cutoff_gap by Gini: raw 0.80 → +15.5 pp; Gini 0.60 → +21.2 pp; Gini 0.45 → +30.8 pp; Gini 0.30 → +35.7 pp |
| Caveat | The widening reflects Youden's J becoming more conservative as PD distinguishability falls (TPR-FPR plateau) while the profit-optimal stays high because most accounts remain profitable on average. |

---

## Claim 5 — Operational cost can push the framework into reject-most regime

**Wording**: *"In the adverse-stress scenario combined with op_cost_annual ≥ 4%, the profit-optimal approval rate collapses to <1% (reject-most), the only regime change observed in the entire 64-cell stress space."*

| Element | Value |
|---------|-------|
| Supporting artifact | `artifacts/op_cost_robustness/cutoffs_by_op_cost.csv` |
| Supporting figure | `artifacts/figures/fig3_op_cost_vs_kstar.{pdf,png}` |
| Key numerical value | adverse_stress at op_cost=0.04: k\* = **0.31%** (in PART B), 0.08-0.14% in PART C combined cells. All other stress cells have k\* > 70%. |
| Caveat | The regime change requires the *combination* of adverse_stress (PD×5, COF=6%, acq=$500, LGD=0.85, flat 18% APR) AND op_cost≥4%. Less extreme scenarios stay in interior. |

---

## Claim 6 — Tenor-aware lifetime economics materially differs from ASB one-period profit

**Wording**: *"The locked tenor-aware Lifetime profit formula produces materially higher portfolio profit estimates than the ASB single-period benchmark, with the bias growing with tenor (≈9% understatement on 24m loans; ≈40% understatement on 36m loans)."*

| Element | Value |
|---------|-------|
| Supporting artifact | `artifacts/economic_framework/asb_comparison.csv` |
| Supporting figure | `artifacts/figures/fig4_asb_vs_lifetime.{pdf,png}` |
| Key numerical value | ASB / Lifetime total profit ratio: 24m = 0.91 (-9%); **36m = 0.60 (-40%)**; combined 24+36m = 0.71 (-29%) |
| Caveat | ASB is a single-period formula assuming one full year of interest at full loan amount; Lifetime correctly applies amortization-based EAD and accumulates interest over the full tenor. Difference is structural to the formula, not noise. |

---

## Claim 7 — 12-month loans are excluded from economic analysis due to a structural zero-default artifact

**Wording**: *"Twelve-month loans were excluded from the economic analysis population because the simulator's writeoff trigger (12 missed installments → coll_status=8) is structurally unreachable within the `default_flag_12m` target window (offsets 12-23 from origination), producing a 0% observed default rate that would corrupt portfolio-level economics."*

| Element | Value |
|---------|-------|
| Supporting artifact | `artifacts/economic_framework/tenor_default_diagnostic.csv` and `tenor_recommendation.json` |
| Supporting figures | Phase 3.1A validation report Section 3 |
| Key numerical value | 12m loans: **298,346 rows / 0 defaults** (0.0000% DR) — vs 24m 2.31% DR / 36m 4.43% DR. After exclusion, economic pop = 235,968 rows. |
| Caveat | This is a simulator artifact, NOT a real-world conclusion that 12m loans are risk-free. Thesis Limitations chapter must document this. |

---

## Claim 8 — LightGBM is the primary predictive model, with a calibration caveat on the economics-OOT subset

**Wording**: *"LightGBM (tuned via Optuna 30 trials, Platt-calibrated on cohorts 202611-202612) is the primary PD model, achieving OOT Gini 0.804 and AUC 0.902. On the economics-OOT subset (24m + 36m only), the Platt-calibrated mean predicted PD under-predicts the empirical base rate by approximately 2× because the calibration slice has a different cohort base rate than the eco subset."*

| Element | Value |
|---------|-------|
| Supporting artifacts | `artifacts/pd_model/lightgbm_tuned_model.pkl`, `lightgbm_tuning_results.json`, `lightgbm_retune_report.md`, `artifacts/calibration_verification/calibration_summary.csv` |
| Supporting figures | `fig6_reliability_diagrams.{pdf,png}` (panel 1), `fig7_feature_importance.{pdf,png}` (left panel) |
| Key numerical value | LightGBM: OOT AUC 0.902, Gini 0.804, ECE 0.0098, mean_pred 0.94% vs base 1.92% (mean_pred / observed = 0.49). PD-multiplier scenarios in Phase 3 (×2, ×3, ×5) approximately correct for this. |
| Caveat | The under-prediction is a real calibration weakness on the eco-OOT subset specifically; it does not invalidate the profit-vs-Youden hypothesis (which survives at every PD multiplier). |

---

## Claim 9 — Bootstrap CIs on OOT economics subset support stability of anchor scenario findings

**Wording**: *"Across 1,000 stratified-by-tenor bootstrap resamples of the 64,027-row OOT economics subset, every anchor scenario retains its category classification (approve-all vs interior) with narrow CIs, and the profit_uplift over Youden remains strictly positive in every resample."*

| Element | Value |
|---------|-------|
| Supporting artifact | `artifacts/economic_framework/bootstrap_anchor_results.parquet`, `bootstrap_ci_summary.csv`, `anchor_scenarios_v2.json` |
| Supporting figure | `fig5_bootstrap_ci_density.{pdf,png}` |
| Key numerical value | k\* CI by anchor: optimistic [100.00, 100.00]; realistic_central_boundary [99.16, 99.36]; moderate_interior [94.99, 95.50]; adverse_stress [84.31, 85.27]. Across 4,000 (anchor × resample) combinations: profit_uplift > 0 in 100%. |
| Caveat | Bootstrap captures only sampling uncertainty within the OOT subset, not (a) PD model uncertainty, (b) cohort/temporal drift uncertainty, (c) APR/LGD assumption uncertainty. Use phrasing "across 4,000 bootstrap resamples, profit_uplift > 0 held in 100% of resamples", NOT "100% probability". |

---

## Cross-claim summary

| Claim | Strength of evidence | Boundary condition |
|-------|----------------------|--------------------|
| 1. Profit > Youden in $ | Very strong (4000/4000 resamples) | OOT subset, 4 anchors |
| 2. Direction varies | Strong (5/36 less permissive but still beats Youden) | Heavy adverse + high op_cost |
| 3. Uplift > 0 always | Very strong (64/64 stress cells) | Tested grid |
| 4. Value widens with weak PD | Strong (monotonic across 4 Gini levels × 4 anchors) | PD perturbation method = `perturb_to_target_gini` |
| 5. Reject-most exists | Single-cell evidence (1/64) | adverse + op_cost ≥ 4% |
| 6. ASB vs Lifetime gap | Definitional (formula difference) | Real-world tenors are 12/24/36 |
| 7. 12m exclusion | Structural (0/298,346 defaults) | Simulator artifact |
| 8. LightGBM primary | Multiple metrics (AUC 0.90, Gini 0.80) + calibration caveat | Eco-OOT subset specifically |
| 9. Bootstrap stability | 4 narrow CIs; 0 boundary flips | Within-OOT sampling only |
