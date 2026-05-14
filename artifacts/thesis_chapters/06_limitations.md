# Chapter 6 — Limitations and Future Work

This chapter records the boundary conditions of the thesis formally and
catalogues the future-research directions that arise from those boundary
conditions. Both lists are deliberately exhaustive: the 10 limitations
of §6.1 and the 7 Future Work items of §6.2 are intended to give a
defensive reader a complete map of where the thesis's claims do not
extend and what work would be required to extend them. Every limitation
is cross-referenced to the chapter section in which the relevant
methodological choice was made; every Future Work item is
cross-referenced to the limitation it addresses.

The chapter introduces no new analysis. Numerical claims are sourced
from Chapters 3, 4, and 5; figure and table references point to
artifacts already documented. The wording rules of the previous
chapters apply throughout.

---

## 6.1 Limitations

The limitations below define the boundary conditions under which
the empirical claims of Chapters 4 and 5 are supported; they
delimit the tested scenario space rather than invalidate the
findings.

### Limitation 1 — Synthetic simulator data, not real-world data

**Statement.** All empirical results in this thesis derive from a
single production run of the synthetic `rl-debt-collection`
simulator (Chapter 3 §3.1) configured with seed 42, `p_positive = 0.00`,
800 clients per day, and a 60-month simulation window. Real
consumer-credit portfolios may exhibit behavioural patterns,
default trajectories, and feature distributions that differ
materially from the simulator's quota-based assignment
mechanism. The simulator approximates but does not replicate any
specific institution's data.

**Reference.** Chapter 3 §3.1 (data generation), §3.7 (software
architecture); Chapter 5 §5.4 (synthetic data positioned as
methodological feature); §5.5 first bullet (boundary condition).

**Scope of impact.** All four headline findings of Chapter 5 §5.1
are conditioned on the simulator's data-generation process. The
quantitative magnitudes (e.g., the dollar uplift CIs in
Table 4.6, the 11-47% relative profit gain in §5.2 Implication 1,
the cut-off gap range +5.33 to +20.59 pp in §4.3) are not
expected to transfer numerically to real data. The qualitative
findings (the strict positivity of dollar uplift, the widening
of the cut-off gap as PD discrimination falls, and the
existence of an adaptive reject-most regime under combined
stress) are expected to transfer in direction but with different
magnitudes; whether they survive the transition is the central
question of Future Work F2 and F7.

**Sensitivity coverage.** Not addressed by sensitivity analysis;
addressable only by replication on real data (Future Work F2).

### Limitation 2 — 12-month loans excluded from economics

**Statement.** Loans with `n_installments = 12` were excluded
from the economic-analysis population (Chapter 3 §3.4) because
the simulator's writeoff trigger (`coll_status = 8` when
`due_installments ≥ 12`) is structurally unreachable within the
`default_flag_12m` target window (offsets 12-23 from
origination). The empirical default rate on 12-month loans is
0/298,346 = 0.000%, reducing the economic-analysis population
from 534,314 modelling rows to 235,968 economic rows. This is
a simulator target-timing artefact, not a real-world conclusion
that 12-month loans are risk-free. Real institutions with
12-month products observe non-trivial default rates.

**Reference.** Chapter 3 §3.4 (12-month loan exclusion);
Chapter 4 §4.2 (population size impact); Chapter 5 §5.5 second
bullet (boundary condition).

**Scope of impact.** Restricts the economic-analysis population
to 24-month and 36-month loans. The H1 row-count threshold of
500,000 is satisfied at the modelling level (534,314 rows), so
the H1 specification is not violated; the economic analysis
proceeds on 235,968 rows. The thesis's quantitative findings
apply to 24-month and 36-month products and do not generalise
to short-tenor (≤ 12 months) lending without an alternative
default definition that addresses the timing artefact.

**Sensitivity coverage.** Not addressed by sensitivity analysis;
addressable by an alternative default definition (Future Work
F3).

### Limitation 3 — APR is exogenous, not market-observed

