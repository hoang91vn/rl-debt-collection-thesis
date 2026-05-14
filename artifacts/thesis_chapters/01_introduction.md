# Chapter 1 — Introduction

Lending is an economic decision. When a bank or credit institution
approves or rejects a loan application, it is committing capital
under uncertainty in pursuit of a margin: interest income
survival-weighted by repayment behaviour, net of expected loss,
funding cost, acquisition cost, and recurring operating expense.
The credit-scoring literature, however, has historically evaluated
borrower-risk models through *discrimination metrics* — the area
under the ROC curve (AUC), the Gini coefficient, the
Kolmogorov-Smirnov statistic — and through cut-off rules derived
from them, of which Youden's J statistic (the threshold maximising
True Positive Rate − False Positive Rate) is the canonical example.
Discrimination metrics measure how well a model *ranks* borrowers;
cut-off rules derived from them assume that the goal of the cut-off
is to balance a classification error trade-off rather than to
maximise an economic objective. The discrepancy between the
classification objective and the dollar-profit objective is the
starting point of this thesis.

The discrepancy matters because the loan-portfolio decision-maker
does not, in general, want to minimise misclassification rate. They
want to maximise expected dollar profit subject to whatever capital,
regulatory, or strategic constraints they face. A cut-off optimised
against profit can — and in practice does — sit at a different
threshold than the one optimised against TPR − FPR. Whether the gap
is large, small, positive, or negative depends on the joint
distribution of borrower-level risk, the pricing scheme, recovery
assumptions, and the cost stack. These dependencies are what
motivate the present thesis.

---

## 1.1 Motivation

The textbook profit-cut-off literature [TODO: cite Mays 2004;
Anderson 2007; Siddiqi 2017] treats profit-curve analysis as a
primary scorecard-validation tool and recommends profit-driven
cut-off selection over discrimination-driven cut-off selection on
principled grounds. The empirical evidence base for that
recommendation is, however, thin in two respects. First, the
published evidence typically rests on a single illustrative profit
curve drawn for a single representative cost regime, with limited
sensitivity analysis across the surrounding economic-assumption
space. Second, the published evidence rarely interrogates how the
profit-versus-discrimination gap behaves under stress: under
degraded PD signal informativeness, under elevated operating cost,
under alternative pricing schemes, or under joint stress on
multiple economic levers simultaneously.

The result is that practitioners adopting profit-driven cut-off
frameworks face several open questions:

- *Magnitude.* Is the dollar advantage of profit-driven over
  discrimination-driven cut-off selection substantial, or is it the
  kind of small refinement that can be safely ignored?
- *Robustness.* Does the advantage survive changes in pricing, loss
  given default, acquisition cost, funding cost, or operating cost?
  Or does the framework produce an advantage only in narrow corners
  of the assumption space?
- *PD-signal sensitivity.* Does the framework retain its advantage
  when the PD model is weaker — and if so, in which direction does
  the advantage move? Conventional intuition might suggest that
  better PD models are needed to extract economic value from cut-off
  optimisation; the question is whether that intuition holds up
  under controlled stress.
- *Adaptivity.* Does the framework collapse correctly when the
  economics genuinely break — when most accounts are loss-making
  after all costs — or does it produce nonsensical "approve
  everyone" recommendations regardless of the underlying conditions?
- *Comparability.* How much does it matter whether the profit metric
  is single-period or tenor-aware? On a portfolio mixing 24-month
  and 36-month loans, does the choice of formula systematically
  distort the cut-off recommendation?

These questions cannot be answered by a single profit-curve
illustration. They require a controlled empirical experiment in
which the relevant economic and PD-signal levers can be varied
independently and jointly, in which the locked formula stack and
the cut-off rule can be evaluated on the same population at every
stress point, and in which the within-sample noise of the dollar
uplift can be quantified separately from the assumption uncertainty.

This thesis conducts such an experiment on the synthetic
`rl-debt-collection` simulator. The synthetic-data choice is
methodological, not incidental: real public consumer-credit
datasets confound the profit-versus-discrimination question with
data-quality artefacts (missingness, censoring, reporting lag),
regulatory artefacts (disparate-impact constraints), and
proprietary-data artefacts (sample selection by the originator,
risk-based pricing already embedded in the data). The simulator
allows the methodology to be tested under known conditions —
controlled APR and LGD assumptions, and a known simulator
data-generating process — so that observed effects can be
attributed to the cut-off framework itself rather than to omitted
confounders. Replication on real data is the
priority direction in the Future Work catalogue (Chapter 6, F2 and
F7), not a substitute for the controlled experiment conducted here.

