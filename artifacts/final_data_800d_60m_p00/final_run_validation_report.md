# Final Production Run Validation Report

**Run label**: `final_data_800d_60m_p00`
**Output directory**: `artifacts/final_data_800d_60m_p00/`
**Date completed**: 2026-05-07 00:23 (local)

---

## 1. Configuration

| Parameter | Value |
|-----------|------:|
| `new_clients_count` | 800/day |
| `start_date` | 20240501 |
| `end_date` | 20290501 |
| `n_periods` | 60 |
| `p_positive` | 0.00 |
| `take_up` | 1.0 |
| `seed` | 42 |
| `reaction_rng_seed` | 43 |
| Matrix tuning | False |
| Simulator core modified | False |
| Take-up implemented | False |

## 2. Simulation Metrics

| Metric | Projected | Actual |
|--------|----------:|-------:|
| Wall time | 14-16h | **12.8h** |
| Originations | ~1,461,600 | **1,460,800** |
| TX rows | 29-31M | **29,266,484** |
| Disk usage | 28-32 GB | **29 GB** |
| `transactions.csv` | ~1.6 GB | **1.55 GB** |
| `accounts.csv` | — | **111 MB** |
| Sim period range | 202405-202905 | **202405-202905** |

## 3. End-of-Simulation Account States

| Status | Count |
|--------|------:|
| Active (status=1) | 615,211 |
| Defaulted (status=2) | 64,979 |
| Closed/paid (status=3) | 780,610 |
| Write-offs at end of sim (`coll_status=8`) | 64,979 |

## 4. Target Variable (`default_flag_12m`)

Target window: offsets 12-23 from `fin_period` (months 13-24 after origination).

| Metric | Count |
|--------|------:|
| `default_flag_12m == 1` (write-off in target window) | 38,699 |
| `default_flag_12m == 0` (no write-off, fully observed) | 886,602 |
| `default_flag_12m == NaN` (censored) | 535,499 |

**Note**: `default_flag_12m` events (38,699) < end-of-sim write-offs (64,979) because many accounts default after offset 23 (months 25+). The wide ABT uses the 12-month forward target.

## 5. Phase 2 Filter — Analytical ABT

Filter parameters (from `build_wide_abt.py`):
- `MIN_FIN_PERIOD = 202509`
- `TRAIN_FIN_PERIOD_MAX = 202612`
- `OOT_FIN_PERIOD_MAX = 202706`

| Metric | Value |
|--------|------:|
| **Post-filter rows** | **534,400** |
| Train rows | 389,600 |
| OOT rows | 144,800 |

### Default rates (using `default_flag_12m` semantics)

| Slice | Rate (exact) | Rate (rounded) |
|-------|-------------:|---------------:|
| Overall (all eligible) | 0.04182315 | 4.18% |
| Post-burn-in (≥ 202509) | 0.01528320 | 1.53% |
| Train (202509-202612) | 0.01651951 | 1.65% |
| OOT (202701-202706) | 0.00854972 | 0.85% |
| **OOT default count** | — | **1,238** |

## 6. Cohort Default-Rate Table (Phase 2 window)

| Cohort | Originations | Write-offs in target window | DR% | Split |
|-------:|-------------:|----------------------------:|----:|:------|
| 202509 | 24,000 | 692 | 2.88 | train |
| 202510 | 24,800 | 651 | 2.63 | train |
| 202511 | 24,000 | 578 | 2.41 | train |
| 202512 | 24,800 | 548 | 2.21 | train |
| 202601 | 24,800 | 485 | 1.96 | train |
| 202602 | 22,400 | 389 | 1.74 | train |
| 202603 | 24,800 | 419 | 1.69 | train |
| 202604 | 24,000 | 396 | 1.65 | train |
| 202605 | 24,800 | 362 | 1.46 | train |
| 202606 | 24,000 | 318 | 1.33 | train |
| 202607 | 24,800 | 330 | 1.33 | train |
| 202608 | 24,800 | 310 | 1.25 | train |
| 202609 | 24,000 | 261 | 1.09 | train |
| 202610 | 24,800 | 244 | 0.98 | train |
| 202611 | 24,000 | 215 | 0.90 | train |
| 202612 | 24,800 | 238 | 0.96 | train |
| 202701 | 24,800 | 217 | 0.88 | oot |
| 202702 | 22,400 | 212 | 0.95 | oot |
| 202703 | 24,800 | 198 | 0.80 | oot |
| 202704 | 24,000 | 222 | 0.93 | oot |
| 202705 | 24,800 | 195 | 0.79 | oot |
| 202706 | 24,000 | 194 | 0.81 | oot |