**Statement.** The simulator does not include any pricing field;
APR is supplied as a methodological assumption via the locked
five-tier risk-priced schedule (Chapter 3 §3.4 Table 3.5)
plus flat-APR alternatives at 12%, 18%, 24%, and 30%.
The locked tier values (0.12 / 0.18 / 0.22 / 0.26 / 0.30) are
informed by typical published consumer-credit pricing ranges
but are not market-validated against any specific institution
or jurisdiction.

**Reference.** Chapter 3 §3.4 (APR scheme); Chapter 4 §4.3
(APR-strategy spread on `k*` = 2.32 pp, second-largest driver);
Chapter 5 §5.5 fifth bullet (boundary condition).

**Scope of impact.** The APR strategy spread on `k*` (2.32 pp,
Table 4.5) means the choice of pricing scheme has measurable
consequences for the cut-off optimum. Different real-market
APR calibrations would shift the magnitude of the dollar uplift
figures in §4.4 and the absolute profit values in §4.2;
direction of the profit-vs-Youden finding is expected to be
robust because the locked sensitivity grid spans 12-30%.

**Sensitivity coverage.** Partially addressed: the four APR
strategies in the Phase 3.2 grid (tiered_uncapped,
tiered_cap_24, flat_18, flat_24) span a meaningful range, and
the profit-vs-Youden finding holds across all of them.
Market-calibration validation deferred to Future Work F5.

### Limitation 4 — LGD is exogenous, not empirically recovered

**Statement.** The LGD assumption (0.65 base case, sensitivity
grid {0.45, 0.55, 0.65, 0.75, 0.85}) is exogenous to the
simulator. Empirical LGD could in principle be derived from
the simulator's transaction trace
(`artifacts/final_data_800d_60m_p00/transactions.csv`) by
following the post-default repayment behaviour of every
defaulted account, but this derivation was deferred to keep
the thesis scope bounded.

**Reference.** Chapter 3 §3.4 (schema audit, LGD treatment,
LGD assumption); Chapter 5 §5.5 fifth bullet
(boundary condition).

**Scope of impact.** The LGD spread on `k*` in the Phase 3.2
stress grid is 1.28 pp (Table 4.5), the third-largest driver
after PD multiplier and APR strategy. The thesis's findings
are robust across LGD ∈ {0.55, 0.65, 0.75, 0.85} (the four
levels used in the 576-cell grid); the magnitude of the
dollar uplift would shift with empirical LGD calibration, but
the direction of the profit-vs-Youden finding is preserved
within the tested range.

**Sensitivity coverage.** Addressed by the four-level LGD grid
in Phase 3.2 and by the five-level sensitivity grid documented
in Chapter 3 §3.4. Empirical LGD recovery deferred to Future
Work F1.

### Limitation 5 — Constant monthly hazard assumption

**Statement.** The locked formulas (Chapter 3 §3.4) extrapolate
the monthly hazard `h = 1 − (1 − PD₁₂ₘ)^(1/12)` from the
12-month forward PD across the full amortization schedule. For
36-month loans this implies a cumulative PD of `1 − (1 − h)^36`,
assuming the same monthly hazard throughout the loan life.
Real-world monthly default hazards typically *decline* with
loan age (the curing effect: borrowers who survive the first
year are increasingly likely to keep paying), so the
constant-hazard assumption likely overstates lifetime expected
loss on long-tenor loans.

**Reference.** Chapter 3 §3.4 (locked formula stack, hazard
extrapolation); Chapter 5 §5.5 fourth bullet (boundary
condition).

**Scope of impact.** Lifetime EL on 36-month loans is
biased high by the constant-hazard assumption. Because
Expected Profit = LT_margin − LT_EL, this also biases
Expected Profit *low* on 36-month loans. A declining-hazard
alternative would likely increase expected profit for
long-tenor accepted loans, but the net effect on the
profit-uplift metric (which depends on the *gap* between
profit-driven and Youden cut-offs) should be verified
empirically under Future Work F4.

**Sensitivity coverage.** Not addressed by sensitivity analysis;
addressable by a Weibull or log-logistic hazard fit (Future
Work F4).

### Limitation 6 — LightGBM under-prediction on the eco-OOT subset