---

## 1.2 Research Question

The thesis is organised around a single main research question:

> *Under what conditions do profit-driven cut-offs outperform
> discrimination-driven cut-offs in expected dollar profit?*

The "under what conditions" framing is deliberate. The question is
not whether profit-driven cut-offs *ever* outperform
discrimination-driven cut-offs — that is established by the
textbook literature on principled grounds — but rather whether the
outperformance is robust across the joint space of economic
assumptions, PD-signal regimes, and operating cost levels that a
real institution would face.

The main question decomposes into four sub-questions, each of which
is addressed by a distinct phase of the empirical analysis reported
in Chapter 4:

1. *How do profit-driven cut-offs differ from Youden's J cut-offs
   in approval-rate and dollar-profit terms on the locked
   tenor-aware Lifetime Net Margin formula stack?* (Chapter 4 §4.2,
   §4.3, §4.4)
2. *How does PD signal informativeness affect the
   profit-versus-Youden cut-off gap?* (Chapter 4 §4.5)
3. *How sensitive are the optimal cut-offs to APR pricing strategy,
   LGD, acquisition cost, funding cost, and operating cost?*
   (Chapter 4 §4.3, §4.6)
4. *Does the tenor-aware Lifetime Net Margin framework materially
   differ from a simpler single-period benchmark, and if so, in
   which direction?* (Chapter 4 §4.2; Finding 4 in Chapter 5 §5.1)

Each sub-question is operationalised as one or more measurable
comparisons on the locked OOT economics population (n = 64,027 rows
of 24-month and 36-month loans; see Chapter 3 §3.4 for the
population derivation). The aggregate evidence base spans a 576-cell
economic stress grid (Chapter 4 §4.3), a 64-cell extended Phase 4.2
stress space (Chapter 4 §4.5, §4.6, §4.7), and a 1,000-resample × 4
anchor scenarios bootstrap (Chapter 4 §4.4).

---

## 1.3 Thesis Claim

The thesis's central empirical claim, refined in Chapter 4 §4.7
after the full evidence base was assembled, is:

> *Within the tested scenario space, profit-driven cut-offs strictly
> beat Youden's J in dollar terms, regardless of whether the
> profit-optimal cut-off is more or less permissive than Youden's
> in approval-rate terms.*

This is not claimed as a universal real-market law; it is an
empirical finding under the locked simulator (Chapter 3 §3.1), the
locked PD model (Chapter 3 §3.3, with the LightGBM tuned + Platt
model as primary), the locked Lifetime Net Margin formula stack
(Chapter 3 §3.4), and the explicit stress-test design (Chapter 3
§3.5) documented in Chapters 3 through 6.

