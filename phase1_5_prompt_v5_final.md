# Phase 1.5 Feature Factory — Prompt v5 (final)

**Supersedes**: phase1_5_prompt_v4_final.md
**Updated**: 2026-05-07
**Reason for v5**: rebased on the 800/day production run (`final_data_800d_60m_p00`) per data freeze of 2026-05-07. Replaces stale 333K row references and "500c" paths.

---

## Anchor Numbers (use these everywhere)

| Property | v4 (stale, 500/day) | **v5 (current, 800/day)** |
|----------|--------------------:|--------------------------:|
| Wide ABT rows | 333,964 | **534,400** |
| Train rows | ~244,000 | **389,600** |
| OOT rows | ~90,000 | **144,800** |
| Train events | unknown | **6,436** |
| OOT events | unknown | **1,238** |
| Train DR | varied | **1.652%** |
| OOT DR | varied | **0.855%** |
| Cohorts | 22 (202509-202706) | **22 (202509-202706)** |
| Wide ABT cols | 192 | **192** (structure unchanged) |

## Path Inventory

| Role | v4 path (stale) | **v5 path (current)** |
|------|-----------------|-----------------------|
| Simulator output | `examples/thesis_baseline/runs/thesis_baseline/` | **`artifacts/final_data_800d_60m_p00/`** |
| Wide ABT (build_wide_abt.py output) | `artifacts/thesis_wide_abt_12m_500c_clean/` | **`artifacts/thesis_wide_abt_800d_60m_p00/`** |
| Feature factory output | `artifacts/phase1_5_feature_factory/` | **`artifacts/phase1_5_feature_factory/`** (unchanged) |

## Cohort Eligibility (Precondition 1 decision)

**Option A: include all 22 cohorts.** No `cohort_eligibility_config.yaml` is needed.
- Maturity-matched analysis (in `preconditions_report.md`) confirms 202706 has fully observable target window (sim ends 202905, target window for 202706 ends 202905).
- All OOT cohorts (202701-202706) cluster within 0.79-0.95% DR at +23m matched age.
- Phase 1.5 simply reads the wide ABT as produced by `build_wide_abt.py`; cohort filtering is already applied there.

## Pre-Phase-1.5 Sequence (must run in order)

### Step 0 — Verify base data freeze
Confirm `artifacts/final_data_800d_60m_p00/` exists with:
- `accounts.csv` (1,460,800 rows, 111 MB)
- `transactions.csv` (29,266,484 rows, ~1.55 GB)
- `summary_abt_<period>.csv` for periods 202405-202904
- `abt_base_<period>.csv` for periods 202405-202904
- `data_generation_config_used.yaml`
- `validation_results.json`
- `cohort_default_rates.csv`

### Step 1 — Build the wide ABT
Run `build_wide_abt.py` against the new simulator output:

```bash
uv run python scripts/build_wide_abt.py \
    --data-dir artifacts/final_data_800d_60m_p00 \
    --output-dir artifacts/thesis_wide_abt_800d_60m_p00
```

(Or via a small wrapper script if CLI flags differ.)

Expected output: `artifacts/thesis_wide_abt_800d_60m_p00/thesis_wide_abt.csv` with 534,400 rows × 192 cols.

**Pre-flight gate**: row count must be in [510,000, 560,000]; train/OOT split must match 389,600/144,800 ± 1% slack.

### Step 2 — Update Phase 1.5 input path
Edit `scripts/phase1_5_feature_factory.py` line 67:

```python
# Before:
INPUT_CSV = Path("artifacts/thesis_wide_abt_12m_500c_clean/thesis_wide_abt.csv")
# After:
INPUT_CSV = Path("artifacts/thesis_wide_abt_800d_60m_p00/thesis_wide_abt.csv")
```

This is the only required source edit.

### Step 3 — Phase 1.5 Step A pre-generation gate
Before generating any feature, the script must verify:

| Check | Expected | Hard fail if |
|-------|----------|--------------|
| Row count | ≈534,400 | < 510,000 |
| Column count | 192 | ≠ 192 |
| `default_flag_12m` distinct values | {0, 1} | NaN present |
| Train rows | ≈389,600 | < 350,000 or > 420,000 |
| OOT rows | ≈144,800 | < 130,000 or > 160,000 |
| `fin_period` range | [202509, 202706] | outside |
| `score` column | absent | present |
| `scorem` column | absent | present |

