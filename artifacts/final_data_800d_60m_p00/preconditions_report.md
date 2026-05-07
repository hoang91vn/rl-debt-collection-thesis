# Preconditions Report — Phase 1.5 Readiness

**Run**: `final_data_800d_60m_p00`
**Date**: 2026-05-07
**Stage**: 1B Preconditions (after data freeze)

---

## Precondition 1 — Cohort 202706 Maturity Verification

### Question
Is cohort 202706 sufficiently mature for the 12-month forward target (`default_flag_12m`), or is its low DR a residual censoring artifact?

### Methodology
`default_flag_12m` semantics (from `build_wide_abt.py` line 397): target window = offsets 12-23 from `fin_period`. Sim ran from 202405 to **202905** (61 unique periods observed).

For cohort 202706:
- Origination: month 202706
- Target window: months 202806-202905 (offsets 12-23)
- Sim end: 202905 → target window **fully observable** ✓

For each OOT cohort, computed cumulative writeoff rate at observation ages +12, +14, +16, +18, +20, +22, +23 months. The +23m comparison is the apples-to-apples measure (matched at maximum observable age for 202706).

### Results: Cumulative Writeoff DR at Matched Observation Ages

| Cohort | n_orig | +12m | +14m | +16m | +18m | +20m | +22m | +23m |
|-------:|-------:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| 202701 | 24,800 | 0.000% | 0.020% | 0.129% | 0.254% | 0.480% | 0.738% | 0.875% |
| 202702 | 22,400 | 0.000% | 0.040% | 0.147% | 0.313% | 0.464% | 0.759% | 0.946% |
| 202703 | 24,800 | 0.004% | 0.016% | 0.109% | 0.258% | 0.448% | 0.665% | 0.798% |
| 202704 | 24,000 | 0.017% | 0.058% | 0.125% | 0.229% | 0.483% | 0.738% | 0.925% |
| 202705 | 24,800 | 0.020% | 0.044% | 0.105% | 0.242% | 0.432% | 0.657% | 0.786% |
| **202706** | **24,000** | **0.004%** | **0.038%** | **0.096%** | **0.238%** | **0.404%** | **0.667%** | **0.808%** |

### Finding
At every matched observation age, **202706 falls within the range observed for 202701-202705**. At +23m (the maximum observable for 202706), all six OOT cohorts cluster between 0.79% and 0.95%, with 202706 (0.81%) sitting at the median.

**Conclusion: 202706's apparent low DR is consistent vintage drift, NOT residual censoring.** The cohort is sufficiently mature for the 12-month forward target.

### Row Count Under Each Option

| Option | Rule | Post-filter rows | H1 (≥500K) |
|--------|------|-----------------:|:----------:|
| **A** | Include all 22 cohorts (202509-202706) | **534,400** | ✅ PASS |
| B | Exclude 202706 only | 510,400 | ✅ PASS |
| C | Exclude 202705-202706 | 485,600 | ❌ FAIL |

### Recommendation
**Option A — Include all 22 cohorts (534,400 rows).**

Rationale:
1. Maturity-matched analysis confirms 202706 is fully observable for the target window.
2. DR at +23m (0.81%) is statistically indistinguishable from peers (range 0.79-0.95%).
3. Excluding 202706 sacrifices 24,000 rows + 194 OOT default events with no methodological benefit.
4. Both A and B pass H1, but A is the principled choice given the maturity evidence.

**No `cohort_eligibility_config.yaml` is needed** — Phase 1.5 will use all rows present in the Phase 2 wide ABT.

---

## Precondition 2 — Train/OOT Distribution-Shift Quantification (Level 1)

### Headline Counts

| Slice | Rows | `default_flag_12m=1` | DR (exact) |
|-------|-----:|---------------------:|-----------:|
| Train (202509-202612) | 389,600 | 6,436 | 1.652% |
| OOT (202701-202706) | 144,800 | 1,238 | 0.855% |

### Cohort DR Trend (in `default_flag_12m` semantics)

Monotonic decay from 2.88% (202509) to 0.81% (202706), no sharp discontinuities.
Full table: `cohort_default_rates.csv` and `final_run_validation_report.md`.

### Application Numeric Features — Train vs OOT

| Feature | Train mean | OOT mean | Train median | OOT median | SMD | PSI |
|---------|-----------:|---------:|-------------:|-----------:|-----:|-----:|
| app_income | 2,389.99 | 2,381.58 | 1,605.0 | 1,596.0 | -0.0038 | 0.000070 |
| app_loan_amount | 4,855.51 | 4,862.78 | 3,816.0 | 3,816.0 | +0.0021 | 0.000041 |
| app_n_installments | 19.57 | 19.57 | 12.0 | 12.0 | -0.0000 | 0.000004 |
| app_number_of_children | 0.43 | 0.43 | 0.0 | 0.0 | -0.0025 | 0.000054 |
| app_spendings | 1,050.28 | 1,046.59 | 688.0 | 684.0 | -0.0036 | 0.000106 |
| act_age | 58.06 | 58.06 | 58.0 | 58.0 | -0.0002 | 0.000073 |

### Application Categorical Features — Train vs OOT (PSI per feature)

| Feature | PSI |
|---------|----:|
| app_nom_branch | 0.000009 |
| app_nom_gender | 0.000005 |
| app_nom_job_code | 0.000039 |
| app_nom_marital_status | 0.000012 |
| app_nom_home_status | 0.000011 |
| app_nom_cars | 0.000001 |