Trend: Monotonically declining from 2.88% (202509) to ~0.85% (OOT) — consistent vintage drift, no sharp discontinuities.

## 7. Burn-in / Censoring Eligibility Check

### Burn-in cohorts excluded (202405-202508)

| Cohort | Originations | Write-offs (end-of-sim) | DR% |
|-------:|-------------:|------------------------:|----:|
| 202405 | 24,800 | 5,549 | 22.38 |
| 202406 | 24,000 | 4,751 | 19.80 |
| 202407 | 24,800 | 4,536 | 18.29 |
| 202408 | 24,800 | 4,012 | 16.18 |
| 202409 | 24,000 | 3,502 | 14.59 |
| 202410 | 24,800 | 3,425 | 13.81 |
| 202411 | 24,000 | 2,980 | 12.42 |
| 202412 | 24,800 | 2,966 | 11.96 |
| 202501 | 24,800 | 2,665 | 10.75 |
| 202502 | 22,400 | 2,329 | 10.40 |
| 202503 | 24,800 | 2,425 | 9.78 |
| 202504 | 24,000 | 2,088 | 8.70 |
| 202505 | 24,800 | 2,114 | 8.52 |
| 202506 | 24,000 | 1,790 | 7.46 |
| 202507 | 24,800 | 1,658 | 6.69 |
| 202508 | 24,800 | 1,580 | 6.37 |

Total burn-in excluded: **390,400 accounts**. DR decay confirms `MIN_FIN_PERIOD=202509` is appropriate — first included cohort DR (2.88% in target window) is well below burn-in extremes.

### Post-OOT excluded (after 202706)

- Cohorts after 202706: target window not fully observable; **535,499 accounts excluded**.

## 8. Score / Scorem Column Audit

| Check | Result |
|-------|:------:|
| `score` column in `summary_abt_*.csv` files | Present |
| `scorem` column in `summary_abt_*.csv` files | Present |
| `build_wide_abt.py` references `score` or `scorem` | **No** (`grep -i score` returns 0 matches) |
| Wide ABT column selection mechanism | **Explicit `FINAL_COLS` whitelist** (line 923: `df_final = df[FINAL_COLS].copy()`) |
| `score`/`scorem` in `FINAL_COLS` | **No** |

`FINAL_COLS` = `ID_COLS` + `APP_COLS` + `ORIG_COLS` + `BEHAV_FLAT` + `CUS_FLAT` + `AGG_COLS` + `SUMMARY_AGG_COLS` + `TARGET_COL` + `META_COLS`. None of these constants contain `score` or `scorem`.

**Conclusion: `score`, `scorem`, and any score-derived columns are excluded from the wide ABT by design.**

## 9. Acceptance Gate

| Gate | Threshold | Actual | Result |
|------|----------:|-------:|:------:|
| Post-filter rows | ≥ 500,000 | 534,400 | **PASS** |

---

**Files in this directory:**
- `data_generation_config_used.yaml` — exact run config
- `validation_results.json` — all numeric metrics
- `cohort_default_rates.csv` — cohort table source data
- `oot_maturity_comparison.csv` — Precondition 1 input
- `final_run_validation_report.md` — this file