**Statement.** The PRIMARY PD model (LightGBM tuned + Platt) was
calibrated on the calibration slice (cohorts 202611-202612)
whose base default rate is approximately 0.85%. The economics-eligible
OOT subset (24-month and 36-month loans, n = 64,027) has an
empirical base rate of 1.92%, approximately twice the
calibration-slice base rate. On the eco-OOT subset the
LightGBM Platt-calibrated mean predicted PD is 0.94% versus
the empirical 1.92%, a predicted-to-observed ratio of 0.49 —
under-prediction by roughly a factor of two.

**Reference.** Chapter 3 §3.3 (calibration design, mean
under-prediction caveat), Table 3.4b (calibration verification);
Chapter 4 §4.1 (multi-model comparison reflecting the same
caveat); Chapter 5 §5.5 third bullet (boundary condition).

**Scope of impact.** The under-prediction is a real
calibration weakness on the eco-OOT subset specifically. The
PD-multiplier scenarios in Phase 3 and 4 (multipliers
{1, 2, 3, 5}) approximately bracket this calibration drift
because PD × 2 raises the mean predicted PD from ~0.94% to
~1.88%, very close to the empirical 1.92%. The
profit-vs-Youden hypothesis is tested at every multiplier and
survives each one (§4.5, §4.7), so the finding is not driven
by the under-prediction. Any real-world deployment of the
framework would need to re-calibrate against its own cohort
base rate.

**Sensitivity coverage.** Bracketed by the PD-multiplier
sensitivity in Phase 3 and 4. Direct re-calibration against an
expected eco-OOT base rate is straightforward future work.

### Limitation 7 — Operating cost sensitivity strong; base case excludes recurring op_cost

**Statement.** The Phase 3.2 576-cell economic stress grid held
operating cost at zero throughout, treating it as a separate
primary lever in Phase 4.2 PART B. The Phase 4.2 op_cost
robustness study (Chapter 4 §4.6) found that operating cost is
a powerful lever: at op_cost = 4% combined with adverse
economic stress, the framework collapses into the only
reject-most regime observed in the 64-cell stress space.
Real lending operations typically incur op_cost in the
1-5% range [TODO: cite banking operating-cost benchmarks; same
source as Chapter 4 §4.6]; the base case's `op_cost = 0` is
unrealistic for production deployment.

**Reference.** Chapter 3 §3.4 (base case parameters); Chapter
4 §4.6 (PART B op_cost robustness); Chapter 5 §5.2 Implication
2 (operational cost management is critical).

**Scope of impact.** The base economic results in §4.2 (mean
Expected Profit $1,493 per account, 100% positive Expected
Profit) are upper-bound estimates that do not reflect
real-world operating expense. The implications drawn from the
576-cell grid (§4.3) — particularly the absence of reject-most
cells in the grid — would shift if op_cost were added as a
sixth dimension. The reject-most regime under
adverse_stress + op_cost = 4% (§4.6) demonstrates that
operating cost can flip the framework's recommendation from
interior optimisation to near-rejection.

**Sensitivity coverage.** Addressed by Phase 4.2 PART B
(four-level op_cost grid {0.00, 0.01, 0.02, 0.04} on three
anchors) and by Phase 4.2 PART C (combined Gini × op_cost
mini-grid). Citation of real-market op_cost benchmarks is
flagged HIGH PRIORITY in Chapter 4 §4.6.

### Limitation 8 — Scorem / demographic over-determinism in simulator

**Statement.** The simulator's internal `score` and `scorem`
columns are produced by a fixed combination of borrower
demographic and behavioural features and are nearly
tautological with respect to default outcome (Phase 2A
diagnostic exp2 measured the absolute Gini of `score` against
`default_flag_12m` at the observation point in the 0.93-0.97
range). The simulator therefore exhibits stronger
demographic-to-outcome determinism than typical real
consumer-credit portfolios. The locked build pipeline excludes
`score`, `scorem`, and any score-derived column from the wide
ABT by an explicit `FINAL_COLS` whitelist
(`scripts/build_wide_abt.py:923`), preventing the leakage from
contaminating the PD models.

**Reference.** Chapter 3 §3.2 (score/scorem exclusion);
Chapter 4 §4.1 (F6D negative-control gate verifying no leakage
in the Lasso pipeline; LightGBM retune verifying no leakage
in the gradient-boosted track).

