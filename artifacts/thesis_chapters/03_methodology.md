# Chapter 3 — Methodology

This chapter documents the empirical design that underpins the thesis. It
describes (i) the data-generation process based on the synthetic
`rl-debt-collection` simulator, (ii) the feature-engineering pipeline and
its governance regime, (iii) the dual-track Probability of Default (PD)
modelling architecture and the leak-free calibration design, (iv) the
locked tenor-aware Lifetime Net Margin economic framework, (v) the stress
testing design that probes the sensitivity of profit-driven cut-off
selection, (vi) the bootstrap validation procedure used to quantify
sampling uncertainty, and (vii) the software architecture that supports
reproducibility. The chapter is deliberately precise about scope: where
findings are conditioned on the simulator, on a particular cohort window,
or on a particular stress grid, that conditionality is stated explicitly
rather than implied.

The phrasing rules used throughout follow `thesis_methodology_lock.md`: the
text uses *across N resamples* or *in K of K stress cells* rather than
true probability statements, and *within the tested scenario space* rather
than universal claims. Where a result is shown to hold without exception
across the tested grid the language is correspondingly stronger; where the
finding admits known counter-examples (for instance, the rare adverse-stress
+ high-op-cost cells in which the profit cut-off is less permissive than
Youden's J), this chapter and the Results chapter say so explicitly.

---

## 3.1 Data Generation

### Simulator overview

The empirical foundation of this thesis is a single production run of the
`rl-debt-collection` simulator [TODO: cite simulator repository / authoring
team]. The simulator is a quota-based Markov-style model: at every monthly
period it generates a configurable number of new accounts, then for every
active account it advances the payment stage by a *deterministic
quota assignment* rather than by an independent per-account Bernoulli
draw. Two transition matrices are defined — a default matrix and a
"positive" matrix that softens transitions when the borrower reacts
favourably to a collection action — and the entries of these matrices
specify *marginal quotas*: for each current delinquency state, the matrix
row gives the share of that state's population that should move to each
next state in the coming period. The simulator implements these quotas as
follows. Within each delinquency state at each period it ranks the
constituent accounts by an internal *score* (a weighted combination of
borrower demographics and behavioural columns plus a small Gaussian
noise term injected into the score formula). The next-state assignment
is then made by walking the cumulative quota thresholds along the
ranked list: the bottom-`q1` fraction by score is moved to the worst
next state, the next `q2` fraction to the second-worst, and so on. The
choice between the default and positive transition matrices is governed
by the `p_positive` parameter, which sets the per-account, per-period
probability of switching to the positive matrix. This thesis uses
`p_positive = 0.00`, which removes positive-matrix switching entirely
but does *not* eliminate all simulator-side randomness: the score-noise
term, the random ordering of ties, and the random generation of new
client demographics each period continue to inject stochastic variation
into the cohort behaviour. Setting `p_positive = 0.00` therefore
isolates the *natural* default propensity of the cohorts (no
collection-action protective effect) without claiming a deterministic
trajectory for any individual account.

Two simulator features are central to the design choices below. First, the
write-off trigger fires when an account accumulates 12 missed
instalments (`coll_status = 8` when `due_installments ≥ 12`). This
threshold has direct consequences for short-tenor loans, as documented in
Section 3.4. Second, the simulator does not include any pricing field;
APR, funding cost, and operating cost are exogenous to the simulator and
therefore must be supplied as methodological assumptions during the
economic stage [TODO: cite zero-interest assumption discussion in
amortization theory references].

### Final production run configuration

Table 3.1 lists the locked configuration of the production run. The choice
of 800 clients per day at 60 monthly periods follows from a pre-flight
sensitivity study (documented in `_recovery/preflight_200.py` and the
preflight report) that established 800/day as the minimum scale at which
the post-Phase-2-filter row count exceeds the H1 threshold of 500,000
analytical observations.

**Table 3.1 — Locked production-run configuration**

| Parameter | Value |
|-----------|-------|
| `new_clients_count` | 800 per day |
| Simulation window | `start_date = 20240501` to `end_date = 20290501` |
| Monthly periods | 60 |
| `p_positive` | 0.00 |
| Random seed | 42 |
| `take_up` | 1.0 |
| `simulator_core_modified` | False |

Source: `scripts/final_run_800d.py` and
`artifacts/final_data_800d_60m_p00/data_generation_config_used.yaml`.

### Population structure and the 12-month target

The simulator output is post-processed by `scripts/build_wide_abt.py` into
a wide Analytical Base Table (ABT). The pipeline applies a Phase 2 cohort
filter — `MIN_FIN_PERIOD = 202509` (excludes the initial warm-up cohorts
from 202405 through 202508, i.e. the first 16 monthly origination cohorts),
`TRAIN_FIN_PERIOD_MAX = 202612`, and `OOT_FIN_PERIOD_MAX = 202706` — and
constructs the binary target `default_flag_12m`. The target is defined as
the occurrence of a write-off (`coll_status = 8`) within the offset window
`t ∈ [12, 23]` from origination, i.e. months 13 through 24 after the loan
starts. This 12-month forward target is the empirical
operationalisation of "default within one year of observation" used
throughout the thesis [TODO: cite Basel III Probability of Default
horizon convention].

The locked production run yielded 1,460,800 originations and a final
modelling population of 534,314 rows (Table 3.2). The post-filter row
count comfortably satisfies the H1 hard requirement (≥ 500,000 rows). The
out-of-time (OOT) split contains 144,789 rows in the original wide ABT
across all loan tenors (12, 24, 36 months); after the economic-eligibility
refinement described in Section 3.4 the OOT population shrinks to the
64,027 rows used for the bootstrap analyses in Section 3.6.

**Table 3.2 — Population definitions**

| Population | Rows | Definition |
|------------|-----:|------------|
| Full modelling pop | 534,314 | Phase 2 wide ABT after cohort filter |
| Economic analysis pop | 235,968 | Modelling pop, `n_installments ∈ {24, 36}` only |
| OOT economics bootstrap pop | 64,027 | Eco pop with `split_new == 'oot'` |
| Train_for_model | 150,476 | Eco pop, cohorts 202509-202610 |
| Calibration slice | 21,465 | Eco pop, cohorts 202611-202612 |

### Justification for synthetic data

The thesis investigates the relationship between PD model discrimination,
calibration, and profit-driven cut-off selection. A simulated portfolio
isolates the methodological question from data-quality, regulatory, and
proprietary-data confounds that would dominate any single real-world
dataset [TODO: cite simulation-based credit-risk methodology, e.g.
Bohn & Stein 2009]. Limitations of this choice — chiefly the absence of
real APR, real LGD recovery, and real cross-cohort behaviour shifts — are
documented in Chapter 6.

---

## 3.2 Feature Engineering

### Feature factory design

The wide ABT produced by `build_wide_abt.py` carries 192 raw columns,
including identifier, target, split, application demographics, loan terms,
and 12 months of behavioural history per series. The Phase 1.5 Feature
Factory (`scripts/phase1_5_feature_factory.py`) expands this 192-column
input into a 2,236-column ABT with full governance metadata for every
generated column. Of the expanded set, 2,229 are *raw features* (excluding
identifier, target, split, and metadata).

Six families of generated features are produced (Table 3.3). Each family
has a documented derivation rule and a default risk-level inheritance from
its source columns.

**Table 3.3 — Generated feature families**

| Family | Description | Count |
|--------|-------------|------:|
| F1 | Rolling window statistics over 13 behavioural series (mean / std / min / max / median / last over 3-12 month windows) | 338 |
| F2 | Trend slope, intercept, and R² over 3, 6, 12 month windows | 117 |
| F3 | Domain-driven ratios (income / loan / installment / age) | 12 |
| F4 | Pairwise interactions of safe application variables and loan terms | 9 |
| F5A / F5B | Group statistics by categorical variable (mean / median / std / count / rank) | 37 + 15 |
| F6A | Rank, percentile, z-score, log1p, square-root transforms of every numeric original | 885 |
| F6B | One-hot decile / quartile bin indicators | 156 |
| F6C | Noisy copies of every numeric original (var + N(0, 0.1·σ)) | 177 |
| F6D | Pure random negative controls (uniform, normal, integer) | 100 |
| F6E | Synthetic bureau-like features (credit score, account age, utilisation, payment history, etc.) built from safe app variables + noise only | 200 |

Total generated: 2,046. Plus 190 originals (after duplicate-column removal
of `app_loan_amount` and `app_n_installments`, which are perfect duplicates
of `loan_amount` and `n_installments` respectively).

### Governance regime and PD eligibility

Every column in the catalog carries fourteen governance fields, including
`feature_family`, `source_columns`, `formula`, `availability_time`,
`source_window`, `uses_target`, `uses_future_behavior`,
`allowed_for_origination_pd`, `allowed_for_behavioral_pd`,
`allowed_for_profit`, `leakage_risk`, and a textual reason explaining any
PD eligibility refusal. Risk levels range from A (target / leakage source)
through H (random control), and are inherited from the most-restrictive
source under the lock's "most-restrictive-wins" rule. The factory writes
the catalog to `artifacts/phase1_5_feature_factory/feature_catalog.csv`.

For Phase 2 modelling the candidate pool is reduced by the predicate
`allowed_for_origination_pd == True AND leakage_risk != 'high' AND
uses_target == False AND uses_future_behavior == False`. This filter
yields 435 PD-eligible features, distributed across families as documented
in `phase2_modeling_report.md`. The filtering is implemented in
`src/governance.py:filter_pd_eligible` and applied uniformly by every
downstream notebook.

### F6D negative controls and pipeline integrity

The 100 F6D features are pure random draws independent of any borrower
attribute. They function as negative controls: a properly configured
selection pipeline must reject them, since they carry no signal. Across
the nine Stage-2 Lasso configurations tested in Phase 2A diagnostics
(Cs = {0.02, 0.05, 0.10} × seeds = {42, 101, 202}), zero F6D features
survived in any run. After the LightGBM retune (Phase 2A Section 3),
zero F6D features appear in the top-20 by gain importance, although small
non-zero gains (the largest is approximately 1/100 of the top feature's
gain) appear deeper in the importance distribution as a normal consequence
of moderate regularisation. The unit-test gate "F6D in top-20 == 0" passed
on the tuned model.

### Score / scorem exclusion

The simulator's internal `score` and `scorem` columns are produced by
`src/abt_behavioral_columns.py:make_summary_abt`. A diagnostic experiment
in Phase 2A (`exp2_score_gini`) measured the absolute Gini of `score`
against `default_flag_12m` at the observation point and found values in the
range 0.93-0.97; the column is therefore near-tautological. The locked
build pipeline excludes `score`, `scorem`, and any score-derived column
from the wide ABT by an explicit `FINAL_COLS` whitelist in
`scripts/build_wide_abt.py:923`. The validator
`src/governance.py:validate_no_score_columns` is invoked at the start of
every Phase 2 notebook and asserts the absence of these columns.

---

## 3.3 PD Modelling

### Dual-track architecture

The thesis adopts a dual-track PD modelling architecture: an interpretable
linear track based on Logistic Regression, and a non-linear gradient-boosted
track based on LightGBM. Within the linear track three model variants are
compared: (i) a 22-feature Logistic Regression with full F6E synthetic
bureau features included (referred to as `LR full-F6E`), (ii) a 7-feature
Logistic Regression that excludes the F6E family entirely (`LR no-F6E`),
and (iii) a Weight-of-Evidence (WoE) scorecard built on the no-F6E feature
set (`Scorecard no-F6E`). Together with the tuned LightGBM model these
constitute the *four base PD models* used throughout Chapters 4 and 5.

The motivation for the dual-track approach is twofold. First, the linear
track is interpretable and remains familiar to credit-risk regulators
and auditors [TODO: cite scorecard literature, e.g. Anderson 2007 or
Siddiqi 2017]. Second, the LightGBM track captures non-linear interactions
that the linear track cannot represent without explicit feature
engineering, providing an upper bound on the discriminative power available
within the locked governance regime [TODO: cite Ke et al. 2017 LightGBM
paper].

### Stage 1 / Stage 2 / Stage 3 selection

The 7- and 22-feature Logistic Regression models are produced by a
three-stage selection pipeline:

- **Stage 1 (univariate prescreening, `src/modeling.py:run_stage1_prescreening`)**:
  filters by sparsity (`pct_nan ≤ 0.5`), variance (train standard
  deviation > 0), univariate Gini (`train_gini ≥ 0.02`), and stability
  (`|train_gini − OOT_gini| / max(train_gini, ε) ≤ 0.20`). The 435
  PD-eligible features reduce to 120 Stage-1 survivors.
- **Stage 2 (Lasso selection, `run_lasso_selection`)**: a single-fit
  L1-penalised Logistic Regression at `C = 0.05` on a 100,000-row
  stratified sub-sample of the training population, using the `liblinear`
  solver. Single-fit Lasso with a fixed `C` is the established convention
  for variable selection at this feature-count scale, in preference to
  Cross-Validated Lasso which is well-known to exhibit instability for
  selection at low default rates [TODO: cite Hastie, Tibshirani &
  Wainwright 2015]. A nine-cell sensitivity sweep (Phase 2A diagnostics
  Test 2) over `C ∈ {0.02, 0.05, 0.10}` and seeds `{42, 101, 202}` produces
  Jaccard mean overlap of 0.567 across configurations and zero F6D
  survivors in every cell. Stage 2 reduces 120 to 64 survivors.
- **Stage 3 (statsmodels logit refinement)**: an unpenalised Logistic
  Regression on the Stage-2 survivors with Variance Inflation Factor (VIF)
  inspection and a `p < 0.05` cutoff. The final feature set contains 22
  features in the full-F6E variant and 7 features in the no-F6E variant.

### LightGBM tuning

The LightGBM track was retuned in Phase 2A after an initial run that
exhibited pathological early stopping (`best_iteration = 1`) and contained
one F6D feature in the top-20 by gain. The retune used Optuna [TODO: cite
Akiba et al. 2019] with the Tree-structured Parzen Estimator sampler, 30
trials, and a search space spanning `learning_rate`, `num_leaves`,
`min_child_samples`, `reg_alpha`, `reg_lambda`, `feature_fraction`, and
`bagging_fraction`. The early stopping validation slice was switched from
a random 15% sample of training to the temporal calibration cohorts
202611-202612, which match the OOT distribution more closely than a random
sub-sample. Best parameters from trial 4 (`learning_rate = 0.039`,
`num_leaves = 20`, `min_child_samples = 213`) yielded `best_iteration = 141`
and removed F6D from the top-20 by gain. The retuned model achieves OOT
AUC = 0.898 and Gini = 0.795 (Tables 3.4a and 3.4b below) and is locked
as the *primary* PD model for downstream Phase 3 and 4 work.

### Calibration design (leak-free)

All four base models are calibrated with Platt scaling [TODO: cite Platt
1999]. The calibration design avoids OOT leakage by partitioning the
training period into two slices: cohorts 202509-202610 are used for model
fitting (`train_for_model`, 150,476 rows in the eco-pop view) and cohorts
202611-202612 are used for calibration (`calib`, 21,465 rows). The OOT
cohorts 202701-202706 are touched only at evaluation time. The split is
implemented in `src/calibration.py:make_calibration_split`, which raises
`ValueError` if the calibration cohorts intersect the original `oot`
split, and the Phase 4 bootstrap honours the same partition.

A deliberate consequence of this design is that the Platt calibrator is
mean-anchored to the calibration-slice base rate (~0.85%) rather than the
eco-OOT base rate (1.92%, after excluding 12-month loans — see
Section 3.4). On the eco-OOT subset the LightGBM Platt-calibrated mean
predicted PD is 0.94% versus the empirical 1.92%, a predicted-to-observed
ratio of 0.49, corresponding to under-prediction by roughly a factor of
two on the eco-OOT subset. This is documented as a real calibration
weakness in Limitations §6 and reflected in Fig 6 (reliability diagrams).
The PD-multiplier scenarios used in Phase 3 and 4 (multipliers
{1, 2, 3, 5}) approximately bracket this calibration drift; the
profit-vs-Youden hypothesis is tested at every multiplier and survives
each one.

### OOT performance comparison

The OOT performance of the four base models is summarised in two tables
that intentionally separate two different evaluations on two different
populations. Table 3.4a reports *discrimination* metrics (AUC, Gini, KS)
on the full OOT split of the wide ABT (n = 144,789, all tenors). These
are taken from the per-phase modelling reports and depend only on the
ranking induced by each model — they are invariant to calibration. Table
3.4b reports *calibration* metrics (Brier, ECE, mean predicted vs
observed) on the economics-eligible OOT subset (n = 64,027, 24m and 36m
only). These are taken from
`artifacts/calibration_verification/calibration_summary.csv` and reveal
the calibration drift that motivated the caveat in the calibration design
discussion above.

The discrimination ranking and the calibration ranking do not coincide:
the LightGBM track dominates the discrimination ranking (highest AUC,
Gini, KS) but underestimates the empirical default rate by roughly a
factor of two on the eco-OOT subset; the LR full-F6E and LR no-F6E
variants have the lowest Expected Calibration Error but with weaker
discrimination than LightGBM. The 7-feature LR no-F6E is recommended as
the lean reference when interpretability is paramount; the 22-feature LR
full-F6E is the robustness variant; LightGBM is the primary predictive
model with the calibration caveat documented in Limitations §6. Figure 6
shows reliability diagrams for the four models on the eco-OOT subset;
Figure 7 compares the top-20 features by gain (LightGBM) and signed
coefficient (LR full-F6E).

![Figure 6 — Reliability diagrams across PD models on the eco-OOT subset](artifacts/figures/fig6_reliability_diagrams.png)

![Figure 7 — Top-20 feature importance comparison (LightGBM gain vs Lasso LR coefficient)](artifacts/figures/fig7_feature_importance.png)

**Table 3.4a — Discrimination on the full OOT split (n = 144,789, all tenors)**

| Model | Features | OOT AUC | OOT Gini | OOT KS | OOT Brier |
|-------|---------:|--------:|---------:|-------:|----------:|
| LR no-F6E | 7 | 0.836 | 0.672 | 0.540 | 0.0082 |
| LR full-F6E | 22 | 0.859 | 0.718 | 0.548 | 0.0080 |
| **LightGBM tuned (PRIMARY)** | 435 (best_iter 141) | **0.898** | **0.795** | **0.638** | **0.0079** |
| Scorecard no-F6E | 7 | 0.803 | 0.606 | 0.481 | 0.0179 |

Source: `artifacts/phase2_rerun_v2/model_metrics.json` (LR full-F6E),
`artifacts/phase2_rerun_v2/diagnostics/test1_f6e_ablation.json` (LR
no-F6E), `artifacts/pd_model/lightgbm_tuning_results.json` (LightGBM
tuned), `artifacts/scorecard/scorecard_metrics.json` (Scorecard no-F6E).
Brier values shown here are computed on the full OOT split (base rate
~0.85%, including 12-month loans whose default rate is structurally
zero); compare with Table 3.4b for the higher-base-rate eco-OOT Brier
values.

**Table 3.4b — Calibration on the eco-OOT subset (n = 64,027, 24m and 36m
only, post-Platt)**

| Model (post-Platt) | Eco-OOT AUC | Gini | Brier | ECE | Mean predicted | mean_pred / observed |
|--------------------|------------:|-----:|------:|----:|---------------:|---------------------:|
| LightGBM Platt (PRIMARY) | 0.902 | 0.804 | 0.0172 | **0.0098** | 0.94% | **0.49** ⚠ |
| LR full-F6E + Platt | 0.864 | 0.728 | 0.0167 | **0.0026** | 2.07% | 1.08 |
| LR no-F6E + Platt | 0.840 | 0.680 | 0.0170 | **0.0029** | 2.08% | 1.08 |
| Scorecard no-F6E + Platt | 0.803 | 0.606 | 0.0179 | 0.0100 | 0.92% | **0.48** ⚠ |

Source: `artifacts/calibration_verification/calibration_summary.csv`. The
empirical eco-OOT base rate is 1.92%. The two ⚠ markers identify
under-predicting models on this subset: LightGBM Platt and Scorecard
no-F6E predict less than half the empirical default rate, while the
two LR variants are within 8% of the empirical rate. Brier scores are
higher than in Table 3.4a because the eco-OOT base rate is higher
(1.92% vs ~0.85%); the Scorecard's Brier 0.0179 is essentially at the
"constant-base-rate predictor" floor of 0.0188, consistent with its
Gini 0.606 — i.e., the Scorecard is the worst-discriminating of the
four and consequently has the worst Brier on this population, whereas
its ECE 0.0100 is comparable to LightGBM's. The discrimination ranking
shifts marginally between Tables 3.4a and 3.4b because the eco-OOT
subset excludes the 12-month loans that have a structurally zero default
rate (Section 3.4).

---

## 3.4 Economic Framework

### Schema audit

Before implementing any economic formula the wide ABT was audited for the
fields required by tenor-aware Lifetime Expected Loss and Lifetime Net
Margin (`artifacts/economic_framework/schema_audit_report.md`). Three
findings shape the framework. First, the simulator is *zero-interest*:
the ratio `installment × n_installments / loan_amount` is 1.000000 ±
0.000000 across all rows. APR is therefore exogenous to the simulator and
must be supplied as a methodological assumption. Second, tenor varies
across only three values — 12, 24, and 36 months — and 12-month loans
exhibit a structurally impossible default rate (Section 3.4 below). Third,
LGD can in principle be derived from the post-default repayment trace in
`transactions.csv` but is treated as exogenous in the locked thesis design;
empirical LGD recovery is identified as Future Work F1.

### 12-month loan exclusion

The simulator's write-off mechanism requires 12 missed instalments
(`coll_status = 8` triggered when `due_installments ≥ 12`). For a
12-month loan the maximum number of missed instalments achievable while
the loan remains active is exactly 12, reached at month 12 — the
loan's terminal month. The `default_flag_12m` target is observed over the
forward window `offset ∈ [12, 23]`, i.e. months 13-24. A 12-month loan is
already closed (paid or written off at month 12) before the target window
begins, so the target is structurally unreachable. The empirical default
rate on 12-month loans is consequently 0/298,346 = 0.000% (compared with
2.31% for 24-month loans and 4.43% for 36-month loans). Including
12-month loans in the economic analysis would mechanically deflate
portfolio-level default rates by mixing in 298,346 zero-default rows.

The thesis therefore *excludes* 12-month loans from the economic-analysis
population, reducing it from 534,314 modelling rows to 235,968 economic
rows. This is a *scope refinement* documented honestly in Limitations §2,
not an H1 violation: the H1 row-count threshold is met at the modelling
level. Real institutions with 12-month products would observe non-zero
default rates; the exclusion is specific to the simulator's target-timing
artifact and does not generalise.

### Locked formula stack

The economic formulas are locked in `phase3_formula_lock.md` and
implemented in `src/economics.py`. Every function in the implementation
cites the lock section it implements. Nine unit tests in
`tests/test_economics.py` verify identity properties (e.g.,
`Σ marginal_PD_t over 12 months = PD_12m`), monotonicity (LT_EL increases
with PD, LGD, and loan amount; Expected Profit increases with APR;
Expected Profit decreases with LGD), and the no-double-counting identity
`Expected_Profit ≡ LT_margin − LT_EL`. All nine tests pass.

The conversion from the calibrated 12-month forward PD to a monthly
hazard uses the standard constant-hazard inversion:

$$h = 1 - (1 - \text{PD}_{12m})^{1/12}$$

The marginal PD schedule is then `survival_begin_t = (1 − h)^(t−1)` and
`marginal_PD_t = survival_begin_t · h` for `t = 1..n_installments`. By
construction `Σ_{t=1..12} marginal_PD_t = PD_12m`. For tenors greater than
12 months the same monthly hazard is extrapolated through the full
amortization schedule; this is the *constant-hazard assumption*
documented in Limitations §5 and identified as Future Work F4. The
amortization schedule itself uses standard French annuity arithmetic
(`src/economics.py:amortization_schedule`); for `apr = 0` the schedule
reduces to straight-line principal repayment, and for `apr > 0` it
produces the familiar declining-balance interest profile.

EAD at month `t` is set equal to the beginning-of-month outstanding
balance from the amortization schedule (`EAD_t = balance_begin_t`). This
is more conservative than treating the entire principal as exposure for
the full tenor and accurately reflects the declining loss profile of an
amortising loan.

The Lifetime Expected Loss is the discounted sum of period-by-period
expected losses:

$$\text{LT\_EL} = \sum_{t=1}^{n_\text{installments}} \text{marginal\_PD}_t \cdot \text{LGD} \cdot \text{EAD}_t \cdot \text{discount}_t$$

Lifetime Margin (gross of credit loss) accumulates expected interest
revenue weighted by survival, net of any operating cost:

$$\text{LT\_margin} = \sum_{t=1}^{n_\text{installments}} \big(\text{survival\_begin}_t \cdot \text{net\_interest}_t - \text{op\_cost}_t\big) \cdot \text{discount}_t$$

where `net_interest_t = balance_begin_t · max(APR − COF, 0) / 12` and
`op_cost_t = survival_begin_t · loan_amount · op_cost_annual / 12`. The
`max(·, 0)` floor on `APR − COF` enforces non-negative net interest in
configurations where funding cost exceeds APR.

The Expected Net Profit subtracts LT_EL exactly once and includes the
acquisition cost as a one-time origination expense:

$$\text{Expected\_Profit} = \text{LT\_margin} - \text{LT\_EL} - \text{acquisition\_cost}$$

Discount factors use end-of-month convention with monthly compounding:
`discount_t = 1 / (1 + discount_annual / 12)^t`. The base case sets
`op_cost_annual = 0` and `discount_annual = 0`; sensitivity grids are
documented in Section 3.5.

### APR scheme and LGD assumption

In the absence of any simulator pricing field the APR is supplied as a
locked five-tier risk-priced schedule (Table 3.5). The tier values are
informed by typical published APR ranges for unsecured consumer credit
[TODO: cite real-market APR survey, e.g., Federal Reserve G.19 release or
EU equivalent], scaled into the 12-30% band that is broadly consistent
with mainstream risk-priced unsecured lending. The thesis acknowledges
explicitly (Limitations §3) that these tiers are a methodological
assumption and not a market-validated calibration; sensitivity analyses
in Phase 3.2 and 4.2 use flat-APR alternatives at 12%, 18%, 24%, and 30%
in addition to the tiered scheme.

**Table 3.5 — Locked APR tier table**

| Band | Condition on PD₁₂ₘ | APR |
|------|--------------------|----:|
| Prime | PD < 0.005 | 0.12 |
| Near-prime | 0.005 ≤ PD < 0.010 | 0.18 |
| Mainstream | 0.010 ≤ PD < 0.020 | 0.22 |
| Subprime | 0.020 ≤ PD < 0.050 | 0.26 |
| Deep-subprime | PD ≥ 0.050 | 0.30 |

LGD is held at 0.65 in the base case, with a sensitivity grid spanning
{0.45, 0.55, 0.65, 0.75, 0.85}. The 0.65 value reflects an industry
baseline for unsecured consumer credit with informal collections [TODO:
cite Schuermann 2004 or equivalent LGD literature].

### ASB benchmark

The simpler "Adjusted Single-period Benchmark" formula
`profit_ASB = (1 − PD) · L · APR − PD · L · LGD` is implemented in
`src/economics.py` for reference but is *not* the main thesis formula.
It assumes one full year of interest at the full loan amount and ignores
tenor, amortization, and survival, and consequently understates lifetime
profit. Empirical comparison on the production population (Fig 4) shows
ASB underestimates total profit by approximately 9% on 24-month loans
and 40% on 36-month loans. The Lifetime formula is therefore the
thesis's main economic measure; ASB is reported only as a benchmark to
quantify the cost of formula simplification.

---

## 3.5 Stress Testing Design

### 576-cell economic stress grid

To quantify the sensitivity of the profit framework to economic
assumptions, Phase 3.2 evaluates a 576-cell grid spanning five dimensions:
PD multiplier `{1, 2, 3, 5}`, cost of funds `{0.00, 0.03, 0.06}`,
acquisition cost `{$0, $250, $500}`, LGD `{0.55, 0.65, 0.75, 0.85}`, and
APR strategy `{tiered_uncapped, tiered_cap_24, flat_18, flat_24}`. The
grid covers light-stress configurations (PD multiplier 1 with no costs)
through severe-stress configurations (PD multiplier 5 with high costs and
flat low APR). For each cell the framework computes mean profit, share of
profitable accounts, profit-optimal approval rate `k*`, profit-optimal PD
threshold, Youden's J approval rate, and the cutoff gap (profit `k*`
minus Youden `k`). Cells are classified as *approve-all* (`k* ≥ 99%`),
*interior* (`50% ≤ k* < 99%`), or *reject-most* (`k* < 50%`).

