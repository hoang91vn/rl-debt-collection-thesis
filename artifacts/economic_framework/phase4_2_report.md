# Phase 4.2 — PD-Quality Stress + op_cost Robustness

**Date**: 2026-05-08
**Population**: OOT economics-eligible subset (24m + 36m only)
**PD source**: LightGBM tuned + Platt-calibrated, raw OOT Gini ≈ 0.804
**Wall time**: ~30 s (mostly the 4 perturb_to_target_gini binary searches)

---

## CHECK 0 — Phase 4.1 bootstrap population correction

The Phase 4.1 report stated "OOT rows: 144,789". This was a transcription
error — the actual code was `eco[eco["split_new"] == "oot"]` which evaluated
to **64,027 rows** (24m: 36,775; 36m: 27,252). The bootstrap results
themselves were computed on the correct 64,027 rows; only the prose label
was wrong.

**Corrected label**: Phase 4.1 was an **OOT validation bootstrap on 64,027
rows**, not portfolio-level. The split composition is exactly the cohorts
202701-202706, with Phase 3.1B's 12-month exclusion already applied at the
parquet level.

The same 64,027-row OOT subset is used for Phase 4.2 below — keeping
methodology consistent across the bootstrap and stress runs.

### Reporting language correction

Per user instruction, future references to bootstrap probabilities use the
phrasing: "Across 4,000 bootstrap resamples, the result held in 100% of
resamples." The earlier "P(profit cutoff > Youden) = 1.0000" should be read
as the same thing — empirical resample frequency, not a true probability.

---

## PART A — PD-quality stress (16 cells: 4 PD variants × 4 anchors)

`perturb_to_target_gini` was applied to the LightGBM Platt-calibrated PD on
the 64,027-row OOT subset, with re-calibration to the OOT base rate so the
comparison isolates *discrimination* shift, not *level* shift.

### PD variants generated

| Variant | Achieved Gini | Sigma | Mean PD (re-calibrated to base) |
|---------|--------------:|------:|-------------------------------:|
| raw | 0.8044 | 0.0 | 1.92% |
| gini_60 | 0.6030 | bin-search | 1.92% |
| gini_45 | 0.4456 | bin-search | 1.92% |
| gini_30 | 0.3027 | bin-search | 1.92% |

(Each PD variant has the same population-level mean as the OOT base rate,
so the only thing changing is the relative ranking of accounts.)

### Cutoff results (16 cells)

| PD variant | Anchor | k* approve % | Youden % | gap pp | profit_uplift | uplift % | category |
|-----------|--------|-------------:|---------:|-------:|--------------:|---------:|---------|
| raw | optimistic_base | 100.00 | 79.59 | +20.41 | $30.7M | 47.1% | approve_all |
| raw | realistic_central_boundary | 99.26 | 79.59 | +19.66 | $17.8M | 38.4% | approve_all |
| raw | moderate_interior | 96.33 | 79.59 | +16.74 | $8.1M | 13.5% | interior |
| raw | adverse_stress | 84.90 | 79.59 | +5.31 | $0.5M | 1.5% | interior |
| gini_60 | optimistic_base | 99.27 | 71.35 | +27.92 | $38.2M | 69.2% | approve_all |
| gini_60 | realistic_central_boundary | 96.15 | 71.35 | +24.80 | $22.2M | 64.2% | interior |
| gini_60 | moderate_interior | 92.68 | 71.35 | +21.33 | $11.1M | 19.5% | interior |
| gini_60 | adverse_stress | 82.04 | 71.35 | +10.69 | $1.6M | 5.5% | interior |
| gini_45 | optimistic_base | 98.76 | 63.42 | +35.35 | $37.2M | 76.9% | interior |
| gini_45 | realistic_central_boundary | 96.22 | 63.42 | +32.80 | $23.2M | 89.1% | interior |
| gini_45 | moderate_interior | 93.96 | 63.42 | +30.54 | $20.5M | 39.7% | interior |
| gini_45 | adverse_stress | 87.89 | 63.42 | +24.47 | $7.9M | 27.4% | interior |
| gini_30 | optimistic_base | 96.42 | 59.12 | +37.30 | $39.4M | 86.6% | interior |
| gini_30 | realistic_central_boundary | 96.00 | 59.12 | +36.88 | $20.7M | 76.4% | interior |
| gini_30 | moderate_interior | 94.41 | 59.12 | +35.29 | $26.2M | 54.4% | interior |
| gini_30 | adverse_stress | 90.72 | 59.12 | +31.60 | $12.7M | 46.6% | interior |

### Findings

