# Phase 2A Modeling Report — initial run + 5 diagnostics

**Status**: Phase 2A initial run + 5 mandatory diagnostics complete. **NOT READY for Phase 2B/3** without the corrections recommended below.

---

## 1. Phase 2A initial run (full-F6E LR with naive OOT calibration)

| Component | Result |
|-----------|--------|
| Logistic / L1 pipeline | Done |
| Final feature set | 22 features (17 F6E, 3 ORIGINAL_APP, 1 F4, 1 F5A) |
| F6D negative controls | 0 survived (PASS) |
| OOT AUC | 0.859 |
| OOT Gini | 0.718 |
| OOT Brier (uncalibrated) | 0.0082 |
| OOT mean predicted vs observed | **1.63% vs 0.85% (1.92× over-prediction)** |
| Calibration design | **FAILED — original spec implied calibrating on OOT, which is leakage** |

The initial run produced strong discrimination but poor temporal calibration, exactly as ChatGPT's review predicted. Calibration must be fitted on a calibration split *carved from the training period*, never on OOT.

---

## 2. Diagnostic Test 1 — F6E ablation

Re-ran the full Stage 1 → Stage 2 → Stage 3 pipeline with **all F6E synthetic-bureau features excluded** from the candidate pool.

| Stage | Full F6E | No F6E | Δ |
|-------|---------:|-------:|--:|
| PD-eligible pool | 435 | 235 | -200 |
| Stage 1 survivors | 120 | 66 | -54 |
| Stage 2 (Lasso) | 64 | 34 | -30 |
| Final (VIF + p<0.05) | **22** | **7** | -15 |

### Final 7 features (no-F6E model)
`app_nom_job_code`, `act_age_log1p`, `mean_cars_by_job_code`, `app_nom_marital_status`, `median_income_by_job_code`, `app_nom_branch`, `app_nom_city`

### OOT performance comparison

| Metric | Full F6E | No F6E | Δ relative |
|--------|---------:|-------:|-----------:|
| AUC | 0.8591 | **0.8361** | -2.7% |
| Gini | 0.7181 | **0.6722** | -6.4% |
| KS | 0.5475 | 0.5395 | -1.5% |
| Brier (raw) | 0.00821 | **0.00821** | ~0% |

### Interpretation
F6E provides **a measurable but not transformative discrimination boost** (~6% Gini on OOT). The no-F6E model is simpler (7 vs 22 features), more interpretable, and uses real demographic features. **Both calibration profiles are equally bad uncalibrated** (mean predicted ~1.6% vs 0.85% base) — F6E is not the root cause of miscalibration; **vintage drift from the simulator is**.

---

## 3. Diagnostic Test 2 — Lasso stability (3 C × 3 seeds = 9 fits)

| C | Seed | Survivors | F6E % | F6D | Wall |
|--:|-----:|----------:|------:|----:|-----:|
| 0.02 | 42 | 45 | 40.0% | 0 | 14s |
| 0.02 | 101 | 46 | 39.1% | 0 | 15s |
| 0.02 | 202 | 39 | 28.2% | 0 | 24s |
| 0.05 | 42 | 64 | 51.6% | 0 | 18s |
| 0.05 | 101 | 59 | 45.8% | 0 | 12s |
| 0.05 | 202 | 54 | 40.7% | 0 | 29s |
| 0.10 | 42 | 72 | 55.6% | 0 | 33s |
| 0.10 | 101 | 66 | 50.0% | 0 | 29s |
| 0.10 | 202 | 64 | 46.9% | 0 | 77s |

| Stability metric | Value |
|------------------|------:|
| Jaccard min (worst pair) | 0.388 |
| Jaccard mean | 0.567 |
| F6E % range across configs | 28-56% |
| F6D survivors across all 9 configs | **0 every time** |
| Core features (≥8/9 runs) | 32 |
| Boundary features (5-7/9 runs) | 18 |

### Interpretation
Selection is **moderately stable** — Jaccard mean 0.57 indicates 57% feature overlap on average between configurations. Tighter regularization (C=0.02) selects fewer features and lowers F6E share (28-40%) vs looser regularization (C=0.10, F6E share 47-56%). **F6D rejection is rock-solid**: 0 random_* features survived in any of the 9 configurations. The 32 "core" features (selected in 8/9+ runs) include the demographic anchors (`app_nom_*`, `act_age_log1p`, `mean_*_by_*`) plus ~10 stable F6E synth_* features. **F6E dominance persists across all configurations, but the *amount* varies (28-56%) suggesting F6E is mostly carrying the marginal discrimination above the demographic baseline.**

---

## 4. Diagnostic Test 3 — Leak-free calibration ✅ FIXES THE PROBLEM

**Splits:**
- Model training: cohorts 202509-202610 (14 cohorts, 340,727 rows)
- Calibration: cohorts 202611-202612 (2 cohorts, 48,798 rows, ~454 events)
- OOT (untouched for calibration): cohorts 202701-202706 (144,789 rows)