The driver hierarchy of the grid is summarised in Fig 9: PD multiplier
moves `k*` by 3.54 percentage points across its range, APR strategy by
2.32 pp, LGD by 1.28 pp, acquisition cost by 0.43 pp, and cost of funds
by 0.43 pp. PD-portfolio risk and APR strategy are the dominant
cut-off drivers within the tested space; the per-loan and per-period
costs play a smaller marginal role *until* operating cost is added in
Phase 4.2, at which point the cost-side reasserts dominance for the
adverse-stress scenario (Section 3.5 below).

### Anchor scenarios

Phase 4 condenses the 576-cell grid into four representative anchor
scenarios (Table 3.6) that span the classification space. The
realistic_central_boundary anchor sits exactly at the boundary between
approve-all and interior; bootstrap CIs (Section 3.6) confirm the
boundary classification is statistically tight rather than the artefact
of a random fluctuation. The moderate_interior anchor was added in
Phase 4.1 to populate the centre of the interior class; it is one stress
notch above realistic_central_boundary in PD multiplier and APR
strategy.

**Table 3.6 — Locked anchor scenarios**

| Anchor | PD mult | COF | Acq | LGD | APR | op_cost |
|--------|--------:|----:|----:|----:|-----|--------:|
| optimistic_base | 1.0 | 0.00 | $0 | 0.55 | tiered_uncapped | 0.00 |
| realistic_central_boundary | 2.0 | 0.03 | $250 | 0.65 | tiered_cap_24 | 0.00 |
| moderate_interior | 3.0 | 0.03 | $250 | 0.65 | flat_18 | 0.00 |
| adverse_stress | 5.0 | 0.06 | $500 | 0.85 | flat_18 | 0.00 |

