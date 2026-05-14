# Writing Readiness Report

**Date**: 2026-05-09
**Phase**: 5 — Pre-writing documentation consolidation
**Verdict**: ✅ **READY for thesis writing.** No critical gaps; one
methodology caveat to surface in Limitations.

---

## 1. What is ready

### Empirical evidence (complete)

- **Phase 1.5 Feature Factory** — 2,236 columns built with 14-field governance per column.
- **Phase 2 PD modeling** — 4 PD models trained, calibrated, and benchmarked: LightGBM tuned (PRIMARY), LR full-F6E, LR no-F6E, Scorecard no-F6E. Plus 3 stressed Gini variants.
- **Phase 3 Economics** — Locked formulas in `src/economics.py` validated by 9/9 unit tests + 5-account validation. Base run on 235,968 economics-eligible accounts.
- **Phase 3.2 Stress** — 576-cell stress grid (PD multiplier × COF × acquisition × LGD × APR) with full classification.
- **Phase 4.1 Bootstrap** — 1,000 stratified resamples × 4 anchor scenarios.
- **Phase 4.2 PD-quality + op_cost stress** — 64 additional stress cells (PARTS A, B, C).
- **Phase 4.3 Calibration verification** — 7 PD sources benchmarked.
- **Phase 4.4 Visualization** — 9 publication figures saved (PDF + PNG).

### Documentation (complete, this Phase 5)

- `thesis_evidence_map.md` — every claim mapped to artifact + figure + numerical value + caveat
- `thesis_methodology_lock.md` — every locked decision in one place + 10-item "Do Not Claim" section
- `thesis_results_summary.md` — every numerical result consolidated into thesis-ready tables
- `thesis_limitations.md` — 10 limitations with phrasing + 7 future-work directions
- `artifact_inventory.md` — every file path + size + purpose + chapter mapping
- `writing_readiness_report.md` — this file

### Source code (production-quality)

- `src/economics.py` — 8 locked functions + 2 batch helpers
- `src/calibration.py` — temporal split + Platt + isotonic + perturb_to_target_gini
- `src/governance.py` — PD-eligibility filter + score/loan-term validators
- `src/modeling.py` — Stage 1, Lasso (single-fit + CV), statsmodels logit, VIF
- `src/evaluation.py` — Gini, KS, Brier, calibration metrics, PSI
- `src/scorecard.py` — OptBinning + WoE + scorecard table builder
- `tests/test_economics.py` — 9 unit tests, all PASS

### Notebooks (10 reproducible)

- 01–01c (Phase 2 + scorecard)
- 02 (Phase 3.1B)
- 03 (Phase 3.2 stress)
- 04 (Phase 4.1 bootstrap)
- 05 (Phase 4.2 PD-quality stress)
- 06 (Phase 4.3 calibration)
- 07 (Phase 4.4 visualization)

All 10 notebooks executed cleanly end-to-end on the saved artifacts.

## 2. What remains optional

### Optional — could enrich but not required

1. **Scorecard full-F6E row-level PD** — would add a 5th PD model panel to Fig 6 and the calibration_summary table. ~30 minutes of work to refit + Platt + score.
2. **Stress test execution** (`perturb_to_target_gini` × profit cut-off bootstrap) — would produce Phase 4.5 stress-test report on the calibrated PD. The infrastructure is in place; execution would take ~30 minutes.
3. **Empirical LGD** — derivable from `transactions.csv`. ~10 minutes compute. Marked as Future Work F1.
4. **Notebook auto-export to .py for the missing exports** — only `01_phase2_feature_selection`, `01a_phase2_diagnostics`, `01b_phase2_lightgbm_retune`, `01c_scorecard`, `03_economic_stress_test`, `06_calibration_verification`, `07_visualization` are missing exported `.py` versions; the others have them. ~5 minutes to batch.

None of these block thesis writing.

## 3. Artifact gaps

No critical gaps. Documented in `artifact_inventory.md` Section F:

| Item | Why missing | Workaround |
|------|-------------|------------|
| Scorecard full-F6E row-level PD | Phase 2B optional task | Use "4 PD models + 3 stressed" framing |
| Empirical LGD per default | Out of scope | Future Work F1 |
| Multi-seed bootstrap | Single-seed only | Future Work F6 |
| Real-data replication | Out of thesis scope | Future Work F2/F7 |