1. **Profit cutoff > Youden in 16/16 (100%) cells** under PD-quality stress.
2. **Profit uplift > 0 in 16/16 cells** — the dollar improvement of profit-driven over Youden-driven cutoffs is strictly positive at every PD-quality level.
3. **The cutoff gap GROWS as Gini falls.** Mean gap by PD variant:
   - raw (Gini 0.80): +15.5 pp
   - gini_60: +21.2 pp
   - gini_45: +30.8 pp
   - gini_30: +35.7 pp

   **Mechanism**: as PD discrimination weakens, Youden's J cutoff becomes more conservative (rejects more) because TPR-FPR plateaus quickly. Profit-optimal cutoff stays high because most accounts remain profitable on average. The gap WIDENS — making the profit-driven approach RELATIVELY MORE valuable when the underlying PD model is worse.

   This is a **stronger thesis result than Phase 4.1 bootstrap** — the value of profit-driven cutoffs is *largest* exactly where credit risk models are weakest.

---

## PART B — op_cost robustness (12 cells: 4 op_cost levels × 3 anchors)

| Anchor | op_cost | k* % | gap pp | mean profit | total profit | share>0 | category |
|--------|--------:|-----:|-------:|------------:|-------------:|--------:|---------|
| realistic_central_boundary | 0.00 | 99.26 | +19.66 | $998 | $63.9M | 96.8% | approve_all |
| realistic_central_boundary | 0.01 | 98.94 | +19.35 | $819 | $52.4M | 93.1% | interior |
| realistic_central_boundary | 0.02 | 98.74 | +19.15 | $640 | $41.0M | 87.4% | interior |
| realistic_central_boundary | 0.04 | 97.74 | +18.15 | $283 | $18.1M | 52.8% | interior |
| moderate_interior | 0.00 | 96.33 | +16.74 | $1,061 | $68.0M | 95.6% | interior |
| moderate_interior | 0.01 | 95.72 | +16.13 | $885 | $56.6M | 94.6% | interior |
| moderate_interior | 0.02 | 94.88 | +15.28 | $708 | $45.3M | 92.8% | interior |
| moderate_interior | 0.04 | 90.97 | +11.38 | $355 | $22.7M | 80.5% | interior |
| adverse_stress | 0.00 | 84.90 | +5.31 | $305 | $19.5M | 67.3% | interior |
| adverse_stress | 0.01 | 81.28 | +1.69 | $132 | $8.4M | 59.2% | interior |
| adverse_stress | 0.02 | 74.72 | -4.87 | -$41 | -$2.6M | 48.2% | interior |
| **adverse_stress** | **0.04** | **0.31** | **-79.28** | **-$387** | **-$24.8M** | **19.3%** | **REJECT-MOST** ⚠️ |

### Op_cost tipping points

| Anchor | First op where k* < 99% | First op where k* < 50% |
|--------|-----------------------|-----------------------|
| realistic_central_boundary | **0.01** | never (in tested range) |
| moderate_interior | already 0.00 | never (in tested range) |
| adverse_stress | already 0.00 | **0.04** |

### Findings (PART B)

1. **op_cost is a powerful lever**: even 1% annual op_cost shifts realistic_central_boundary from approve_all (k*=99.25%) to interior (k*=98.94%).
2. **adverse_stress + op_cost=4% reaches REJECT-MOST**: k* drops to 0.31% (essentially "approve nobody"). This is the only reject-most cell discovered across any analysis to date.
3. **In adverse + op_cost ≥ 2%, "profit cutoff > Youden" FAILS at the approval-rate level** — the gap goes negative (-4.87 to -79.28 pp). Profit-optimal correctly rejects more accounts than Youden when most accounts are loss-making.
4. **BUT**: profit_uplift > 0 in 12/12 cells. Even when profit-cutoff is LESS permissive than Youden, it generates HIGHER total profit because Youden naively approves loss-making accounts.

This refines the thesis: the *more accurate* statement is **"profit-driven cutoff produces strictly greater total profit than Youden's J cutoff"**, NOT "profit-driven cutoff is more permissive". In severe stress, profit-optimal becomes MORE conservative AND still wins.

---

## PART C — Combined mini-grid (36 cells: 4 Gini × 3 op_cost × 3 anchors)

Full results in `artifacts/economic_framework/phase4_2_combined_grid.csv`.

### Headline summary

| Metric | Count / 36 |
|--------|-----------:|
| approve_all | 1 |
| interior | 31 |
| **reject_most** | **4** |
| profit_uplift > 0 (all cells) | **36 / 36** ✅ |
| cutoff_gap > 0 (profit MORE permissive) | 31 / 36 |
| cutoff_gap < 0 (profit LESS permissive) | 5 / 36 |

### The 4 reject_most cells

All 4 are **adverse_stress + op_cost=0.04** (regardless of PD variant):

| PD variant | Gini | k* % | gap pp | profit_uplift |
|-----------|-----:|-----:|-------:|--------------:|
| raw | 0.804 | 0.31 | -79.28 | +$6.27M |
| gini_60 | 0.603 | 0.08 | -71.27 | +$3.08M |
| gini_45 | 0.446 | 0.12 | -63.29 | +$0.76M |
| gini_30 | 0.303 | 0.14 | -58.98 | +$0.50M |

In all 4 reject_most cells, profit-driven uplift is STILL POSITIVE — profit-optimal correctly rejects, while Youden incurs net losses by approving.