### PD-quality stress (Gini perturbation)

A separate Phase 4.2 study (PART A) tests the sensitivity of the
profit-vs-Youden finding to PD model discrimination quality. The
calibrated PRIMARY PD is perturbed using
`src/calibration.py:perturb_to_target_gini`, which adds Gaussian noise to
the logit-space score and binary-searches the noise standard deviation to
hit a specified target Gini, then re-anchors the mean back to the
empirical base rate. Three target Ginis are tested: 0.30, 0.45, 0.60.
The raw model has Gini ≈ 0.80. Each perturbed PD variant is then run
through all four anchor scenarios, producing a 16-cell sub-grid. The
finding (visualised in Fig 2) is that the cutoff gap *widens* monotonically
as Gini falls — from a mean +15.5 pp at raw to +35.7 pp at Gini 0.30 —
because Youden's J becomes more conservative as discrimination falls
while the profit-optimal cut-off remains close to the full population.

This is interpreted in the thesis as *portfolio risk stress* expressed
through a degraded PD signal, not as a claim about the absolute quality
of the underlying simulator's PD models.

### Operating cost robustness

A second Phase 4.2 study (PART B) varies operating cost across
`{0.00, 0.01, 0.02, 0.04}` for three anchor scenarios. The study finds
the only *reject-most* regime in the entire 64-cell stress space:
adverse_stress combined with op_cost_annual ≥ 4% pushes `k*` to 0.31%,
mean profit to −$390 per loan, and total profit to −$92M. At op_cost ≤ 2%
the framework remains in the interior regime even under adverse stress.
Operating cost is identified as a powerful lever that the original 576-cell
grid (which held op_cost at zero) understated. Future work F2 should
include op_cost as a primary stress dimension in any market-calibrated
extension.