(`score`/`scorem` absence is verified — see `final_run_validation_report.md` §8 — but Step A re-checks defensively.)

### Step 4 — Generate feature families
Per the existing v4 specification (unchanged):
- F1 Rolling: 338 features
- F2 Trend: 117 features
- F3 Ratio: 17 features
- F4 Interaction: 9 features
- F5A Group stats: 37 features
- F5B Group ratios: 12 features
- F6A-E Transforms/controls: ~1,668 features

**Target total**: ~2,200-2,400 features (range, depending on safe-app survival rate).

### Step 5 — Step B: governance metadata catalog
14-field metadata per generated column:
- `feature_name`, `feature_family`, `parent_feature`, `monthly_offsets_used`, `aggregation_op`, `derivation_formula`, `dtype`, `cardinality`, `pct_null`, `train_mean`, `train_std`, `is_constant`, `risk_level` (A-H), `notes`

### Step 6 — Step C: write outputs
- `artifacts/phase1_5_feature_factory/thesis_wide_abt_expanded.parquet` (or `.csv.gz` fallback)
- `artifacts/phase1_5_feature_factory/feature_catalog.csv`
- `artifacts/phase1_5_feature_factory/feature_family_summary.txt`
- `artifacts/phase1_5_feature_factory/run_config.json`
- `artifacts/phase1_5_feature_factory/phase1_5_report.md`
- `artifacts/phase1_5_feature_factory/extraction_log.txt`

### Step 7 — Validation
After expansion:
- Row count unchanged (still 534,400)
- All original columns preserved
- New columns match `feature_catalog.csv` 1-1
- No new column has all-null or all-constant values (or, if it does, it is flagged in catalog and excluded from downstream sets)

## Risk-Level Inheritance (Rule Precedence A-H)

Unchanged from v4. Levels:
- **A** target / leakage source
- **B** ID / metadata
- **C** late behavioral (months > 12 post-origination)
- **D** aggregate of late behavioral
- **E** loan-term parameters set at origination but jointly determined with target
- **F** early behavioral (months 1-12)
- **G** safe application features (origination snapshot)
- **H** random / synthetic noise

Most-restrictive-wins: any feature whose lineage touches level A or B is excluded.

## Known Properties of the New Data (v5-specific)

These were unknown at v4 because the data did not exist. v5 anchors them:

1. **`score`/`scorem` excluded**: confirmed absent from wide ABT via `FINAL_COLS` whitelist audit (build_wide_abt.py line 923).
2. **Train/OOT app-feature distributions identical**: max PSI = 0.000106, max |SMD| = 0.0038. No covariate shift; only target-rate shift.
3. **Vintage drift**: cohort DR decays monotonically from 2.88% (202509) to 0.81% (202706). Models will need calibration adjustment in Phase 4.
4. **Loan terms**: `n_installments ∈ {12, 24, 36}` with mean 19.6, median 12. `installment` mean 248, median 223. `loan_amount` = `installment × n_installments` (deterministic).
5. **Categorical cardinalities**: `app_nom_branch` 4 values, `app_nom_gender` 2, `app_nom_job_code` 4, `app_nom_marital_status` 4, `app_nom_home_status` 2, `app_nom_cars` 2.
6. **Burn-in cohorts excluded**: 202405-202508 (390,400 accounts). Their high DR (22.4% → 6.4%) reflects simulator quota mechanics, not portfolio behavior.

## Deferred to Phase 4 (do not attempt in 1.5)

- PD calibration (Brier, ECE, reliability diagram, Hosmer-Lemeshow)
- Observed:Expected ratio per decile
- Profit-curve, KS, lift charts
- ROC/Gini stability tests across cohorts

These require PD predictions on the new ABT, which do not yet exist.

## Stopping Conditions (treat any as a hard stop)

- Wide ABT row count outside [510K, 560K]
- More than 5% of generated features marked constant (catalog risk_level = H)
- Phase 1.5 wall time exceeds 4× the 333K baseline (suggests memory thrashing)
- Any feature with risk_level A or B leaks into the safe-feature set

If any condition trips, stop, write a diagnostic report, and ask for direction.