### OOT performance (full-F6E LR, evaluated three ways)

| Metric | pd_raw | pd_platt | pd_iso |
|--------|-------:|---------:|-------:|
| AUC | 0.8591 | 0.8591 | 0.8573 |
| Gini | 0.7182 | 0.7182 | 0.7146 |
| KS | 0.5484 | 0.5484 | 0.5435 |
| Brier | 0.00821 | **0.00799** | **0.00800** |
| **ECE** | 0.00879 | **0.00107** | **0.00079** |
| Mean predicted | 1.73% | **0.92%** | **0.93%** |
| Base rate (truth) | 0.85% | 0.85% | 0.85% |

### Interpretation
**Both Platt scaling and isotonic regression preserve discrimination (AUC unchanged) AND fix the calibration drift.**
- ECE drops by **8-11×** (0.00879 → 0.00107 / 0.00079)
- Mean predicted drops from 1.73% (2× base rate, severely biased) to ~0.92% (within 9% of true 0.85% base)
- Platt is a single sigmoid → smoother, slightly worse fit
- Isotonic is non-parametric → tighter ECE but slight AUC cost (-0.002)

**This is the leak-free recipe to use going forward.** All future calibrated PD scores must come from this temporal split design. Calibrators saved to `diagnostics/calibrators.pkl`.

---

## 5. Diagnostic Test 4 — LightGBM baseline ⚠️ TRAINING ISSUE FOUND

| Property | Value |
|----------|------:|
| Features (PD-eligible pool, with F6E) | 435 |
| `scale_pos_weight` | 56.65 |
| Validation set | 15% of train_for_model (≈51K rows) |
| Early-stopping patience | 50 |
| **`best_iteration`** | **1** ⚠️ |

### OOT performance

| Metric | pd_lgb_raw | pd_lgb_platt | pd_lgb_iso |
|--------|-----------:|-------------:|-----------:|
| AUC | **0.8726** | 0.8726 | 0.8704 |
| Gini | 0.7452 | 0.7452 | 0.7408 |
| KS | 0.5961 | 0.5961 | 0.5961 |
| Brier | 0.0110 | 0.00810 | 0.00809 |
| ECE | 0.0449 | 0.00095 | 0.00084 |
| Mean predicted (raw) | **5.34%** ❌ | 0.94% | 0.93% |

### Top 20 features by gain
1. `job_code_x_income`, 2. `age_x_n_children`, 3. `act_age`, 4. `count_by_marital_status`, 5. `app_nom_gender`, 6. `mean_age_by_marital_status`, 7-15. various `synth_*` (income, secured_limit, highest_limit, etc.), 16. `synth_noise_normal_2`, **17. `random_normal_10` (F6D!)** 🚨, 18. `synth_avg_account_age`, 19-20. zero-importance fillers.

### Interpretation: ⚠️ This LightGBM run is NOT a usable benchmark.
1. **`best_iteration=1` means LightGBM is essentially a single-tree decision stump**. Validation AUC didn't improve past iteration 1 within 50-iteration patience. The reported AUC 0.873 reflects scale_pos_weight blowing up predictions (mean 5.34% vs base 0.85%) plus a single-tree split on the strongest demographic signal (`job_code_x_income`).
2. **`random_normal_10` (F6D pure noise) appears at rank 17 by gain** — clear sign of pipeline issue with this run. With proper training, F6D importance should be ≈ 0.
3. The post-Platt OOT metrics look superficially good because Platt rescales the saturated raw predictions, but **the underlying model is one tree**.

**LightGBM needs retraining** with: (a) larger validation slice or temporal val set, (b) `scale_pos_weight` reconsidered (the value 56.65 is too aggressive — maybe `is_unbalance=True` instead), (c) explicit max_depth/leaves tuning, (d) consider L1/L2 reg increases. Until then, **do not use this LightGBM as the primary model**.

Model saved to `artifacts/pd_model/lightgbm_model.pkl` for diagnostic reference; **flagged as not production-ready**.

---

## 6. Diagnostic Test 5 — Score-discrimination stress-test design (no execution)

`StressTestPlan` saved with target Ginis [0.60, 0.45, 0.30], logit-noise perturbation method, base-rate re-calibration. Sanity check on a 10K subsample hit target Gini 0.30 with σ=3.08 in 20 binary-search iterations (within 0.5% tolerance). Reference implementation `perturb_to_target_gini()` is ready in `src/calibration.py`. **Phase 3/4 will execute on the chosen calibrated PD score.**

---

## 7. Strategic narrative (per ChatGPT, save for thesis methodology chapter)

> "The raw synthetic model produces very high discrimination but poor temporal calibration. Therefore, the thesis evaluates profit cut-offs under calibrated and controlled-discrimination PD regimes rather than relying only on the raw simulator score."