Two qualifiers are essential. First, "strictly beat in dollar
terms" is the dollar-anchored form of the claim, deliberately
substituted for an earlier direction-anchored form
("profit-driven cut-offs are systematically more permissive than
Youden's") which the empirical evidence did not uniformly support.
The dollar-anchored form is supported by positive point-estimate
uplift in 64 of 64 stress cells of the Phase 4.2 design and by
positive uplift in 4,000 of 4,000 bootstrap × anchor combinations,
with per-anchor 95% CIs not crossing zero (Chapter 4 §4.4 and §4.7).

Second, *within the tested scenario space* is a strict boundary
condition, not a rhetorical flourish. The boundary conditions under
which the claim is valid are enumerated in Chapter 5 §5.5 and
treated formally as Limitations in Chapter 6 §6.1. The replication
directions that would extend the claim's scope — to real data, to
alternative simulator configurations, to declining-hazard
formulations, and to market-calibrated APR tier tables — are
catalogued as Future Work F1 through F7 in Chapter 6 §6.2.

---

## 1.4 Contributions

The thesis advances four contributions to the profit-driven credit
scoring literature.

**Contribution 1 — A tenor-aware Lifetime Net Margin framework for
cut-off optimisation.** Most published profit-cut-off analyses adopt
a single-period profit formula in which one period of interest is
collected from a non-defaulting borrower and one period of expected
loss is incurred on a defaulting borrower. The thesis adopts a
tenor-aware Lifetime Net Margin formula that survival-weights
revenue and expected loss across the full amortization schedule
(Chapter 3 §3.4; reference implementation in `src/economics.py`,
validated by nine identity and monotonicity unit tests in
`tests/test_economics.py`). The Phase 3.1B base economic comparison
(Chapter 4 §4.2) shows that the simpler Adjusted Single-period
Benchmark (ASB) understates the lifetime metric by approximately
40% on 36-month loans because amortization and survival weighting
are systematically ignored in the single-period form. The locked
formulas in `phase3_formula_lock.md` provide a reference
implementation against which subsequent tenor-aware studies can
compare.

**Contribution 2 — A multi-dimensional stress-test design.** The
bulk of published stress-testing analyses for retail credit profit
frameworks vary one or two parameters at a time [TODO: cite
Bellotti & Crook 2009; Verbraken et al. 2014]. The thesis instead
constructs a 576-cell economic stress grid crossing five dimensions
(PD multiplier, APR strategy, acquisition cost, LGD, cost of funds;
Chapter 4 §4.3) and a 64-cell extended Phase 4.2 stress space
crossing PD discrimination stress and operating cost (Chapter 4
§4.5, §4.6, §4.7). The design is motivated by the empirical finding
that the only reject-most regime in the entire 64-cell space
appears at the *simultaneous* extreme of all six stress dimensions
— a regime that no single-axis study would have detected. The
multi-dimensional design is therefore proposed not only as an
empirical apparatus but as a methodological contribution in its own
right: characterising the robustness of a cut-off framework
requires probing the joint stress space, not its marginal
projections.

**Contribution 3 — The PD-signal inversion finding.** The most
novel empirical contribution of the thesis is documented in
Chapter 4 §4.5: the cut-off gap between profit-driven and Youden's
J cut-offs *widens* monotonically as PD signal informativeness
falls — from approximately +15.5 percentage points at the LightGBM
raw Gini ≈ 0.80 to approximately +35.7 pp at Gini 0.30. The
mechanism is straightforward when stated: as the ROC curve
flattens, Youden's J-maximising threshold migrates inward (becomes
more conservative), while the profit-optimal threshold remains
anchored to the underlying economics. The two cut-offs therefore
separate as discrimination falls. The implication inverts an
implicit assumption pervasive in practical credit-risk discussions
— that better PD models are needed to derive value from
profit-driven cut-off optimisation. To the author's knowledge, this
inversion has not been explicitly reported in the published
profit-driven credit-scoring literature, and it is highlighted here
as the most novel of the four contributions.

**Contribution 4 — A bootstrap-versus-assumption uncertainty
discipline.** The thesis separates *sampling* uncertainty from
*assumption* uncertainty as a methodological practice. The Phase
4.1 1,000-resample stratified bootstrap on the OOT economics
population (Chapter 3 §3.6, Chapter 4 §4.4) quantifies sampling
uncertainty within a fixed locked pipeline. Assumption uncertainty
— variation across alternative APR / LGD / cost-of-funds
assumptions, alternative PD-signal regimes, alternative formula
choices — is addressed separately by the multi-dimensional stress
grids (Chapter 4 §4.3, §4.5, §4.6, §4.7). The discipline allows
each uncertainty source to be addressed by the appropriate
methodological tool and prevents the bootstrap CIs from being
misread as estimates of total uncertainty. Many published
profit-cut-off studies conflate these uncertainty sources,
typically by reporting a single point estimate with no
quantification of either; the separation is offered here as a
methodological practice that future work in the area can adopt.

The four contributions are deliberately positioned as overlapping
but distinct. Contribution 1 is a formula-stack contribution;
Contribution 2 is an experimental-design contribution; Contribution
3 is a substantive empirical finding; Contribution 4 is a
methodological discipline. The PD-signal inversion (Contribution 3)
is highlighted as the most novel because the literature gap it
addresses is the largest.

---

## 1.5 Methodology Overview

The empirical chain underlying the thesis claim is documented
formally in Chapter 3 and is summarised here for orientation.

**Data.** All empirical results derive from a single production run
of the synthetic `rl-debt-collection` simulator (Chapter 3 §3.1),
configured with seed 42, `p_positive = 0.00`, 800 clients per
simulation day, and a 60-month simulation window. The simulator
output is processed into a wide Application Behaviour Table (wide
ABT) by the locked build pipeline, producing 534,314 modelling rows
across all loan tenors (Chapter 3 §3.2). Loans with `n_installments
= 12` are excluded from the economic-analysis population because
the simulator's writeoff trigger is structurally unreachable within
the 12-month forward target window, leaving 235,968
economic-analysis rows (Chapter 3 §3.4). The OOT economics subset
for the bootstrap and stress analyses contains 64,027 rows of
24-month and 36-month loans with realised 12-month default-flag
observations.