**Scope of impact.** The PD models trained on the wide ABT
benefit from strong demographic signals
(`app_nom_job_code`, `app_nom_marital_status`, `act_age`)
because the simulator's score formula weights these heavily.
Real consumer-credit data may show weaker demographic
determinism, in which case the PD models trained on real data
would have lower discrimination than the simulator-trained
LightGBM Gini ≈ 0.80. This is one mechanism by which
real-data discrimination might land in the Gini 0.45-0.60
range tested in Phase 4.2 PART A — the PD-quality stress
study is therefore a partial proxy for the real-data
transition documented under Future Work F2.

**Sensitivity coverage.** Indirectly addressed by the
PD-quality stress in Phase 4.2 PART A (which tests Gini levels
spanning 0.30-0.80). Direct addressing requires real-data
replication (Future Work F2).

### Limitation 9 — Single simulator configuration

**Statement.** All thesis results derive from a single
simulator seed (42), a single value of `p_positive` (0.00),
and a single client-generation rate (800 per day for 60
months). Cross-seed and cross-configuration robustness is not
empirically established. The bootstrap CIs in Phase 4.1
quantify within-OOT sampling uncertainty only and do not
capture cross-configuration variance.

**Reference.** Chapter 3 §3.1 (single production run);
Chapter 5 §5.5 first bullet (boundary condition); §5.6
Direction 3 (multi-seed simulator robustness as Future Work).

**Scope of impact.** All point estimates and CIs in Chapter 4
are conditioned on the single configuration. If the four
headline findings are sensitive to seed or to `p_positive`,
the thesis's quantitative magnitudes would change accordingly;
qualitative findings (strict positivity of dollar uplift,
widening of cut-off gap with weaker PD) may be more robust
because they reflect structural properties of the locked
formulas and the Youden-vs-profit comparison, but this remains
an empirical question for Future Work F6.

**Sensitivity coverage.** Not addressed; addressable by Future
Work F6 (multi-seed sweep of the entire pipeline).

### Limitation 10 — Bootstrap captures sampling uncertainty only

**Statement.** The Phase 4.1 1,000-resample bootstrap on the
64,027-row OOT economics population (Chapter 3 §3.6, Chapter
4 §4.4) quantifies *within-population sampling* uncertainty.
It does not capture (i) PD model uncertainty across
alternative hyperparameters, (ii) calibration drift across
cohorts beyond 202706, (iii) APR / LGD / cost-of-funds
assumption uncertainty, or (iv) formula-choice uncertainty
(constant versus declining hazard, lifetime versus
single-period, alternative discount factor conventions).

**Reference.** Chapter 3 §3.6 (bootstrap design and phrasing
rules); Chapter 4 §4.4 (bootstrap CI table and explicit
omitted-uncertainty list); Chapter 5 §5.4
(bootstrap-versus-assumption discipline).

**Scope of impact.** The bootstrap CIs in Table 4.6 are valid
estimates of the noise in the cut-off metrics that would
arise if the same locked pipeline were applied to a different
sample drawn from the same OOT population. They are *not*
estimates of the variance that would arise across alternative
PD models, alternative APR / LGD assumptions, or alternative
formula choices. Each of those uncertainty sources is
addressed by a different methodology element: multi-model PD
comparison (§4.1), multi-dimensional stress grids (§4.3,
§4.5, §4.6, §4.7), and the locked formula contract
(§3.4). The locked phrasing rules (§3.6, applied throughout
Chapters 4 and 5) prevent the bootstrap empirical frequencies
from being misread as true probabilities.

**Sensitivity coverage.** Sampling uncertainty fully
addressed by the bootstrap; assumption uncertainty addressed
by stress grids; model uncertainty partially addressed by the
multi-model comparison; cross-configuration uncertainty
deferred to Future Work F6.

---

## 6.2 Future Work

The Future Work catalogue below extends `thesis_limitations.md` and
the discussion of §5.6 with a single per-item brief that records the
research question, the limitation it addresses, the methodological
approach, an estimate of effort or compute cost, and a priority
ranking. The seven items are deliberately complementary: F1 and F4
strengthen the locked formulas with empirical inputs; F2, F6, and
F7 extend the empirical scope across data and configurations;
F3 addresses a specific simulator artefact; F5 calibrates the
exogenous APR assumption against real markets.