Top-category proportion shifts: all < 0.3 percentage points.

### Summary

| Metric | Value | Interpretation |
|--------|------:|----------------|
| Max PSI (any feature) | 0.000106 | No shift (threshold 0.10) |
| Max \|SMD\| numeric | 0.0038 | Negligible (threshold 0.10) |

### Finding
**Application/loan feature distributions are statistically identical between train and OOT.** Customer profiles, loan terms, and demographic distributions are stable across the time split. The 2× train/OOT DR gap (1.65% → 0.85%) is **driven entirely by the simulator's vintage drift** (quota-based transition mechanism producing lower DR as the active pool grows), not by changing customer composition.

### Phase 4 Calibration-Risk Items

Items deferred to Phase 4 (after PD model rerun on the new ABT):

1. **Train→OOT calibration drift**: Train DR (1.65%) is ~1.93× OOT DR (0.85%). PD models trained on the train split will systematically over-predict OOT defaults by approximately this factor. Recommend isotonic regression or Platt scaling on a held-out calibration set before Phase 4 deployment metrics.
2. **Observed:Expected ratio per decile**: Compute after PD scores exist on the new data.
3. **Brier score, ECE, reliability diagram**: Compute after PD scores exist.
4. **Hosmer-Lemeshow test**: Compute after PD scores exist.
5. **Vintage-stratified calibration**: Given the within-train DR decay (2.88% → 0.96%), check whether early-train cohorts dominate calibration loss.

These cannot be computed now — no PD predictions exist on the new data.

---

## Precondition 3 — Phase 1.5 Prompt and Path Update

### Status

- v4 prompt file (`phase1_5_prompt_v4_final.md`) does not exist in worktree (likely external/in-conversation).
- New v5 prompt created: `phase1_5_prompt_v5_final.md` at repository root.
- v5 incorporates: new data location, Option A cohort decision, actual production row counts.

### Path Updates Required Before Phase 1.5 Run

**`scripts/phase1_5_feature_factory.py` currently has** (line 67):
```python
INPUT_CSV = Path("artifacts/thesis_wide_abt_12m_500c_clean/thesis_wide_abt.csv")
```

**Required changes (one-line edit, deferred until after `build_wide_abt.py` runs)**:
```python
INPUT_CSV = Path("artifacts/thesis_wide_abt_800d_60m_p00/thesis_wide_abt.csv")
```

**`scripts/build_wide_abt.py` currently has** (line 28-29):
```python
DEFAULT_DATA_DIR   = Path("examples/thesis_baseline/runs/thesis_baseline")
DEFAULT_OUTPUT_DIR = Path("artifacts/thesis_wide_abt_12m_500c_clean")
```

**Will be invoked with CLI overrides** (no source edit needed):
```bash
uv run python scripts/build_wide_abt.py \
    --data-dir artifacts/final_data_800d_60m_p00 \
    --output-dir artifacts/thesis_wide_abt_800d_60m_p00
```

(Or wrapper script calling the same.) The `DEFAULT_*` constants stay as historical pointers per the user's "do not modify simulator/build for cosmetic reasons" guideline.

### Cohort Eligibility Rule

Per Precondition 1 recommendation (Option A): **no cohort exclusion needed.** Phase 1.5 reads all rows produced by `build_wide_abt.py`, which already applies `MIN_FIN_PERIOD=202509` and `OOT_FIN_PERIOD_MAX=202706`.

### Step A Schema Assumptions

The Phase 1.5 feature factory assumes the input wide ABT has:
- ~534,400 rows (split: 389,600 train + 144,800 OOT)
- 192 columns (192 cols structure unchanged from 333K baseline)
- Target: `default_flag_12m` ∈ {0, 1}, no NaN
- Splits: `split` ∈ {"train", "oot"}
- Cohort range: `fin_period` ∈ [202509, 202706]
- Train DR: 1.65%, OOT DR: 0.85%

Step A's pre-generation gate must verify these row/column/DR ranges before generating ~2000 features.

---

## Final Analytical Population

| Property | Value |
|----------|------:|
| Total rows in Phase 2 wide ABT | **534,400** |
| Train rows | 389,600 |
| OOT rows | 144,800 |
| Train events (`default_flag_12m=1`) | 6,436 |
| OOT events (`default_flag_12m=1`) | 1,238 |
| Train DR | 1.652% |
| OOT DR | 0.855% |
| Cohorts included | 22 (202509-202706) |
| Cohorts excluded | None (Option A) |

**H1 hard requirement (≥ 500,000 rows): PASS.**

---

## Files Produced (in this directory)

- `validation_results.json` — exact metrics
- `cohort_default_rates.csv` — cohort table source
- `oot_maturity_comparison.csv` — Precondition 1 maturity-matched table
- `app_numeric_distribution_shift.csv` — Precondition 2 numeric features
- `app_categorical_psi.csv` — Precondition 2 categorical PSI summary
- `app_categorical_top_distributions.json` — Precondition 2 categorical top-N
- `app_distribution_shift_summary.json` — Precondition 2 summary
- `final_run_validation_report.md` — full validation report
- `preconditions_report.md` — this file

## Files Produced (in repo root)

- `phase1_5_prompt_v5_final.md` — updated Phase 1.5 prompt

---

## What's NOT Done

Per user's "Stop after preconditions report":
- No simulator modifications.
- No Feature Factory execution.
- No `build_wide_abt.py` execution (Phase 1.5 input not yet built).
- No PD calibration (deferred to Phase 4).
- No external communication.