### Combined mini-grid

A 36-cell combined grid (Phase 4.2 PART C) crosses Gini ∈ {raw, 0.60,
0.45, 0.30}, op_cost ∈ {0, 0.02, 0.04}, and three anchor scenarios. The
combined grid produces four reject-most cells (all in adverse_stress at
op_cost = 0.04, regardless of Gini) and 31 interior cells; one
approve-all cell remains. Critically, profit uplift over Youden is
strictly positive in 36/36 combined cells, even in the five cells where
the profit cut-off is *less* permissive than Youden. This separation
between cut-off direction and dollar uplift is documented as Claim 2
in `thesis_evidence_map.md`.

---

## 3.6 Bootstrap Validation

### Design and stratification

The bootstrap validation in Phase 4.1 quantifies sampling uncertainty
within the OOT economics population (64,027 rows). One thousand resamples
are drawn with replacement, *stratified by tenor* (24m and 36m proportions
preserved in every resample), with `random_state = 42`. Per resample and
per anchor the framework recomputes the full economic pipeline and stores:
`profit_at_kstar`, `approve_pct_kstar`, `cutoff_pd_star`,
`profit_at_youden`, `approve_pct_youden`, `cutoff_gap`, `profit_uplift`,
and `profit_uplift_pct`. Across the four anchor scenarios this produces
4,000 (anchor × resample) records.