### F1 — Empirical LGD recovery from `transactions.csv`

**Research question.** Does the simulator's empirical post-default
LGD distribution fall within the {0.45, 0.55, 0.65, 0.75, 0.85}
sensitivity grid used in Chapters 3 and 4, and how would the
empirical distribution change the dollar uplift figures of §4.4?

**Addresses.** Limitation 4 (LGD as exogenous assumption).

**Approach.** For each `default_flag_12m == 1` aid in
`artifacts/final_data_800d_60m_p00/transactions.csv`, locate the
write-off period (the first month with `coll_status = 8`), sum the
subsequent `paid_installments × installment` recoveries (if any),
and compute LGD = max(0, (loan_amount − recovered) / loan_amount).
Aggregate the per-aid LGDs into a population distribution; compare
to the locked sensitivity grid; re-run the Phase 3.1B base economic
calculation with the empirical LGD distribution as input and report
the shift in mean Expected Profit and total portfolio profit.

**Effort estimate.** ~10-30 minutes compute on the existing
hardware, depending on memory and I/O bandwidth (transactions.csv
is 1.55 GB, 29M rows; the per-aid join is the dominant cost).
The new analysis requires no new artifacts beyond an additional
CSV summarising the empirical LGD distribution.

**Priority.** **High.** This is the cheapest Future Work item and
directly addresses one of the four exogenous-assumption
limitations. If the empirical LGD distribution is bimodal or
non-overlapping with the locked grid, additional sensitivity
points may need to be added; otherwise the existing locked grid
is validated against simulator-empirical evidence.

### F2 — Real-data replication

**Research question.** Do the four headline findings of Chapter 5
§5.1 — and particularly the PD-quality inversion of Finding 2 —
survive the transition from the synthetic simulator to a real
public consumer-credit dataset?

**Addresses.** Limitation 1 (synthetic data, not real-world data),
partially Limitation 8 (demographic over-determinism), partially
Limitation 9 (single simulator configuration).

**Approach.** Apply the full Chapter 3 methodology pipeline
(Phase 1.5 feature factory → Phase 2 dual-track PD modelling →
Phase 3 economic framework → Phase 4 stress testing and
bootstrap) to a real public credit dataset such as Lending Club,
Freddie Mac single-family, Bondora, or the Home Credit Default
Risk dataset on Kaggle. Test three specific hypotheses: (i) does
the cut-off gap widen as PD discrimination falls in real data as
it does in the simulator (§4.5), (ii) does the dollar uplift
remain positive across the real-data analogue of the tested
scenario space (§4.7), and (iii) does the reject-most regime
appear under realistic combinations of high operating cost and
adverse credit conditions (§4.6).

**Effort estimate.** Substantial — approximately one full
re-run of the analytical pipeline plus dataset-specific feature
engineering and target definition (typically 2-4 weeks of
focused effort per real dataset). Some adaptation is required
because real datasets may lack the tenor variation the
simulator provides; replication on a single tenor (e.g.,
36-month Lending Club originations) is the minimum-viable
target.

**Priority.** **High.** This is the most substantive scope
extension and the strongest test of whether the synthetic-data
methodology developed here generalises to production deployment.

### F3 — Alternative default definitions for 12-month loans

**Research question.** Can the structural zero-default artefact
on 12-month loans (Limitation 2) be addressed by an alternative
target definition that captures defaults at or before the
loan's terminal month rather than within the 13-24 month
forward window?

**Addresses.** Limitation 2 (12-month loans excluded).

**Approach.** Define and test three candidate alternative
default flags: (a) `default_flag_first_30dpd_within_term` (any
30+ days-past-due event before loan closure, regardless of
target window), (b)
`default_flag_writeoff_at_or_after_terminal` (include
write-offs at month 12 itself, extending the offset window to
[12, 23] inclusive of offset 12 for 12-month loans), and (c) a
discrete-time hazard target estimated from the per-month
delinquency state. Compare empirical default rates on
12-month loans under each alternative; assess whether any
alternative produces a non-trivial default rate that could
support including 12-month loans in the economic analysis.