**PD modelling.** The thesis uses a dual-track PD modelling design
(Chapter 3 §3.3): a tree-based gradient-boosted model (LightGBM
tuned + Platt scaling) as the primary PD source, complemented by a
Logistic Regression track on Lasso-selected features and a WoE
Scorecard for interpretability comparison. Calibration is performed
on a leak-free temporal slice (cohorts 202611-202612) using Platt
scaling. The under-prediction of the LightGBM Platt-calibrated mean
PD on the eco-OOT subset (predicted-to-observed ratio approximately
0.49) is documented as a calibration caveat and is bracketed by the
PD-multiplier stress scenarios used in Phase 3 and Phase 4.

**Economic framework.** The locked Lifetime Net Margin formula
stack (Chapter 3 §3.4) computes per-loan expected profit as the
survival-weighted lifetime margin minus the survival-weighted
lifetime expected loss, minus acquisition cost and recurring
operating cost. The five-tier risk-priced APR schedule maps PD
bands to APR values informed by published consumer-credit pricing
ranges; the LGD assumption is exogenous (0.65 base case, sensitivity
grid {0.45, 0.55, 0.65, 0.75, 0.85}) and is bracketed by Future
Work F1.

**Stress-test design.** The Phase 3.2 stress test (Chapter 3 §3.5)
constructs a 576-cell economic grid by crossing five dimensions:
PD multiplier, APR strategy, acquisition cost, LGD, and cost of
funds. The Phase 4.2 extended stress space adds 64 cells across
PD discrimination stress (PART A), operating cost (PART B), and
combined PD-signal × operating-cost stress (PART C), evaluated on
the same locked formulas and the same OOT subset.

**Bootstrap validation.** The Phase 4.1 bootstrap (Chapter 3 §3.6)
draws 1,000 stratified resamples from the 64,027-row OOT economics
population at each of four anchor scenarios (optimistic_base,
realistic_central_boundary, moderate_interior, adverse_stress),
producing 4,000 anchor × resample combinations. The bootstrap
quantifies sampling uncertainty within the OOT population only;
assumption uncertainty is addressed by the stress grids.

**Software architecture.** The pipeline is implemented in modular
Python in `src/` (Chapter 3 §3.7), with locked formula functions in
`src/economics.py`, calibration utilities in `src/calibration.py`,
and validation gates throughout. Ten Jupyter notebooks reproduce
the empirical chain end-to-end on the saved artefacts.

---

## 1.6 Findings Preview

The empirical chain produced four headline findings, summarised
here in compact form. Each is developed at length in Chapter 4
(empirical evidence) and Chapter 5 (synthesis and implications).

**Finding 1 — Profit-driven cut-offs strictly beat Youden's J in
dollar terms.** Across the 64 cells of the Phase 4.2 stress space,
the point-estimate dollar uplift from the profit-driven cut-off
relative to the Youden's J cut-off remained positive in every cell.
Across the 4,000 (anchor × bootstrap) combinations of the Phase 4.1
OOT bootstrap, the dollar uplift was likewise positive in every
combination, and the per-anchor 95% bootstrap CIs did not cross
zero in any of the four anchor scenarios (Chapter 4 §4.4 and §4.7).
The dollar magnitude of the advantage ranges from approximately
$0.46M at the adverse_stress anchor to approximately $30.75M at
the optimistic_base anchor on the OOT economics population.

**Finding 2 — The cut-off gap widens as the PD signal weakens.**
The Phase 4.2 PART A study (Chapter 4 §4.5) perturbed the LightGBM
Platt PD to target Ginis of 0.30, 0.45, and 0.60 and observed that
the mean cut-off gap widens monotonically as Gini falls — from
approximately +15.5 percentage points at the LightGBM raw Gini ≈
0.80 to approximately +35.7 pp at Gini 0.30. The mechanism is the
inward migration of Youden's J as the ROC flattens, while the
profit-optimal cut-off remains anchored to the underlying
economics. Within the tested scenario space, the approval-rate
gap between the profit-driven and Youden cut-offs is largest where
the underlying PD signal is weakest; this suggests a larger
strategic opportunity, although relative dollar uplift for the
PD-signal sub-grid is not directly tabulated.