Per-anchor 95% confidence intervals (2.5%-97.5% percentile method) are
narrow in absolute terms (Table 3.7), confirming that the cut-off
classification is a tight statistical conclusion and not an artefact of
sampling. Notably the realistic_central_boundary anchor sits at
`k* = 99.25%` with a CI `[99.16%, 99.36%]` — entirely above 99%, so the
boundary classification is retained across 1,000 of 1,000 resamples
rather than flipping randomly between approve-all and interior. The
moderate_interior anchor sits at `k* = 95.31%` with CI `[94.99%, 95.50%]`
and the adverse_stress at `k* = 84.83%` with CI `[84.31%, 85.27%]`; both
remain firmly in the interior class.

**Table 3.7 — Bootstrap CIs for the cutoff gap**

| Anchor | k* approve % (95% CI) | cutoff_gap (95% CI, pp) |
|--------|-----------------------:|-------------------------:|
| optimistic_base | 100.00 [100.00, 100.00] | +20.41 [+20.10, +20.71] |
| realistic_central_boundary | 99.25 [99.16, 99.36] | +19.66 [+19.36, +19.97] |
| moderate_interior | 95.31 [94.99, 95.50] | +15.72 [+15.35, +16.02] |
| adverse_stress | 84.83 [84.31, 85.27] | +5.24 [+4.79, +5.64] |