**Effort estimate.** Moderate — approximately one week to
implement the alternative targets, re-run the wide-ABT build,
and re-fit the four base PD models on the alternative
populations. Compute is dominated by the wide-ABT regeneration
(~15 minutes per definition).

**Priority.** **Medium.** The 12-month exclusion is a clean
boundary condition for the current thesis and does not
undermine the headline findings; expanding to 12-month loans
would broaden the economic-analysis population and improve
external validity, but the marginal contribution is smaller
than F1 or F2.

### F4 — Declining-hazard alternative

**Research question.** How much of the dollar uplift figures
in §4.4 and §4.7 is attributable to the constant-hazard
assumption (Limitation 5) versus the underlying profit-vs-Youden
mechanism?

**Addresses.** Limitation 5 (constant-hazard assumption).

**Approach.** Fit a parametric declining-hazard schedule
(Weibull or log-logistic) to the simulator's per-month default
counts by loan age, using the writeoff events in
`transactions.csv`. Replace the constant `h` in the locked
LT_EL formula with the fitted declining-hazard schedule; re-run
Phase 3.1B base economics and Phase 4.1 bootstrap on the
chosen anchor scenarios; report the percentage shift in
dollar uplift attributable to the hazard substitution. The
expected qualitative outcome is that lifetime EL on 36-month
loans falls (because hazards decline after the first year). The
net effect on the profit-uplift metric — which depends on how the
hazard schedule reshapes both Youden's J and the profit-optimal
cut-offs — is an empirical question that this extension would
resolve.

**Effort estimate.** Moderate — approximately one week to fit
the hazard curve, re-implement the LT_EL formula with the
declining schedule, re-run the relevant Phase 3 and 4 cells,
and compare. Minimal new analysis beyond the existing
infrastructure.

**Priority.** **Medium.** The net effect of the constant-hazard
assumption on the profit-uplift metric is an empirical question
(Limitation 5 scope-of-impact note); the declining-hazard
extension would resolve it. Useful for quantifying the magnitude
reservation but not essential for the thesis's central claim.

### F5 — Market-calibrated APR tier validation

**Research question.** Does the thesis's profit-vs-Youden
finding survive recalibration of the locked APR tier table to a
specific real-market APR distribution?

**Addresses.** Limitation 3 (APR exogenous, not market-observed).

**Approach.** Survey published APR-by-PD-band data for a
specific market (US, EU, or emerging-market segments are
natural slices). Calibrate the tier table in Chapter 3 §3.4
Table 3.5 to the published market median (or to the most
representative published quantile by market segment). Re-run
the Phase 3.1B base economics, the Phase 3.2 576-cell stress
grid, and the Phase 4.1 bootstrap with the recalibrated tier
table; report the shift in the dollar uplift magnitude and
verify that the dollar-anchored claim survives in sign.

**Effort estimate.** Low-to-moderate — the survey of published
APR data is the dominant cost (typically 1-2 weeks for a
single market); the re-run of the locked pipeline with new APR
values is mostly automated (~1 hour compute).

**Priority.** **Medium-high.** APR is the second-largest
driver of the cut-off gap (Table 4.5), and a defensible
market-calibration would strengthen the thesis's external
validity claim materially.

### F6 — Multi-seed simulator robustness

**Research question.** Do the four headline findings survive
when the entire pipeline is re-run on multiple simulator seeds
and multiple `p_positive` levels?

**Addresses.** Limitation 9 (single simulator configuration).

**Approach.** Re-run the full Phase 1.5 through Phase 4.4
pipeline on at least five alternative seeds and at least three
alternative `p_positive` levels (e.g., {0.00, 0.02, 0.05}).
For each (seed × `p_positive`) configuration, record the
dollar uplift point estimate, the cut-off gap distribution
across the four anchors, and the anchor scenario
classification. Aggregate across configurations and report
cross-configuration variance for each headline finding. If
the variance is narrow (e.g., dollar uplift CIs that overlap
the single-seed CIs), the single-seed results are validated;
if the variance is wide, the thesis's quantitative claims
would need to be re-stated with widened uncertainty bands.