**Finding 3 — The framework adapts to severe stress.** The Phase
4.2 PART B and PART C operating-cost robustness studies (Chapter 4
§4.6 and §4.7) identified one cell in the entire 64-cell stress
space — adverse_stress at op_cost = 0.04 — in which the
profit-optimal approval rate collapses to 0.31% with mean
per-account profit of −$387 and total portfolio profit of −$24.8M.
The existence of this single reject-most cell is interpretively
important: a framework that prescribed "approve more than Youden"
under all conditions would be either trivial or suspect. The
reject-most cell shows that the framework can and does prescribe
near-rejection at the simultaneous extreme of all six stress
dimensions, and is therefore an adaptive optimisation rule rather
than a one-sided "approve-all" recommendation.

**Finding 4 — The tenor-aware Lifetime Net Margin formula
outperforms ASB by approximately 40% on 36-month loans.** The
Phase 3.1B base economic comparison (Chapter 4 §4.2) showed that
the locked Lifetime Net Margin total of approximately $352.3M on
the 235,968-row economics-eligible population exceeds the simpler
ASB total of approximately $250.9M; the ASB-to-Lifetime ratio is
0.91 on 24-month loans and 0.60 on 36-month loans. The structural
mechanism is that ASB ignores both amortization and survival
weighting, while the Lifetime formula applies declining-balance
interest over the full loan life and survival-weights every period.
The implication is that any cut-off optimisation conducted on a
single-period profit metric will systematically under-weight
long-tenor loans by an arithmetic property of the formula rather
than by an economic property of the portfolio.

The empirical wording rules used throughout Chapters 4 and 5 are
observed in the previews above. Stress-cell uplifts are described
in *point-estimate* form because the per-cell bootstrap CIs were
not computed (only the four anchor-level bootstraps were run);
bootstrap-anchor uplifts are described as *per-anchor 95% CIs did
not cross zero* because that is the precise empirical statement
supported by Phase 4.1.

---

## 1.7 Thesis Structure

The remainder of the thesis is organised as follows.

**Chapter 2 — Literature Review.** A focused review of the
credit-scoring literature, organised around the four bodies of
work that the thesis intersects: (i) discrimination-driven cut-off
selection and the Youden's J family, (ii) profit-driven cut-off
selection and the textbook profit-curve tradition, (iii) lifetime
expected loss measurement and IFRS 9 staging, and (iv) stress
testing methodology in retail credit. The review locates the
thesis's contributions against existing work and identifies the
literature gaps that the thesis addresses (notably the gap that
motivates Contribution 3).

**Chapter 3 — Methodology.** The complete methodological
documentation of the empirical chain: data generation (§3.1),
feature engineering and the wide ABT build (§3.2), dual-track PD
modelling and calibration (§3.3), the locked Lifetime Net Margin
economic framework including APR scheme, LGD assumption, and
locked formulas (§3.4), the multi-dimensional stress-test design
(§3.5), the bootstrap validation design and locked phrasing rules
(§3.6), and the software architecture (§3.7).

**Chapter 4 — Results.** The empirical evidence supporting the
four headline findings: multi-model PD comparison and validation
gates (§4.1), Phase 3.1B base economics on the 235,968-row
population (§4.2), Phase 3.2 576-cell economic stress grid (§4.3),
Phase 4.1 bootstrap CIs across the four anchor scenarios (§4.4),
Phase 4.2 PART A PD-signal stress study (§4.5), Phase 4.2 PART B
operating-cost robustness study (§4.6), and Phase 4.2 PART C
combined Gini × operating-cost grid plus the refined dollar-anchored
thesis claim (§4.7).

**Chapter 5 — Discussion.** The synthesis of the four headline
findings (§5.1) into substantive contributions: implications for
credit risk practice (§5.2), positioning against the existing
literature (§5.3), reflection on the methodological design choices
including synthetic data, multi-dimensional stress, bootstrap
discipline, and validation gates (§5.4), boundary conditions
limiting the scope of the findings (§5.5), and future research
directions (§5.6).

**Chapter 6 — Limitations and Future Work.** The formal
limitations catalogue (10 limitations, each with statement,
reference, scope of impact, and sensitivity coverage; §6.1) and
the Future Work catalogue (7 directions F1 through F7, each with
research question, addressed limitation, approach, effort estimate,
and priority; §6.2).

The empirical core of the argument is concentrated in Chapters 3
and 4; the substantive contribution is articulated in Chapter 5;
the boundary conditions and the research extensions are catalogued
in Chapter 6. A reader interested in the central claim and its
empirical support can read Chapter 4 §4.7 directly with reference
to the locked methodology of Chapter 3 §§3.4-§3.6. A reader
interested in the methodological discipline and the boundary
conditions should additionally read Chapter 5 §5.4-§5.5 and
Chapter 6 §6.1 in full.