Source: `artifacts/economic_framework/bootstrap_ci_summary.csv`. The full
4,000-row resample-level dataset is available at
`artifacts/economic_framework/bootstrap_anchor_results.parquet`. Figure 5
visualises the per-anchor density of `profit_uplift` with the 2.5%, 50%,
and 97.5% percentile lines.

![Figure 5 — Per-anchor bootstrap density of profit uplift with 2.5%, 50%, 97.5% percentile lines](artifacts/figures/fig5_bootstrap_ci_density.png)

### Phrasing rules

The bootstrap quantifies sampling uncertainty *within* the OOT population
only. It does *not* capture (i) PD model uncertainty across alternative
hyperparameters, (ii) calibration drift across cohorts beyond 202706,
(iii) APR / LGD / cost-of-funds assumption uncertainty, or (iv) formula
choice uncertainty (e.g., constant versus declining hazard). The thesis
text therefore reports bootstrap results using the locked phrasing
*"across N bootstrap resamples, profit uplift > 0 held in K of N
resamples"* rather than *"P(profit uplift > 0) = K/N"*. The empirical
frequency of a result holding in the bootstrap is not equivalent to the
true probability that the result generalises to other simulator
configurations or to real data; the bootstrap addresses only the
sampling-noise component of the total uncertainty.