**Effort estimate.** Substantial — each pipeline rerun is
approximately 12-15 hours of compute (the simulator alone is
~13 hours), so a five-seed × three-`p_positive` sweep
requires approximately 200 hours of compute distributed
across the seeds. Analysis automation reduces the human
effort to approximately one week of orchestration and
reporting.

**Priority.** **Medium-low.** The single-seed limitation is
clearly documented and the qualitative findings are expected
to be robust across seeds (the locked formulas and the
Youden-vs-profit comparison are deterministic functions of
the calibrated PDs and the cost parameters). Multi-seed
robustness would tighten the empirical evidence but is not
required to defend the central claims.

### F7 — External validation via transfer scoring

**Research question.** Do the dual-track PD models trained on
simulator data retain meaningful discrimination, calibration,
and profit-vs-Youden behaviour when scored on a real public
dataset without re-fitting?

**Addresses.** Limitation 1 (synthetic data) in combination
with Limitation 6 (calibration mismatch).

**Approach.** Combine F2 and F6: take the locked LightGBM
tuned + Platt model from this thesis (saved at
`artifacts/pd_model/lightgbm_tuned_model.pkl`) and *score*
it on a real public dataset such as Lending Club, without
refitting. Measure (i) discrimination metrics on the real
data versus the synthetic OOT, (ii) calibration drift under
transfer (predicted-to-observed ratio on the real-data base
rate), and (iii) the profit-vs-Youden uplift on the
real-data analogue of the eco-OOT subset. Two outcomes are
informative: if the simulator-trained model retains
discrimination and the profit-vs-Youden finding holds, the
synthetic methodology has demonstrated transfer; if either
collapses, the synthetic methodology is locally valid but
not transferable, and the contribution is strictly
methodological rather than predictive. Where direct feature
overlap is not possible, the transfer experiment should be
interpreted as pipeline-level transfer rather than exact model
transfer; feature harmonisation or a shared reduced feature
set would be required.

**Effort estimate.** Substantial — combines F2 effort (real
dataset acquisition, feature mapping, target alignment) with
the additional complexity of feature-name reconciliation
between the simulator's columns and the real dataset's
columns. Approximately 4-6 weeks of focused effort per
real dataset.

**Priority.** **Medium.** This is the most ambitious Future
Work item but also the strongest test of external validity.
Most usefully attempted *after* F2 has been completed on
the chosen real dataset (so that the dataset preparation is
already in place).

---

## 6.3 Summary of Future Work prioritisation

| Item | Priority | Effort | Limitation(s) addressed |
|------|----------|--------|--------------------------|
| F1 — Empirical LGD recovery | **High** | ~10 min compute | 4 |
| F2 — Real-data replication | **High** | 2-4 weeks per dataset | 1 (full), 8 (partial), 9 (partial) |
| F3 — Alternative 12-month default definitions | Medium | ~1 week | 2 |
| F4 — Declining-hazard alternative | Medium | ~1 week | 5 |
| F5 — Market-calibrated APR tiers | Medium-high | 1-2 weeks survey + 1 hr compute | 3 |
| F6 — Multi-seed simulator robustness | Medium-low | ~200 hrs compute + 1 week orchestration | 9 |
| F7 — External validation via transfer scoring | Medium | 4-6 weeks per dataset, after F2 | 1 + 6 (combined) |

The two High-priority items (F1 empirical LGD and F2 real-data
replication) address the two most prominent limitations: the
exogenous LGD assumption and the synthetic-data origin. Together
they would cover the largest share of the boundary-condition
volume identified in §6.1 and would substantially strengthen the
external-validity claim that the thesis can make about its
findings.

---

## 6.4 Closing remark

The thesis's claims are deliberately modest in scope: profit-driven
cut-off selection produces strictly higher dollar Expected Profit
than Youden's J in 64 of 64 stress cells and 4,000 of 4,000
bootstrap × anchor combinations *within the tested scenario space*.
The boundary conditions enumerated in §6.1 constrain the scope of
that claim; the Future Work programme of §6.2 charts the path by
which subsequent research could extend it. Neither chapter aims to
diminish the thesis's findings — they aim to make explicit the
conditions under which those findings hold, so that subsequent work
can build on them with confidence in what is known and what
remains to be tested.
