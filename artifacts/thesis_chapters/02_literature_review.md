# Chapter 2 — Literature Review

This chapter situates the thesis against the existing credit-scoring
literature. It covers six bodies of work — discrimination-driven
cut-off selection, profit-driven cut-off selection, lifetime
expected loss measurement and IFRS 9 staging, stress testing
methodology in retail credit, PD modelling and calibration, and
synthetic-data methodology — and concludes with an explicit summary
of the literature gaps that the thesis addresses.

The chapter is deliberately a positioning chapter, not a
data-presentation chapter: empirical evidence is documented in
Chapter 4 and synthesised in Chapter 5, while this chapter
restricts itself to the prior literature and to how the present
thesis responds to identified gaps. Citations are flagged as
`[TODO: cite]` placeholders throughout; the citation map will be
finalised before submission. Each section ends with an explicit
statement of the thesis's response to the gap identified in that
strand of the literature.

---

## 2.1 Discrimination-driven cut-off selection

Credit scoring as a quantitative discipline has been dominated for
several decades by *discrimination metrics* — measures of how well
a borrower-risk model separates defaulters from non-defaulters in a
probabilistic sense, without regard to the economic consequences of
acting on the model's outputs.

The canonical discrimination metric in modern practice is the area
under the Receiver Operating Characteristic curve (AUC), which
equals the probability that a randomly chosen positive case
(default) is assigned a higher score than a randomly chosen
negative case (non-default) [TODO: cite Fawcett 2006 "An
introduction to ROC analysis"]. The AUC is monotonically related to
the Gini coefficient via Gini = 2·AUC − 1, so the two metrics
measure the same underlying quality and are interchangeable up to a
linear transform [TODO: cite Hand & Till 2001]. The
Kolmogorov-Smirnov statistic, defined as the maximum absolute
difference between the cumulative distribution functions of scores
for defaulters and non-defaulters, is a third widely used
discrimination metric in the credit-scoring tradition [TODO: cite
KS treatment in Siddiqi 2017 or Anderson 2007].

Discrimination metrics support cut-off selection through derived
rules. The Youden's J statistic [TODO: cite Youden 1950 "Index for
rating diagnostic tests"] is the canonical example: J = TPR − FPR,
and the cut-off that maximises J is the threshold on the score that
delivers the largest absolute separation between true-positive and
false-positive rates. Youden's J was introduced in a
clinical-diagnostics context and has since been widely adopted in
credit scoring for its simplicity and its appearance of an
"optimal" trade-off between the two error types.

Discrimination metrics dominated the credit-scoring evaluation
literature for several reasons. First, discrimination metrics are
model-property measures: they depend only on the score and the
realised label, not on any economic assumption about cost or
revenue. They are therefore robust to changes in the cost regime
that the lender faces and can be reported in textbook examples
without requiring any cost-side assumptions. Second, discrimination
metrics generalise across portfolios with different default rates
and different sample sizes — useful properties for benchmarking
model families across institutional contexts. Third, the
discrimination tradition predates the cost-sensitive learning
literature [TODO: cite Elkan 2001 "The foundations of cost-sensitive
learning"] by several decades and is more deeply embedded in
practitioner training and regulatory model-validation conventions.

The limitations of discrimination-only evaluation have, however,
been recognised in the literature for at least two decades [TODO:
cite Hand 2009 "Measuring classifier performance: a coherent
alternative to the area under the ROC curve"]. Hand (2009) in
particular argued that the AUC implicitly weights different
misclassification costs in a way that depends on the score
distribution, so the same AUC value can correspond to materially
different expected costs depending on the underlying loss function.
Cut-off rules derived from discrimination metrics inherit the same
limitation: Youden's J implicitly assumes that the cost of a false
positive equals the cost of a false negative, which is rarely true
in lending, where the cost of a defaulted loan typically dominates
the foregone-margin cost of a wrongly rejected good loan.

**Thesis response.** The thesis takes the limitations of
discrimination-only evaluation as its starting point. Discrimination
metrics remain useful as model-quality summaries (and are reported
in Chapter 4 §4.1 alongside calibration metrics), but they are not
adopted as the cut-off optimisation objective. Cut-off selection is
performed against a tenor-aware Lifetime Net Margin objective
documented in Chapter 3 §3.4, with Youden's J retained throughout
as a discrimination-driven *benchmark* against which the
profit-driven cut-off is compared. The empirical comparison of the
two cut-off rules is the central evidence base of Chapter 4.

---

## 2.2 Profit-driven cut-off selection

The profit-driven alternative to discrimination-driven cut-off
selection has a continuous tradition in the credit-scoring textbook
literature. Mays (2004) [TODO: cite Mays "Credit Scoring for Risk
Managers"] devotes a chapter to profit-curve analysis as a primary
scorecard-validation tool, recommending that profit-optimised
cut-offs replace discrimination-optimised cut-offs in production
scoring systems. Anderson (2007) [TODO: cite Anderson "The Credit
Scoring Toolkit"] develops the methodology in more depth, with
detailed treatment of revenue, cost, and recovery components in the
profit calculation. Siddiqi (2017) [TODO: cite Siddiqi "Intelligent
Credit Scoring"] extends the framework to risk-based pricing
portfolios and explicitly recommends profit-based cut-off selection
over discrimination-based selection for institutions whose APR
varies systematically with PD band.

In industry practice, profit-curve analysis is widely used at the
model-validation stage of scorecard deployment, both as a sanity
check on the discrimination-derived cut-off and as an internal
governance instrument when the discrimination-driven and the
profit-driven cut-offs disagree by a material margin. The textbook
literature treats the profit-cut-off as a principled improvement on
the Youden's J cut-off; the case for it usually rests on a single
illustrative profit curve demonstrating that the profit-optimal
threshold differs from the J-optimal threshold and that the
area-under-profit-curve under the profit-optimal threshold is
larger.

The published evidence base for profit-driven cut-off selection
has, however, three notable gaps. First, the published evidence
typically rests on a single illustrative profit curve drawn for a
single representative cost regime, with limited sensitivity
analysis across the surrounding economic-assumption space. Second,
the published evidence rarely interrogates how the
profit-versus-discrimination gap behaves under stress on the
PD-signal side: most published profit curves are drawn at a fixed
PD-signal discrimination level, and the question of how the profit
advantage changes if the PD signal is weaker or stronger is rarely
addressed empirically. Third, the published evidence rarely
separates *sampling* uncertainty (how much the empirical
profit-uplift estimate would vary across alternative samples drawn
from the same population) from *assumption* uncertainty (how much
the estimate would vary across alternative cost / pricing /
recovery assumptions), so the reader is left without a precise
reading of what the reported point estimate means.

A second strand of profit-driven cut-off literature focuses on
single-period versus lifetime profit formulations. The textbook
treatments above implicitly use a single-period profit formula in
which one period of interest is collected from a non-defaulting
borrower and one period of expected loss is incurred on a
defaulting borrower. More recent work in tenor-aware credit-risk
modelling has emphasised that this single-period approximation
systematically under-weights longer-tenor loans because amortization
and survival weighting are ignored [TODO: cite tenor-aware credit
risk literature, e.g., Krüger & Rösch 2017 or Bellini 2019]. The
transition from single-period to lifetime profit formulations is
the formal counterpart to the IFRS 9 lifetime-ECL transition
discussed in §2.3 below.

A third strand approaches the profit-versus-discrimination question
through cost-sensitive evaluation metrics. The Expected Maximum
Profit (EMP) framework of Verbraken et al. (2014) [TODO: cite
Verbraken, Verbeke & Baesens 2014 "Expected Maximum Profit
framework"] integrates over a probability distribution of cost
parameters to produce a single scalar metric that ranks classifiers
by their expected profitability under cost uncertainty. The EMP
framework is conceptually adjacent to the profit-driven cut-off
framework in this thesis but uses a different operationalisation:
EMP marginalises out the cost parameters, while the thesis here
holds the cost parameters explicit and evaluates the framework on a
discrete grid that spans the assumption space. The two
operationalisations answer different questions and are
complementary rather than substitutes.

**Thesis response.** The thesis responds to all three published-
evidence gaps. The single-illustrative-cell limitation is addressed
by the 576-cell economic stress grid (Chapter 4 §4.3) and the
64-cell extended Phase 4.2 stress space (Chapter 4 §4.5, §4.6,
§4.7). The PD-signal sensitivity gap is addressed by the Phase 4.2
PART A study (Chapter 4 §4.5), which produces the PD-signal
inversion finding documented as Contribution 3 in Chapter 1 §1.4.
The sampling-versus-assumption uncertainty gap is addressed by the
bootstrap-versus-assumption discipline of Contribution 4: the
Phase 4.1 1,000-resample bootstrap (Chapter 4 §4.4) quantifies
sampling uncertainty within the OOT economics population, and the
multi-dimensional stress grids quantify assumption uncertainty
separately. The single-period versus lifetime distinction is
addressed by Contribution 1 — the tenor-aware Lifetime Net Margin
formula stack (Chapter 3 §3.4) — with empirical evidence of the
magnitude of the single-period bias documented in Chapter 4 §4.2.

---

## 2.3 Lifetime Expected Loss and IFRS 9

Lifetime Expected Loss (ECL) measurement entered the regulatory
mainstream through the IFRS 9 financial reporting standard, which
replaced the incurred-loss model of IAS 39 with an expected-loss
model effective from 2018 [TODO: cite IFRS 9 standard; Beerbaum
2015 "Significant Increase in Credit Risk under IFRS 9"]. Under
IFRS 9, lifetime ECL must be recognised on Stage 2 and Stage 3
financial assets, defined respectively as assets with significantly
increased credit risk since origination and assets that are
credit-impaired. The standard form of the lifetime-ECL formula is:

> LT_EL = Σ_t marginal_PD_t · LGD · EAD_t · discount_t

where the sum runs over the remaining life of the asset,
`marginal_PD_t` is the conditional probability of default in period
t given survival up to period t, `EAD_t` is the exposure at default
in period t, `LGD` is the loss given default, and `discount_t` is
the period-t discount factor.

The IFRS 9 standard has produced a substantial implementation
literature in retail credit modelling [TODO: cite Krüger, Rösch &
Scheule 2018 IFRS 9 implementation; PwC 2017 IFRS 9 implementation
guidance; Skoglund 2017 "Implementing Credit Risk Models for IFRS
9"]. The literature emphasises three implementation challenges.
First, the marginal PD term requires a tenor-aware PD model that
produces conditional default probabilities for every period of the
loan's remaining life, not just a single 12-month forward PD.
Second, the LGD term must reflect post-default recovery behaviour
over the loss-period, which in unsecured consumer credit typically
requires a recovery curve fit to historical workout data. Third,
the discount factor must be consistent across the lifetime PD, the
LGD, and the EAD components, with the effective interest rate at
origination being the IFRS 9-conventional choice.

A parallel literature on LGD modelling in unsecured consumer credit
[TODO: cite Schuermann 2004 "What do we know about loss given
default?"; Bellotti & Crook 2012 LGD models for unsecured consumer
credit] documents the empirical difficulties of estimating LGD from
post-default recovery data: censoring of the workout period,
heterogeneity across borrower segments, and the strong influence of
collection-policy design on realised recoveries. Most published
profit-curve analyses sidestep these difficulties by adopting a
fixed exogenous LGD assumption, a practice this thesis follows.

**Thesis response.** The thesis adopts a tenor-aware Lifetime Net
Margin formula stack (Chapter 3 §3.4) that is structurally
compatible with IFRS 9 lifetime-ECL conventions: the lifetime
expected loss component uses the same `Σ_t marginal_PD_t · LGD ·
EAD_t · discount_t` form. The marginal PDs are derived from the
LightGBM Platt-calibrated 12-month forward PD via the constant-
hazard extrapolation `h = 1 − (1 − PD₁₂ₘ)^(1/12)`, an explicit
simplification documented as Limitation 5 in Chapter 6 §6.1 with
the declining-hazard alternative catalogued as Future Work F4. The
EAD curve is derived from the locked amortization schedule for each
loan tenor, and the discount factor uses the locked discount-rate
convention. The LGD assumption is exogenous (0.65 base case,
sensitivity grid {0.45, 0.55, 0.65, 0.75, 0.85}) rather than
empirically calibrated against the simulator's transaction trace;
empirical LGD recovery is catalogued as Future Work F1 in
Chapter 6 §6.2. The thesis applies the lifetime-ECL formula stack
to *cut-off optimisation* rather than to *provisioning*, but the
unification of the two uses on the same locked formula stack is a
small methodological contribution: the same implementation in
`src/economics.py` could in principle support both the cut-off
optimisation reported in Chapter 4 and a Stage 2/3 provisioning
calculation under IFRS 9, although the thesis does not exercise the
second use.

---

## 2.4 Stress testing methodology in retail credit

Stress testing in retail credit risk is a long-established
practice, both for regulatory capital purposes (Basel II/III stress
tests, CCAR/DFAST in the United States, EBA stress tests in Europe)
[TODO: cite Basel stress-testing principles BCBS 2018; CCAR/DFAST
methodology; EBA stress test methodology] and for internal
portfolio management. The published academic and practitioner
literature on retail-credit stress testing has, however, two
dominant tendencies that limit its applicability to profit-driven
cut-off selection.

First, most published stress-testing analyses vary one or two
parameters at a time [TODO: cite Bellotti & Crook 2009 "Credit
scoring with macroeconomic variables using survival analysis";
Verbraken, Verbeke & Baesens 2014]. Single-axis sensitivity is the
dominant pattern: the analyst varies the macroeconomic stress
driver (GDP growth, unemployment rate, house price index) while
holding the model and the cost stack fixed, or varies the LGD
assumption while holding the PD and the macroeconomic inputs fixed.
Joint stress on multiple axes simultaneously is rare in published
profit-curve analyses, and the consequence is that joint-extreme
behaviours — which can be qualitatively different from the
marginal-extreme behaviours — are systematically under-detected.

Second, cost-sensitive learning [TODO: cite Elkan 2001] and
cost-sensitive evaluation [TODO: cite Verbraken et al. 2014 EMP
framework] have produced a parallel literature on incorporating
asymmetric misclassification costs into model training and
evaluation. The Expected Maximum Profit (EMP) framework, discussed
in §2.2 above, is the canonical cost-sensitive evaluation metric in
the credit-scoring literature; it is conceptually adjacent to the
multi-dimensional stress design adopted in this thesis but uses a
different operationalisation as noted earlier.

Simulation-based credit-risk methodology [TODO: cite Bohn & Stein
2009 "Active Credit Portfolio Management in Practice"; Allen &
Saunders 2003 retail-credit simulation review] forms a third strand
of relevant literature. Simulation has been used to quantify the
impact of correlated defaults on portfolio loss distributions, to
evaluate stress-testing assumptions under controlled conditions,
and to back-test risk models on hypothetical adverse scenarios.
The use of simulation in this thesis is methodological in the same
spirit: the synthetic `rl-debt-collection` simulator allows the
methodology to be tested under controlled APR and LGD assumptions
and a known data-generating process, so that observed effects can
be attributed to the cut-off framework itself rather than to
omitted real-data confounders.

**Thesis response.** The thesis's contribution in this strand is
the multi-dimensional stress design, which crosses six dimensions
(PD multiplier, APR strategy, acquisition cost, LGD, cost of funds,
and operating cost) in the Phase 4.2 extended stress space
(Chapter 4 §4.5, §4.6, §4.7). The empirical motivation for the
multi-dimensional design is the finding that the only reject-most
regime in the entire 64-cell stress space appears at the
*simultaneous* extreme of all six dimensions — a regime that no
single-axis study would have detected. Single-axis sensitivity is
therefore positioned in this thesis as insufficient for
characterising the robustness of a cut-off framework, and the
multi-dimensional approach is offered as the methodological
alternative (Contribution 2 in Chapter 1 §1.4).

---

## 2.5 PD modelling and calibration

PD modelling for retail credit has historically been dominated by
logistic-regression scorecards [TODO: cite Thomas, Edelman & Crook
2002 "Credit Scoring and its Applications"; Siddiqi 2006/2017
scorecard development]. The classical workflow combines
weight-of-evidence (WoE) feature transformation, information-value
variable screening, lasso or stepwise variable selection, and
logistic-regression coefficient estimation, with the final score
scaled to a points-and-points-to-double-the-odds (PDO) format for
human interpretability. The WoE-and-scorecard tradition remains the
dominant choice in regulated banking environments because of its
transparency and ease of model documentation under Basel II/III
model-risk-management standards.

A parallel strand of the literature has documented the empirical
advantages of gradient-boosted machine-learning models over
logistic regression for credit-risk prediction. LightGBM [TODO:
cite Ke et al. 2017 "LightGBM: A Highly Efficient Gradient Boosting
Decision Tree"] and XGBoost [TODO: cite Chen & Guestrin 2016
"XGBoost: A Scalable Tree Boosting System"] are the two most widely
deployed gradient-boosted frameworks in production credit scoring;
both consistently outperform logistic-regression scorecards on
discrimination metrics by a measurable margin in published
benchmarks [TODO: cite credit-risk LightGBM-versus-LR empirical
comparisons]. Hyperparameter optimisation for the gradient-boosted
track is typically performed with a Bayesian-optimisation framework
such as Optuna [TODO: cite Akiba et al. 2019 "Optuna: A
Next-generation Hyperparameter Optimization Framework"].

A third literature distinguishes *discrimination* from
*calibration*. Discrimination, as discussed in §2.1, measures how
well the model ranks borrowers; calibration measures how closely
the model's predicted PDs match the empirical default frequencies
in equally-binned score ranges [TODO: cite Niculescu-Mizil & Caruana
2005 "Predicting Good Probabilities with Supervised Learning"]. A
model can have high discrimination but poor calibration, or vice
versa, and the two qualities are required for different downstream
uses. Discrimination matters most for ranking-based decisions
(which borrowers to approve first); calibration matters most for
absolute-probability-based decisions (what dollar provision to set
against an account, what dollar profit to expect from approving an
account). The thesis's profit-driven cut-off optimisation depends
on calibrated PDs because the lifetime EL component of the profit
formula multiplies absolute PD against LGD and EAD; un-calibrated
PDs would distort the per-account expected-profit estimates and
bias the cut-off optimum.

Two calibration techniques are well-established in the credit-risk
literature. Platt scaling [TODO: cite Platt 1999 "Probabilistic
Outputs for Support Vector Machines"] fits a logistic regression of
the binary outcome on the model's raw score, producing a parametric
monotonic transformation from raw scores to calibrated
probabilities. Isotonic regression [TODO: cite Zadrozny & Elkan
2002 "Transforming classifier scores into accurate multi-class
probability estimates"] fits a non-parametric monotonic
transformation. Platt is the more widely used choice in production
credit-risk pipelines because it requires fewer parameters and is
less prone to overfitting on small calibration samples.

**Thesis response.** The thesis's PD modelling and calibration
design (Chapter 3 §3.3) is dual-track: a tree-based gradient-
boosted model (LightGBM tuned with Optuna and Platt-calibrated on a
leak-free temporal slice) serves as the primary PD source,
complemented by a Logistic Regression track on Lasso-selected
features and a WoE Scorecard for interpretability comparison. The
dual-track design is a deliberate response to the literature's
split between modern-ML and classical-scorecard practice: by
maintaining both tracks throughout the empirical chain, the thesis
can compare the cut-off behaviour produced by the two paradigms on
the same locked economic framework. The discrimination-versus-
calibration distinction is also operationalised in the empirical
chain: Chapter 4 §4.1 reports both discrimination metrics (Gini,
AUC, KS) and calibration summaries (notably the predicted-to-
observed ratio on the eco-OOT subset) for every PD model, and the
LightGBM under-prediction on the eco-OOT subset (predicted-to-
observed ratio approximately 0.49,
documented as Limitation 6 in Chapter 6 §6.1) is identified
precisely because the calibration discipline distinguishes a
discrimination outcome from a calibration outcome.

---

## 2.6 Synthetic data for methodological research

The use of synthetic data for methodological research in credit
risk is uncommon in the academic credit-scoring literature but has
antecedents in adjacent quantitative-finance and machine-learning
fields. Synthetic data generation is the dominant evaluation
strategy in domains where real data is restricted by privacy
regulation, by competitive sensitivity, or by physical
impossibility — the canonical examples are healthcare (HIPAA-
restricted patient data) [TODO: cite Patki et al. 2016 "The
Synthetic Data Vault"; Choi et al. 2017 medGAN] and high-frequency
finance (proprietary order-book data) [TODO: cite Buehler et al.
2020 synthetic order-book generators].

In credit-scoring, synthetic-data methodology has been used most
often to evaluate fair-lending interventions or to stress-test
scoring algorithms against rare adverse scenarios that real data
does not contain [TODO: cite synthetic-data fair-lending literature,
e.g., Hardt, Price & Srebro 2016 or Bellamy et al. 2018 IBM AIF360].
Public real-data alternatives — Lending Club, Freddie Mac
single-family, Bondora, the Home Credit Default Risk dataset on
Kaggle — are widely used for academic profit-curve and stress-
testing research and have the advantage of being directly
comparable to real production lending. They have, however, four
well-documented limitations that motivate the synthetic-data choice
in this thesis.

First, *sample selection*: every public credit dataset is
conditioned on the originator's approval policy at the time of
origination. The dataset therefore reflects only borrowers the
originator was willing to approve, not the full applicant
population. The cut-off optimisation question — what should the
optimal threshold be on the *applicant* population, including
borrowers the originator rejected — is structurally hard to answer
on a sample-selected dataset without reject-inference techniques
whose own assumptions are difficult to validate [TODO: cite
reject-inference literature, e.g., Crook & Banasik 2004].

Second, *embedded pricing*: in risk-based pricing portfolios such
as Lending Club, the APR charged on each loan is itself a function
of the borrower's risk score at origination. The APR distribution
in the data is therefore endogenous to the originator's pricing
policy, and any cut-off optimisation that uses the realised APRs
reproduces the originator's pricing rather than testing alternative
pricing schemes. Disentangling the cut-off question from the
pricing question on real risk-priced data is methodologically
delicate.

Third, *missingness and censoring*: real public credit datasets
typically suffer from systematic missingness (borrowers whose loans
were paid early appear differently in the data than borrowers
whose loans defaulted late) and censoring (loans whose terms have
not yet completed are right-censored on the default indicator).
Both phenomena complicate the construction of a clean default flag
and the comparison of profit estimates across loans with different
observed loan-life durations.

Fourth, *product heterogeneity*: real-data portfolios mix loan
products with different terms, amortization structures, and pricing
tiers. A profit-curve analysis on a heterogeneous portfolio is
inherently a weighted average over the product mix, and the analyst
rarely has the per-product transparency required to disaggregate
the result.

The synthetic `rl-debt-collection` simulator used in this thesis
bypasses all four limitations by construction: the simulator
generates the full applicant population (including rejected
applicants in the underlying data-generating process), the APR is
supplied as an exogenous methodological assumption rather than
embedded in the data, the default flag is fully observed within the
simulation horizon, and the loan products are configurable by the
analyst. The synthetic-data choice does not, however, claim
realism: the simulator approximates but does not replicate any
specific institution's data-generating process, and the methodology
validated under controlled conditions on synthetic data may not
transfer numerically to any specific real portfolio.

**Thesis response.** The thesis is explicit that the synthetic-data
choice does not eliminate the need for real-data replication — it
enables it. The Future Work catalogue (Chapter 6 §6.2) prioritises
real-data replication (F2) and external validation via transfer
scoring (F7) as the most substantive scope-extension directions,
precisely because the synthetic-data methodology developed here
will only achieve full external validity when its findings are
demonstrated to survive the transition to real data. The boundary
condition that the empirical claim holds *within the tested
scenario space* (Chapter 4 §4.7) is enforced consistently in
Chapters 4 through 6 to prevent any over-generalisation of the
synthetic-data finding to real-market behaviour.

---

## 2.7 Summary of literature gap and thesis positioning

The six literature strands above identify five overlapping gaps in
the published credit-scoring research. Each gap is addressed by one
or more of the four thesis contributions enumerated in
Chapter 1 §1.4.

**Gap 1 — Limited multi-dimensional stress evidence.** The
published profit-cut-off literature (§2.2) typically reports
single-cell or single-axis profit-curve analyses, and the published
stress-testing literature (§2.4) varies one or two parameters at a
time. The thesis responds with the 576-cell economic stress grid
(Chapter 4 §4.3) and the 64-cell extended Phase 4.2 stress space
(Chapter 4 §4.5, §4.6, §4.7), addressed by **Contribution 2** (the
multi-dimensional stress-test design).

**Gap 2 — Limited PD-signal sensitivity evidence.** The published
profit-cut-off literature rarely interrogates how the
profit-versus-discrimination gap behaves when the PD signal is
weaker (§2.2). The thesis responds with the Phase 4.2 PART A
PD-signal stress study (Chapter 4 §4.5), which produces the
PD-signal inversion finding documented as Finding 2 in
Chapter 5 §5.1, addressed by **Contribution 3** (the PD-signal
inversion finding, highlighted in Chapter 1 §1.4 as the most novel
of the four contributions).

**Gap 3 — Limited statistical-uncertainty quantification.** The
published profit-cut-off literature rarely separates sampling
uncertainty from assumption uncertainty (§2.2), and most published
profit-curve analyses report point estimates with no uncertainty
quantification. The thesis responds with the bootstrap-versus-
assumption discipline (Chapter 1 §1.4 Contribution 4): the
Phase 4.1 1,000-resample bootstrap (Chapter 4 §4.4) for sampling
uncertainty within the OOT economics population, and the
multi-dimensional stress grids for assumption uncertainty.

**Gap 4 — Limited tenor-aware lifetime-framework adoption.** The
published profit-cut-off literature typically uses single-period
profit formulas that systematically under-weight long-tenor loans
by ignoring amortization and survival weighting (§2.2 and §2.3).
The thesis responds with a tenor-aware Lifetime Net Margin formula
stack (Chapter 3 §3.4) that survival-weights revenue and expected
loss over the full amortization schedule, addressed by
**Contribution 1**, with empirical evidence of the magnitude of the
single-period bias documented in Chapter 4 §4.2 (Finding 4).

**Gap 5 — Confound between methodology and real-data artefacts.**
The published profit-cut-off literature is split between studies on
real public datasets (which suffer from sample selection, embedded
pricing, missingness, and product heterogeneity confounds; §2.6)
and studies on illustrative simulated examples (which lack the
empirical scale needed to characterise robustness; §2.4). The
thesis responds with a controlled empirical experiment on the
synthetic `rl-debt-collection` simulator at full scale (Chapter 3
§3.1: 534,314 modelling rows; Chapter 3 §3.4: 235,968
economic-analysis rows; Chapter 3 §3.6 and Chapter 4 §4.4: 64,027
OOT economics rows), with real-data replication and transfer
scoring catalogued as Future Work F2 and F7 in Chapter 6 §6.2.

The thesis's position, in summary, is that profit-driven cut-off
selection has principled support in the textbook literature but
limited controlled empirical evidence at scale. Within the tested
scenario space documented in Chapter 4 §4.7, the thesis provides
such evidence. The boundary conditions of the empirical claim —
what is shown, on what data, under what assumptions — are
documented in Chapter 5 §5.5 and Chapter 6 §6.1, and the directions
in which subsequent work could extend the claim are catalogued as
Future Work F1 through F7 in Chapter 6 §6.2. The intent of this
chapter has been to show what the existing literature does and
does not contain on the profit-versus-discrimination question, and
to make explicit the specific gaps that the thesis fills.