---

## 3.7 Software Architecture

### Module structure

The empirical pipeline is implemented across two layers. The *re-usable
helper layer* lives under `src/` and contains six task-specific modules:
`governance.py` (PD-eligibility and validators), `modeling.py` (Stage 1,
Lasso, statsmodels logit, VIF), `evaluation.py` (Gini, KS, Brier,
calibration metrics, PSI), `calibration.py` (temporal split, Platt,
isotonic, `perturb_to_target_gini`, `StressTestPlan`), `scorecard.py`
(OptBinning + WoE + scorecard table builder), and `economics.py` (locked
Phase 3 formulas plus vectorised batch helpers). Each function carries a
docstring referencing the section of `phase3_formula_lock.md` it
implements where applicable, and unit tests in `tests/test_economics.py`
verify identity and monotonicity properties on the locked formulas.

The *analysis layer* lives under `notebooks/` and contains ten Jupyter
notebooks, one per analysis phase:

- `01_phase2_feature_selection.ipynb`
- `01a_phase2_diagnostics.ipynb`
- `01b_phase2_lightgbm_retune.ipynb`
- `01c_scorecard.ipynb`
- `02_economic_framework.ipynb`
- `03_economic_stress_test.ipynb`
- `04_bootstrap_cutoff_ci.ipynb`
- `05_pd_quality_opcost_stress.ipynb`
- `06_calibration_verification.ipynb`
- `07_visualization.ipynb`

