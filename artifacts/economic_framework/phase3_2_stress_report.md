# Phase 3.2 — Economic Realism Stress Test Report

**Date**: 2026-05-08
**Population**: 235,968 rows (24m + 36m only, primary PD = LightGBM tuned + Platt)
**Grid**: 576 cells = 4 PD-mult × 3 COF × 3 acq × 4 LGD × 4 APR strategies
**Wall time**: ~6 min total (notebook execute + analysis)

---

## 1. Headline finding

**The "approve-all" result from Phase 3.1B does NOT fully survive realistic stress.** Under the 576-cell stress grid:

| Category | Cells | Share |
|----------|------:|------:|
| approve-all (k* ≥ 99%) | 220 | 38.2% |
| **interior (50% ≤ k* < 99%)** | **356** | **61.8%** |
| reject-most (k* < 50%) | 0 | 0.0% |

The economics shift from "always approve everyone" (Phase 3.1B base) to **interior optimum on most realistic stresses** (62% of cells). However, **no scenario triggers reject-most** — even the adversarial stress (PD×5, COF=6%, acq=$500, LGD=0.85, flat 18% APR) lands at k*=84.73% (still approving most). This is a strong signal that the locked simulator's economic regime is structurally profitable but with material variation in optimal cut-off severity.

## 2. K* distribution across the 576-cell grid

| Pct | k* approve % |
|-----|------------:|
| min | **84.73%** (adverse stress anchor) |
| p10 | 94.41% |
| median | 98.24% |
| p90 | 100.00% |
| max | 100.00% |

The cutoff sits in `[84.73%, 100%]`. Even the worst-case combination keeps a 14.73 pp interior margin. Phase 4 bootstrap will quantify CIs around this band.

## 3. Profit-vs-Youden cutoff finding under stress

**The Phase 3.1B finding (profit cutoff more permissive than Youden) survives the entire stress grid.**

| Statistic | cutoff_gap_profit_minus_youden (pp) |
|-----------|-----------------------------------:|
| min | **+5.33** |
| median | +18.83 |
| max | +20.59 |
| mean | +18.23 |

**100.0% of cells (576/576)** have profit-driven cutoff MORE permissive than Youden's J. The minimum gap of +5.33 pp occurs in the adverse-stress anchor — even there, profit-driven approves 5+ pp more than Youden would. **The thesis hypothesis is robust to economic stress.**

## 4. Driver analysis

What moves k* the most? Mean k* by single-dimension parameter level (others varying):

| Parameter | Min level → Max level | Mean k* range | Spread |
|-----------|----------------------|---------------|-------:|
| **PD multiplier** | 1.0 → 5.0 | 99.81% → 96.27% | **3.54 pp** |
| **APR strategy** | tiered_uncapped → flat_18 | 98.59% → 96.27% | **2.32 pp** |
| LGD | 0.55 → 0.85 | 98.28% → 97.00% | 1.28 pp |
| acquisition_cost | $0 → $500 | 97.83% → 97.40% | 0.43 pp |
| cost_of_funds_annual | 0.00 → 0.06 | 97.83% → 97.40% | 0.43 pp |

**Two dominant drivers**: PD stress multiplier and APR strategy together account for ~6 pp of cutoff variation. LGD is third. Per-loan acquisition cost and cost of funds have small marginal impact at these grid levels.

### Frequency of each parameter level among the 356 INTERIOR cells

| pd_multiplier | count |
|--:|--:|
| 5.0 | 144 |
| 3.0 | 134 |
| 2.0 | 72 |
| 1.0 | 6 |

| APR strategy | count |
|---|--:|
| flat_18 | 110 |
| tiered_cap_24 | 89 |
| flat_24 | 89 |
| tiered_uncapped | 68 |

| LGD | count |
|---:|--:|
| 0.85 | 103 |
| 0.75 | 95 |
| 0.65 | 85 |
| 0.55 | 73 |

PD×5 generates 40% of interior cells. flat_18 (the most APR-conservative scenario) generates 31%. PD×1 (no PD stress) is essentially never interior — confirming that the simulator's calibrated PDs at face value are too low to make many loans unprofitable.

## 5. Three anchor scenarios