## 4. Inconsistencies / caveats found in Phase 5 review

1. **Phase 4.1 OOT row-count typo**: the original Phase 4.1 report said "144,789 OOT rows" but the actual bootstrap used 64,027 rows (`split_new == 'oot'` filtered to 24m + 36m). Already corrected in `phase4_2_report.md` CHECK 0 and in `thesis_results_summary.md` Section 1. **Use 64,027 throughout the thesis.**
2. **LightGBM mean-prediction under-prediction (~50%)** on the eco-OOT subset. Documented in:
   - `thesis_methodology_lock.md` Section 4 (calibration design)
   - `thesis_limitations.md` §6
   - `thesis_results_summary.md` Section 11 with ⚠️ marker
   - Reflected in Fig 6 reliability diagrams (LightGBM curve sits below diagonal)
3. **`final_run_800d.py` script reflects pre-launch placeholder spec, not runtime data**. The actual 800/day run completed at 12.8h wall, 1,460,800 originations (vs ~1,461,600 in the spec). Within rounding; thesis Methodology should cite the runtime numbers.

All inconsistencies are documented and traceable.

## 5. Recommended chapter-writing order

| Order | Chapter | Lead artifact | Estimated writing time |
|------:|---------|---------------|------------------------|
| 1 | **Methodology** | `thesis_methodology_lock.md` + `thesis_results_summary.md` Sections 1-3, 11 | ~1-2 days |
| 2 | **Results — Empirical evidence** | `thesis_results_summary.md` Sections 4-12 + Figs 1, 4, 5 | ~2 days |
| 3 | **Results — Stress robustness** | `thesis_results_summary.md` Sections 5, 8-10 + Figs 2, 3, 8 | ~1 day |
| 4 | **Discussion — Drivers** | Fig 9 + Phase 3.2 driver narrative | ~0.5 day |
| 5 | **Discussion — Strategic narrative** | `thesis_results_summary.md` Section 14 | ~0.5 day |
| 6 | **Limitations** | `thesis_limitations.md` (full) | ~0.5 day |
| 7 | **Future Work** | `thesis_limitations.md` Future Work F1-F7 | ~0.5 day |
| 8 | **Introduction + Literature Review** | (write last for coherence) | ~2 days |
| 9 | **Abstract + Conclusion** | (write last) | ~0.5 day |

Total estimated writing time: **~8-10 days** for a single author.

**Recommended drafting order**: Methodology → Results → Discussion → Limitations → Future Work → Intro/Lit Review → Abstract/Conclusion. This matches the empirical chain of decisions and lets the introduction frame what was actually achieved.

## 6. Pre-flight checklist before writing the first paragraph

- [x] Population numbers locked (534,314 / 235,968 / 64,027)
- [x] PD model named and locked (LightGBM tuned + Platt = PRIMARY)
- [x] Locked formulas documented (`phase3_formula_lock.md`)
- [x] All 9 figures saved at 300 DPI in PDF + PNG
- [x] All 64 stress cells with profit_uplift > 0 — confirmed
- [x] All 4,000 (anchor × bootstrap) combinations with profit_uplift > 0 — confirmed
- [x] Phrasing rules documented ("across N resamples", not "true probability")
- [x] "Do Not Claim" list documented (10 items)
- [x] Limitations list documented (10 items)
- [x] Future Work list documented (7 items)
- [x] All 10 notebooks executable end-to-end on saved artifacts
- [x] All `src/` modules unit-tested (where applicable)
- [x] Artifact inventory complete with sizes and chapter mapping

## 7. Final readiness assessment

**READY for thesis writing.**

All empirical evidence is in place. All documentation is consolidated. All
limitations are honest and explicit. The phrasing discipline ("across N
bootstrap resamples", "within tested scenario space") is locked into the
methodology document and the evidence map. The 9 figures are
publication-ready. The artifact inventory is complete.

The only methodology caveat to surface honestly is the LightGBM
under-prediction on the eco-OOT subset (Limitation §6), which is documented
across 4 places and visible in Fig 6.

**Recommended next action**: Begin drafting the Methodology chapter using
`thesis_methodology_lock.md` as the source of truth.