Each notebook is independently executable end-to-end on the saved
artifacts (the wide ABT, the calibrated PD scores, the LightGBM model
pickle, the WoE-transformed ABT). The `nbconvert --to script` workflow
auto-exports each notebook to a `.py` file in `artifacts/...` for
executable archival. The `src/` modules are imported into the notebooks
rather than duplicated, so any change to the locked formulas propagates
to every analysis simultaneously.

### Reproducibility

All random seeds are explicit (`SEED = 42` in the production simulator
run, `random_state = 42` in every Lasso, LightGBM, Optuna, bootstrap
draw, and `perturb_to_target_gini` call). The simulator output is
gitignored due to size (~30 GB) but every downstream analysis is
deterministic given the locked simulator output. A user with the
simulator output, the `src/` modules, and any one of the ten notebooks
can regenerate the corresponding analysis exactly. The artifact
inventory (`artifact_inventory.md`) records sizes and regeneration costs
for every large file.

### Disciplinary boundaries observed

Three disciplinary rules were observed throughout the project. First, the
simulator core is treated as *immutable*: no file under
`rl-debt-collection/src/rl_debt_collection/` was modified. Second, the
locked formulas in `phase3_formula_lock.md` are treated as a *contract*:
implementations cite the lock and unit tests verify identities, so any
divergence is detectable. Third, every claim in the Results chapter has
a supporting artifact mapped in `thesis_evidence_map.md` and a
caveat-aware phrasing rule documented in `thesis_methodology_lock.md`.
This three-document discipline is intended to make every numerical
result in the thesis traceable to its underlying artifact and to make
the boundary conditions of every claim explicit.