Turning the artifact into methodology contribution: the simulator's vintage drift produces an unrealistic LR/LightGBM with AUC 0.86-0.87 on OOT. The thesis methodology will:
1. Use the **leak-free calibrated** PD as the ANCHOR PD
2. Generate stress-test PD variants at controlled Ginis (0.60, 0.45, 0.30) to mimic real-world discrimination levels
3. Compare profit cut-offs across all 4 regimes (raw + 3 stress-tested)
4. Frame the contribution as: *"Profit-driven cut-off selection is robust to discrimination level X but breaks down at Y"*

---

## 8. Phase 2A status — corrected

| Component | Status |
|-----------|:------:|
| Logistic / L1 pipeline | ✅ Done initial run |
| F6D negative control | ✅ Pass (0 in any config across 9+ Lasso runs) |
| Calibration design | ✅ **FIXED** (Test 3 — temporal split inside train, Platt + isotonic, ECE 0.001) |
| F6E legitimacy | ✅ **CHARACTERIZED** (Test 1 — provides ~6% Gini boost; non-F6E model is simpler and only slightly worse) |
| Lasso stability | ✅ **CHARACTERIZED** (Test 2 — moderate Jaccard 0.39-1.0, mean 0.57; F6D=0 always) |
| LightGBM baseline | ⚠️ **TRAINED BUT NOT USABLE** — best_iteration=1, F6D in top 20 by gain. Needs retuning. |
| Stress-test design | ✅ Done (Test 5 — design + sanity check passed) |
| Ready for Phase 2B/3 | **Conditional** — see recommendation below |

---

## 9. Recommendation: **(b) modified**

> **Use the F6E-excluded LR + Platt calibration as the MAIN INTERPRETABLE PD; the full-F6E LR + Platt as a ROBUSTNESS variant; LightGBM REQUIRES RETUNING before it can serve as a benchmark; stress-test regimes are designed (Test 5) and ready for Phase 3 execution.**

### Justification

1. **No-F6E LR is publishable**: 7 demographic features, OOT AUC 0.836, Gini 0.672. Loses ~6% Gini vs full-F6E but is interpretable for thesis defence and avoids dependency on synthetic bureau features whose generative process is contestable.
2. **Full-F6E LR is a robustness check**: same temporal calibration recipe, OOT AUC 0.859, Gini 0.718. Reports "with synthetic-bureau features added, discrimination improves modestly".
3. **LightGBM is currently broken** (best_iteration=1, F6D in top 20). Retune in a follow-up Phase 2A.5 task before it can be reported as the dual-track baseline.
4. **Stress-test design is in place** — Phase 3 can call `src.calibration.perturb_to_target_gini` on the chosen anchor PD without re-implementing.

### Hard constraints satisfied across all diagnostics
- No `score`/`scorem` simulator-tautological columns ever entered the modeling pool ✅
- No loan-term transforms in origination-PD pool ✅
- F6D pure-random rejection: 0 in 9/9 Lasso configurations ✅
- Calibration designed without OOT leakage ✅

---

## 10. Outstanding work (NOT executed in this round)

- [ ] **Retune LightGBM** so `best_iteration` >> 1 and F6D is ≈ 0 in importance
- [ ] **Phase 2B** — scorecard / WoE binning (deferred per instructions)
- [ ] **Phase 3** — profit cut-off analysis on the chosen calibrated PD (with stress-test variants)
- [ ] **Phase 4** — bootstrap CIs, reliability diagrams, lift charts

Per instructions: **stopping after diagnostics; no Phase 2B/3 execution; no simulator modifications.**

---

## 11. Wall time

| Step | Wall |
|------|-----:|
| Test 1 (F6E ablation, full pipeline) | ~3 min |
| Test 2 (9 Lasso fits) | ~4 min |
| Test 3 (refit + Platt + isotonic + scoring) | ~30s |
| Test 4 (LightGBM fit + scoring + Platt) | ~30s |
| Test 5 (sanity check on 10K) | <5s |
| Notebook total (incl. data loads) | ~9 min |

---

## 12. Files produced

```
artifacts/phase2_rerun_v2/diagnostics/
  test1_f6e_ablation.json        (1.2 KB)
  test2_lasso_stability.json     (3.4 KB)
  test3_calibration.json         (1.3 KB)
  test4_lightgbm.json            (3.6 KB)
  test5_stress_test_design.json  (0.8 KB)
  calibrators.pkl                (3.0 KB — Platt + isotonic for full-F6E LR)
artifacts/pd_model/
  lightgbm_model.pkl             (42 KB — saved but flagged not-production-ready)
notebooks/
  01a_phase2_diagnostics.ipynb   (51 KB, 26 cells, end-to-end execution PASS)
src/
  calibration.py                 (NEW — make_calibration_split, fit_platt,
                                  fit_isotonic, apply_calibrator,
                                  StressTestPlan, perturb_to_target_gini)
artifacts/phase2_rerun_v2/
  phase2_modeling_report.md      (this file)
```