| Anchor | PD mult | COF | Acq | LGD | APR | Mean profit | Total profit | Share > 0 | k* | Gap vs Youden | Category |
|--------|--------:|----:|----:|----:|-----|------------:|-------------:|----------:|---:|--------------:|---------|
| optimistic_base | 1.0 | 0.00 | 0 | 0.55 | tiered_uncapped | $1,502.75 | $354.6M | 100.00% | 100.00% | +20.59 pp | approve_all |
| **realistic_central** | **2.0** | **0.03** | **$250** | **0.65** | **tiered_cap_24** | **$999.64** | **$235.9M** | **96.68%** | **99.25%** | **+19.85 pp** | **approve_all** (boundary) |
| adverse_stress | 5.0 | 0.06 | $500 | 0.85 | flat_18 | $300.59 | $70.9M | 67.26% | **84.73%** | +5.33 pp | **interior** |

### Anchor interpretation

- **optimistic_base** (Phase 3.1B baseline + LGD=0.55): every account profitable, optimal is approve-all. Confirms the original finding.
- **realistic_central**: shows ~33% lower mean profit and ~3% of accounts unprofitable, but k* still rounds to "approve-all" at 99.25%. **This is the cell most representative of mainstream lending economics**.
- **adverse_stress**: 67% of accounts are still profit-positive but ~33% have negative expected profit. k* drops to 84.73% — the bottom 15% by stressed PD becomes a drag. This is the "stressed" scenario.

## 6. Recommended central scenario for Phase 4 bootstrap

**`realistic_central`** (mult=2, COF=0.03, acq=$250, LGD=0.65, tiered_cap_24).

Rationale:
1. **Non-trivial costs**: includes funding cost (3% — typical bank funding spread) and acquisition cost ($250 — representative origination cost for unsecured consumer loans).
2. **PD calibration cushion**: PD×2 multiplier accounts for known calibration drift in the simulator (Phase 2A diagnostics found OOT mean predicted at ~110% of base rate at the headline calibration; doubling adds margin).
3. **Mainstream APR cap**: tiered_cap_24 keeps the locked-tier scheme but caps at 24% — matches typical real-world subprime APR ceilings (e.g., US state laws cap unsecured consumer at 18-25% in many jurisdictions).
4. **Industry-standard LGD**: 0.65 is the Phase 3.0 audit base assumption.
5. **Right at the boundary** (k*=99.25%, i.e., on the edge between approve-all and interior). This is methodologically valuable: bootstrap CIs will reveal whether the "approve-all" classification is statistically significant or random fluctuation around the boundary.

## 7. Phase 4 sensitivity matrix recommendation (NOT executed)

For Phase 4 bootstrap: instead of bootstrapping all 576 cells, focus on the 3 anchors + a small ablation grid:

- All 3 anchors (optimistic, realistic_central, adverse) — 1000-resample bootstrap each
- Realistic anchor with one parameter perturbed at a time — single-driver sensitivity (5 single-perturbation cells)
- Total: 8 bootstrap targets × 1000 resamples ≈ manageable compute

## 8. Files produced

```
artifacts/economic_framework/
  economic_stress_grid.parquet     (39 KB — 576 cells × 17 cols)
  stress_cutoff_results.csv        (75 KB — compact view)
  anchor_scenarios.json            (2.2 KB — 3 anchors)
  phase3_2_stress_report.md        (this file)
notebooks/
  03_economic_stress_test.ipynb    (executed clean)
src/
  economics.py                     (extended with cost_of_funds_annual,
                                    acquisition_cost, apr_tier_lookup_capped,
                                    apr_tier_lookup_capped_vec)
```

## 9. Wall time

| Step | Wall |
|------|-----:|
| Load eco-pop parquet | ~3s |
| Compute Youden per PD model on OOT | ~1s |
| 576-cell grid (batch_lifetime_economics + cutoff per cell) | ~290s |
| Classification + drivers + saves | ~5s |
| **Total** | **~5 min** |

## 10. Stopping point

Per spec: **"Stop after Phase 3.2 report. Do not proceed to Phase 4 bootstrap."**

### Awaiting your go for Phase 4

Phase 4 bootstrap targets:
- 3 anchor scenarios + small ablation (8 cells × 1000 resamples)
- CIs on: total Expected_Profit, k*, cutoff_pd_star, cutoff_gap_profit_minus_youden
- Compute on the same 235,968-row population
- Results inform: thesis confidence statements about the profit-vs-Youden hypothesis