### The 5 cells where profit_cutoff < Youden

| PD variant | op_cost | Anchor | k* % | gap pp | profit_uplift |
|-----------|--------:|--------|-----:|-------:|--------------:|
| raw | 0.02 | adverse_stress | 74.72 | -4.87 | +$0.19M |
| raw | 0.04 | adverse_stress | 0.31 | -79.28 | +$6.27M |
| gini_60 | 0.04 | adverse_stress | 0.08 | -71.27 | +$3.08M |
| gini_45 | 0.04 | adverse_stress | 0.12 | -63.29 | +$0.76M |
| gini_30 | 0.04 | adverse_stress | 0.14 | -58.98 | +$0.50M |

All 5 are extreme-adverse cells. The gap goes negative when the optimum collapses to "reject most", which happens only under the worst stress combinations. **The profit_uplift sign is positive in all 5** — Youden loses real money in these cells.

---

## Key thesis findings

1. **Profit-driven uplift is universally positive** (uplift > 0 in 64/64 = 100% of cells across PART A + B + C). This is the cleanest formulation of the thesis hypothesis: switching from Youden's J to profit-optimal cutoffs always (in this synthetic regime) generates more dollars.

2. **The "more permissive" framing has limits.** It holds in 47/64 (73%) of stress cells, fails in adverse + high-op-cost cells where profit-optimal correctly REJECTS while Youden naively APPROVES loss-makers. The richer thesis claim is "profit-optimal beats Youden in $ terms regardless of which direction it leans".

3. **Lower PD discrimination → larger profit-driven advantage.** When Gini falls from 0.80 to 0.30, the cutoff_gap grows from +15.5 to +35.7 pp (mean across anchors). The value of profit-driven cutoffs is largest exactly where credit risk models are weakest. This is a strong defensive narrative for the thesis.

4. **Op_cost is the dominant lever for triggering reject_most.** No PD variant alone produces reject_most. Only adverse_stress + op_cost ≥ 4% breaks into reject_most territory.

---

## Recommended final thesis scenario set

For the thesis main results (Phase 5 / writing):

| Scenario | Purpose | k* | Profit uplift % |
|----------|---------|---:|----------------:|
| **optimistic_base** | optimistic anchor; pure-form result | 100% | 47% |
| **realistic_central_boundary** | mainstream lender economics; base case for thesis | 99.25% | 38% |
| **moderate_interior** (NEW from 4.1) | clean interior optimum; key thesis case | 96.3% | 13.5% |
| **adverse_stress** | downside scenario; uplift small but positive | 84.9% | 1.5% |

Add **two PD-quality variants** for the discrimination-stress chapter:
- `realistic_central_boundary` × `gini_45` — gap +32.8 pp, uplift 89% (showcase the "weaker model → larger profit-driven advantage" finding)
- `adverse_stress` × `gini_30` — gap +31.6 pp, uplift 47% (combined stress, profit still wins big)

Add **one op_cost stress** for the cost-stress chapter:
- `adverse_stress` × `op_cost=0.04` — the only reject_most cell, illustrates that profit-optimal correctly REJECTS when warranted

## Whether Phase 4.3 visualization can proceed

**YES** — all upstream stress evidence is now in place:
- Phase 4.1 bootstrap (CIs on 4 anchors)
- Phase 4.2 PD-quality (4 Gini levels × 4 anchors)
- Phase 4.2 op_cost (4 op_cost × 3 anchors)
- Phase 4.2 combined mini-grid (36 cells)

Visualization should focus on:
1. Profit curves (cumulative profit vs accepted percentile) per anchor
2. Profit-uplift density plots from bootstrap
3. Gini-vs-cutoff_gap surface (PART A)
4. op_cost-vs-k* curves per anchor (PART B)
5. Reliability diagrams (Platt-calibrated PD vs observed defaults)
6. Side-by-side bar chart: profit at profit-optimal vs profit at Youden

---

## Files produced

```
artifacts/pd_quality_stress/
  pd_variants.parquet              (1.2 MB — 64K rows × 6 cols)
  cutoffs_by_gini.csv              (16 rows × 12 cols)
artifacts/op_cost_robustness/
  cutoffs_by_op_cost.csv           (12 rows × 12 cols)
artifacts/economic_framework/
  phase4_2_combined_grid.csv       (36 rows × 14 cols)
  phase4_2_report.md               (this file)
  exported_pd_quality_stress_script.py  (12.9 KB — auto-exported)
notebooks/
  05_pd_quality_opcost_stress.ipynb
```

## Wall time

| Step | Wall |
|------|-----:|
| Load OOT subset | <1s |
| 3× perturb_to_target_gini | ~5s |
| PART A (16 cells) | ~3s |
| PART B (12 cells) | ~2s |
| PART C (36 cells) | ~5s |
| Save artifacts | ~2s |
| **Total** | **~20s** |

## Stopping point

Per spec: **"Stop after Phase 4.2 report. Do not proceed to visualization. Do not modify simulator."**

Awaiting your go for Phase 4.3 visualization.
