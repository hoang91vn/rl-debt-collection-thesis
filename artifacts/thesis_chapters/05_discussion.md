# Chapter 5 — Discussion

This chapter synthesises the empirical findings of Chapter 4 into the
thesis's substantive contribution and positions that contribution
against the existing literature on profit-driven credit scoring. It
contains no new analysis: every numerical claim is sourced from
Chapters 3 or 4 and every figure or table reference points back to
artifacts already documented. The chapter is organised in six sections.
§5.1 distils the four headline findings; §5.2 translates them into
implications for credit-risk practice under the locked thesis
assumptions; §5.3 places the work in dialogue with prior literature
and identifies the novel methodological contribution; §5.4 articulates
the methodological positioning of the synthetic-data design choice and
the discipline used in stress testing, bootstrap, and validation gates;
§5.5 records the boundary conditions that limit the scope of the
findings (forward-linking to the formal Limitations chapter); and §5.6
outlines the future-research directions that arise naturally from
those boundary conditions (forward-linking to the Future Work section
of Chapter 6).

The wording rules of Chapters 3 and 4 are observed throughout: *across
N resamples* and *within the tested scenario space* in place of true
probability statements, *portfolio risk stress* in preference to *PD
model quality*, the consistent "12-month" form, and explicit boundary
conditions wherever a claim might otherwise be over-generalised.

---

## 5.1 Synthesis of Empirical Findings

The thesis's empirical chain produced four headline findings, each
derived from a distinct phase of the analysis pipeline. They are
restated here in compact form so that the implications discussion in
§5.2 has a single reference point.

### Finding 1 — Profit cut-off strictly beats Youden's J in dollar terms

Across the 64 cells of the Phase 4.2 stress space and across the
4,000 (anchor × resample) combinations of the OOT bootstrap, the
profit-driven cut-off produced strictly higher dollar Expected Profit
than the Youden's J cut-off in 64 of 64 cells and 4,000 of 4,000
bootstrap-anchor combinations (§4.4, §4.7). The dollar magnitude of
the advantage ranges from $0.46M at the adverse_stress anchor on the
OOT economics population to $30.75M at the optimistic_base anchor
(Table 4.6); per-anchor 95% CIs do not cross zero in any of the four
scenarios. The refined chapter-conclusion claim was therefore
formulated in dollar-anchored rather than direction-anchored terms:
"profit-driven cut-offs strictly beat Youden's J in dollar terms,
regardless of whether the profit-optimal cut-off is more or less
permissive than Youden's in approval-rate terms" (§4.7).

### Finding 2 — The cut-off gap widens as the PD signal weakens

The Phase 4.2 PART A study (§4.5) perturbed the LightGBM Platt PD to
target Ginis of 0.30, 0.45, and 0.60 (compared to a raw Gini ≈ 0.80)
and observed that the mean cut-off gap *widens monotonically* as Gini
falls — from +15.5 percentage points at the raw Gini to +35.7 pp at
Gini 0.30 (Table 4.7, Figure 2). The mechanism is that Youden's J
maximises TPR − FPR; as the score's discrimination falls the ROC
curve flattens and the J-maximising threshold migrates inward, while
the profit-optimal threshold stays anchored to the underlying
economics and remains close to the full-population point. The gap
between the two therefore widens as the PD becomes less informative.
Within the tested scenario space, the framework's dollar advantage
grows precisely where the underlying PD signal is weakest.

### Finding 3 — The framework adapts to severe stress (reject-most as self-falsification)

The Phase 4.2 PART B + PART C op_cost robustness studies (§4.6, §4.7)
identified one cell — adverse_stress at op_cost = 0.04 — in which the
profit-optimal approval rate `k*` collapses to 0.31% on the OOT
economics population, with mean profit −$387 per account and total
profit −$24.8M. This is the only reject-most cell in the entire 64-cell
Phase 4.2 stress space. Its existence is interpretively important: a
profit-driven framework that *always* prescribed "approve more than
Youden" regardless of conditions would be either trivial (a constant
rule disguised as optimisation) or suspect (a systematic artefact
rather than a substantive economic finding). The reject-most cell
shows that the framework can and does prescribe near-rejection when
the underlying economics make most accounts loss-making, and it does
so at the simultaneous extreme of all six stress dimensions
(PD × 5, LGD 0.85, flat 18% APR, $500 acquisition cost, 6% cost of
funds, 4% operating cost). The framework is therefore an adaptive
optimisation rule rather than a one-sided "approve-all" recommendation.

### Finding 4 — Tenor-aware lifetime framework outperforms ASB by ~40% on 36-month loans

The Phase 3.1B base economic comparison (§4.2, Figure 4) showed that
the locked tenor-aware Lifetime Net Margin formula produces
substantially higher portfolio profit estimates than the simpler ASB
single-period benchmark. On the 235,968-row economics-eligible
population, the ASB total of $250.9M is 71% of the Lifetime total of
$352.3M; the gap grows with tenor (ASB / Lifetime ratio = 0.91 on
24-month loans, 0.60 on 36-month loans). The structural mechanism is
that ASB assumes one full year of interest at the full loan amount
and ignores both amortization and survival weighting, while the
Lifetime formula applies declining-balance interest over the full
loan life and survival-weights every period. The ~40% understatement
on 36-month loans is not a numerical anomaly; it is a definitional
property of the simpler formula. A thesis that adopted ASB as its main
economic measure would systematically under-weight long-tenor loans
in the cut-off optimisation for arithmetic reasons rather than
economic ones.

---

## 5.2 Implications for Credit Risk Practice

The four findings translate into practical implications for credit
risk management — but those implications are conditioned on the
thesis assumptions (synthetic simulator data, exogenous APR and LGD,
locked formulas, single seed) and should not be interpreted as
market-validated prescriptions. With that caveat foregrounded, the
following practical inferences are supported by the empirical chain.

### Implication 1 — Profit-driven cut-offs add value across PD-signal regimes, with larger cut-off gaps under weaker PD signals

For institutions whose PD models achieve high discrimination,
profit-driven cut-offs still generate material uplift in the tested
scenario space. However, the incremental cut-off gap relative to
Youden's J is smaller than under degraded PD signals. At a Gini
above approximately 0.70 within the simulator's behavioural
envelope (§4.5), the cut-off gap relative to Youden's J in the
tested scenario space is around 15-20 percentage points and the
dollar uplift on the 64,027-row OOT economics population ranges
from approximately $5M (moderate_interior anchor) to $30M
(optimistic_base anchor) — approximately 11-47% relative profit
gain across the optimistic-to-moderate-interior anchors, depending
on the cost regime (§4.4, Table 4.6). For institutions whose PD
signal is materially weaker (Gini 0.45-0.60), the cut-off gap
widens to 20-35 pp (§4.5, Table 4.7). The wider cut-off gap
suggests a larger strategic opportunity, although the PART A grid
reports approval-rate gaps rather than directly tabulated relative
profit uplift. The practical inference is that *banks with weaker
scoring infrastructure may have proportionally more to gain from
adopting profit-driven cut-off selection than banks with stronger
scoring* — the opposite of what conventional wisdom would suggest.

### Implication 2 — Operational cost management is critical

The Phase 4.2 PART B finding (§4.6) — that operating cost = 4%
combined with adverse-stress economic conditions tips the framework
into the reject-most regime — implies that operational cost
discipline is a precondition for the framework's continued positive
guidance. In the tested scenario space, the framework remains in
the interior or approve-all classification at op_cost ≤ 2% across
all anchor scenarios; at op_cost = 4% it remains interior for the
realistic and moderate anchors but collapses to reject-most for the
adverse_stress anchor. The implication is that institutions
operating with op_cost above approximately 2% should expect the
profit-driven cut-off to recommend *materially tighter* approval
than at lower op_cost levels, and at op_cost approaching 4% may face
a regime in which most accounts are loss-making after operating
expense — at which point the framework correctly recommends
near-rejection.

### Implication 3 — APR pricing strategy is the second-most important driver

The Phase 3.2 driver hierarchy (§4.3, Table 4.5, Figure 9) ranked
APR strategy second only to PD multiplier in influence on the
profit-optimal cut-off, with a 2.32 pp spread on `k*` across the
tested APR strategies (tiered_uncapped, tiered_cap_24, flat_18,
flat_24). The implication is that the choice of pricing scheme — in
particular, whether the institution prices risk through tiered APR or
applies a flat APR across the portfolio — has measurable consequences
for the cut-off optimum. Within the tested scenario space, tiered
risk-priced APR generates higher portfolio profit than flat pricing
at comparable nominal APR levels because the tiered scheme charges
higher APR on higher-PD borrowers. This finding is directionally
consistent with conventional risk-based pricing literature [TODO:
cite risk-based pricing literature, e.g., Edelberg 2006 or
Phillips 2018] but is here quantified within the thesis's
synthetic-data and locked-formula context rather than across a real
market.

### Implication 4 — These implications are conditioned, not market-validated

The implications above are derived strictly *within the tested
scenario space* — the locked APR tier table (Section 3.4), the
exogenous LGD assumption of 0.65 base with sensitivity grid
{0.45, 0.55, 0.65, 0.75, 0.85}, the constant-hazard extrapolation
from PD₁₂ₘ to lifetime horizon (§3.4), the single simulator seed,
and the synthetic-data origin of every input. None of the
implications are statements about real market behaviour. The thesis
does not claim that profit-driven cut-off selection will produce a
30% dollar uplift in any real bank's loan book; it claims that
within the tested scenario space, on a synthetic portfolio of
235,968 loans, the dollar uplift falls within a quantified range
with quantified per-anchor confidence intervals.

---

## 5.3 Comparison with Existing Literature

The thesis contributes to four overlapping bodies of literature:
(i) profit-driven cut-off selection in credit scoring, (ii) lifetime
expected loss measurement and IFRS 9 staging, (iii) stress testing
methodology in retail credit, and (iv) the use of synthetic data for
methodological research. This section locates the work in each.

### Confirmation of established profit-cut-off literature

The core idea that profit-driven cut-off selection can outperform
discrimination-driven selection is not original to this thesis. Mays
(2004) [TODO: cite Mays "Credit Scoring for Risk Managers"] and
Anderson (2007) [TODO: cite Anderson "The Credit Scoring Toolkit"]
both treat profit curves as a primary scorecard-validation tool, and
Siddiqi (2017) [TODO: cite Siddiqi "Intelligent Credit Scoring"]
explicitly recommends profit-based cut-off selection for risk-priced
lending portfolios. The empirical evidence in Chapter 4 confirms
their guidance — that profit-driven cut-offs outperform
discrimination-driven cut-offs in dollar terms — within the
synthetic-data scenario space tested here. The thesis's contribution
to this strand of literature is not to overturn the existing
guidance but to *quantify* it under controlled stress: the
4,000-bootstrap × 4-anchor × 64-stress-cell evidence constitutes a
substantially larger empirical base for the profit-cut-off claim
than is typically reported in the textbook literature, where
illustrative single-cell or single-curve examples are the norm.

### Extension: tenor-aware lifetime framework

Most published profit-cut-off analyses use single-period profit
formulas (revenue from one period of interest minus expected loss
in that period). The thesis adopts a tenor-aware Lifetime Net
Margin formula (§3.4) that survival-weights revenue and expected
loss over the full amortization schedule; the comparison against
the ASB single-period benchmark (§4.2) demonstrates a structural
~40% understatement on 36-month loans. The implication for the
literature is that single-period analyses systematically
under-weight longer-tenor portfolios in cut-off optimisation, and
that a tenor-aware extension is necessary for any framework whose
target portfolio mixes short-term and longer-term unsecured
credit. The locked formulas in `phase3_formula_lock.md` provide a
reference implementation against which future tenor-aware studies
can compare.

This extension is also a contribution to the IFRS 9 lifetime
expected loss literature [TODO: cite IFRS 9 ECL literature, e.g.,
Beerbaum 2015 or Krüger et al. 2018]. The Lifetime Expected Loss
formula used in the thesis is structurally compatible with
Stage 2/3 ECL calculations under IFRS 9 — `LT_EL = Σ_t marginal_PD_t
· LGD · EAD_t · discount_t` is the standard IFRS 9 form — although
the thesis applies it to *cut-off optimisation* rather than to
provisioning. The unification of the two uses is itself a small
methodological contribution: the same formula stack supports both
loss provisioning and approval decision-making, and the locked
implementation in `src/economics.py` is independently unit-tested
(nine identity and monotonicity tests in `tests/test_economics.py`).

### Extension: multi-dimensional stress testing

The bulk of published stress-testing analyses for retail credit
profit frameworks vary one or two parameters at a time
[TODO: cite single-axis sensitivity examples, e.g., Bellotti &
Crook 2009 or Verbraken et al. 2014]. The thesis instead constructs
a 576-cell economic stress grid (§4.3) crossing five dimensions,
plus a 16-cell PD-quality grid (§4.5) and a 12-cell op_cost grid
(§4.6) and a 36-cell combined grid (§4.7) — a total of 64 stress
cells beyond the 576-cell economic grid, all evaluated on the same
locked formulas and the same OOT subset. The implication is that
single-axis sensitivity is insufficient for characterising the
robustness of a cut-off framework: the only reject-most regime in
the entire 64-cell space appears at the *simultaneous* extreme of
six dimensions, an outcome no single-axis study would have
detected. The multi-dimensional stress design is therefore
proposed here as a methodology contribution in its own right.

### Novel contribution: the PD-quality inversion finding

The most novel methodological contribution of the thesis is the
PD-quality inversion documented in §4.5 and Finding 2 above. To
the author's knowledge, no published study in the profit-driven
credit scoring literature has explicitly reported that the value
of a profit-anchored cut-off relative to a discrimination-anchored
cut-off *grows* as the PD signal weakens. The mechanism — Youden's
J becoming inward-conservative as the ROC flattens, while the
profit-optimal cut-off remains anchored to economics — is
straightforward when stated, but it inverts an implicit
assumption (that better PD models are needed to derive value from
profit-driven optimisation) that pervades practical credit risk
discussions. The implication for institutions with weaker scoring
infrastructure is that they may have proportionally more to gain
from adopting profit-driven cut-off selection than institutions
with stronger scoring, not less. Within the tested scenario space,
this finding is robust across the four anchor scenarios and across
all 16 cells of the PD-quality stress sub-grid, with the
point-estimate uplift positive in every tested cell (no
per-stress-cell CI was computed; the bootstrap CIs of §4.4 cover
the four anchor scenarios but not the individual PART A cells).
The qualifier *within the tested scenario space* matters: the
finding has not been demonstrated on
real-data, on alternative simulator configurations, or with
alternative PD-perturbation methodologies, and the future-work
section identifies these as priority replication targets.

---

## 5.4 Methodological Positioning

This section reflects on four methodological choices that shape the
thesis's contribution: the use of synthetic data, the
multi-dimensional stress design, the bootstrap-versus-assumption
discipline, and the use of validation gates throughout the pipeline.
Each is presented as a *deliberate design choice* rather than as a
limitation — the limitations are recorded in §5.5 and in Chapter 6.

### Synthetic data: feature, not bug

The thesis uses output from a single synthetic simulator
(`rl-debt-collection`) rather than a real-world public credit
dataset. This choice is sometimes treated as a weakness in
methodological work; here it is presented as an enabling design
choice. Real consumer-credit datasets (Lending Club, Freddie Mac,
Bondora, Home Credit) confound the methodological question of
profit-driven cut-off selection with data-quality issues
(missingness, censoring, reporting lag), regulatory issues
(disparate-impact constraints that distort cut-off comparisons),
and proprietary-data confounds (sample selection by the originator,
risk-based pricing already embedded in the data). A simulator
allows the methodology to be tested under known conditions — known
APR, known LGD, known PD generation process — so that any observed
effect can be attributed to the cut-off framework rather than to
omitted confounders. The Future Work direction in §5.6 (and in
Chapter 6) of replicating the analysis on real public data is a
*next step* in the research programme, not a substitute for the
controlled methodological experiment conducted here.

### Multi-dimensional stress design

The thesis's stress test design covers 64 distinct cells beyond the
576-cell economic grid, intentionally probing the joint space of
(i) economic assumptions (Phase 3.2), (ii) PD-quality stress
(Phase 4.2 PART A), (iii) operating-cost stress (Phase 4.2 PART B),
and (iv) the combined PD-quality × operating-cost grid (Phase 4.2
PART C). Single-axis sensitivity — varying one parameter while
holding all others at default — was deliberately rejected as
insufficient because the empirical evidence shows that the
framework's behaviour at extreme conditions (the reject-most
regime) appears only at the *joint* extreme of all six
dimensions. A study that reported sensitivity to operating cost
alone, holding the other five dimensions at base values, would
have missed the reject-most regime entirely. The multi-dimensional
design is therefore a precondition for the claim that the
framework is adaptive (Finding 3) and for the boundary
characterisation that supports the refined thesis claim (§4.7).

### Bootstrap versus assumption uncertainty

The Phase 4.1 bootstrap design (§3.6, §4.4) is intentionally narrow
in scope: it quantifies *sampling* uncertainty within the OOT
economics population only. It does not quantify (i) PD model
uncertainty across alternative hyperparameters, (ii) calibration
drift across cohorts beyond 202706, (iii) APR / LGD /
cost-of-funds assumption uncertainty, or (iv) formula choice
uncertainty (e.g., constant versus declining hazard). These four
omitted uncertainty sources are documented in §3.6 and in the
Limitations chapter. The discipline of separating sampling
uncertainty from assumption uncertainty allows each to be
addressed by a different methodological tool: bootstrap for
sampling, multi-dimensional stress grids for assumption ranges,
and replication on alternative data / alternative simulator seeds
for residual model and data-process uncertainty. Many published
profit-cut-off studies conflate these uncertainty sources,
typically by reporting a single point estimate with no
quantification. The thesis's separation is a methodology
contribution that future work in this area can adopt.

### Validation gates and process discipline

The thesis pipeline incorporates several explicit validation gates
that protect against the most common failure modes in this kind
of analysis: the F6D negative-control gate (§4.1) detects leakage
of pure-noise features into the selection pipeline; the score /
scorem exclusion via FINAL_COLS whitelist in
`scripts/build_wide_abt.py` prevents the simulator's
near-tautological internal score from contaminating the PD models
(§3.2); the leak-free temporal calibration design (§3.3, §4.4)
prevents OOT contamination of the Platt scaling; the 12-month loan
exclusion (§3.4, §4.2) prevents a structural simulator artefact
from corrupting portfolio-level economics; the locked formula
contract (`phase3_formula_lock.md`, §3.4) prevents formula
drift across the analysis chain; the unit tests in
`tests/test_economics.py` verify identity and monotonicity
properties on the locked formulas (§3.4); and the locked phrasing
rules (§3.6, §4.7) prevent overclaiming. None of these gates is a
research finding in itself; collectively they constitute the
process discipline that supports the rigour of the substantive
findings in Chapter 4.

---

## 5.5 Boundary Conditions

The conclusions of this chapter are valid only within explicitly
documented boundary conditions, summarised here for readability and
treated formally in Chapter 6 (Limitations). Each boundary condition
constrains the generality of one or more findings.

- **Within the tested scenario space.** The 4,000 bootstrap × anchor
  combinations of §4.4 and the 64 stress cells of §4.5-§4.7 define
  the empirical base of every claim. Findings outside this space —
  for instance, at PD multipliers above 5, at LGD below 0.45 or
  above 0.85, at APR strategies beyond the four tested, or at
  operating-cost levels above 4% — are not directly supported by
  the analysis.

- **Synthetic simulator artefact dependencies.** The structural
  zero-default rate on 12-month loans (§3.4, §4.2) is a simulator
  target-timing artefact, not a real-world observation. The PD
  multiplier values used in the anchor scenarios approximately
  bracket the LightGBM Platt-calibrator's mean-prediction drift
  (§3.3) but do not directly reflect a real-world calibration
  miss. The Adjusted Single-period Benchmark (ASB) gap on 36-month
  loans (§4.2) reflects amortization arithmetic shared by any
  synthetic or real portfolio with declining-balance loans, so this
  particular finding is more transferable than the others.

- **LightGBM calibration mismatch on the eco-OOT subset.** The
  primary PD model under-predicts the eco-OOT empirical default
  rate by approximately a factor of two (predicted-to-observed
  ratio 0.49, §3.3 and Table 3.4b). The PD-multiplier scenarios
  used in Phase 3 and 4 (multipliers {1, 2, 3, 5}) approximately
  bracket this calibration drift; the profit-vs-Youden hypothesis
  is tested at every multiplier and survives each one. The
  finding is therefore not driven by the calibration miss, but
  the miss itself is a methodological caveat that any real-world
  application of the framework must address through its own
  calibration design.

- **Constant monthly hazard assumption.** The locked formulas
  (§3.4) extrapolate the monthly hazard `h = 1 − (1 − PD₁₂ₘ)^(1/12)`
  from the 12-month forward PD across the full amortization
  schedule. For 36-month loans this implies a cumulative PD of
  `1 − (1 − h)^36`, which assumes the same monthly hazard
  throughout the loan life. Real-world hazard rates typically
  decline with loan age (curing effect), so the constant-hazard
  assumption likely *overstates* lifetime EL on long-tenor loans.
  The implication is that any real-world LT_EL estimate using the
  locked formulas would be a conservative (high-side) estimate.
  Whether this translates into larger profit uplift for the
  framework depends on how the hazard reshapes both Youden's J
  threshold and the profit-optimal threshold; the net effect on
  the profit-uplift metric is an empirical question that Future
  Work F4 would resolve.

- **APR and LGD as exogenous assumptions.** The simulator does not
  produce APR or LGD as outputs; both are supplied as locked
  thesis assumptions (Section 3.4). The locked APR tier table
  (Table 3.5) is informed by published consumer-credit pricing
  ranges but is not market-validated; the LGD = 0.65 base is an
  industry-conventional unsecured-consumer baseline but is not
  empirically calibrated against the simulator's own
  post-default repayment trace (which is feasible but deferred to
  Future Work F1).

These boundary conditions do not undermine the claims of Chapter 4 —
each claim is already framed conditionally — but they delimit the
scope of the conclusions to the specific assumption set tested.

---

## 5.6 Future Research Directions

Six directions for future research arise naturally from the
boundary conditions of §5.5. They are listed here in approximate
order of methodological priority; the formal Future Work catalogue
(F1-F7) appears in Chapter 6.

### Direction 1 — Empirical LGD recovery validation

The simulator's transaction trace
(`artifacts/final_data_800d_60m_p00/transactions.csv`) preserves
the post-default repayment behaviour of every defaulted account.
A focused future study could derive empirical LGD by, for each
`default_flag_12m == 1` aid: locating the writeoff period, summing
all subsequent paid_installments × installment, and computing
LGD = max(0, (loan_amount − recovered) / loan_amount). The
empirical LGD distribution could then be compared to the
exogenous 0.65 base assumption used here. If the empirical
distribution falls within the {0.45, 0.55, 0.65, 0.75, 0.85}
sensitivity grid the thesis's central conclusions are reinforced;
if it falls outside, the analysis would need to be extended with
additional grid points. The compute cost is approximately 10-30
minutes on the existing hardware, depending on memory and I/O
bandwidth.

### Direction 2 — Real-data replication

The most pressing scope-extension is replication on a real public
consumer-credit dataset (Lending Club, Freddie Mac single-family,
Bondora, Home Credit Default Risk on Kaggle). The replication
would test whether the four headline findings of §5.1 — and
particularly the PD-quality inversion of Finding 2 — survive
the transition from synthetic to real data. Three specific
hypotheses warrant testing: (i) does the cut-off gap widen as
PD discrimination falls in real data as it does in the simulator,
(ii) does the dollar uplift remain strictly positive across the
real-data analogue of the tested scenario space, and (iii) does
the reject-most regime appear under realistic combinations of
high operating cost and adverse credit conditions. Real data
will also allow the LightGBM under-prediction caveat (§3.3) to
be revisited under cohort distributions that match the
production application rather than a 12-month-loan-excluded
synthetic subset.

### Direction 3 — Multi-seed simulator robustness

All thesis results derive from a single simulator seed (42).
Cross-seed and cross-configuration robustness is therefore an
open question. A future study could re-run the entire Phase 1.5
through Phase 4.4 pipeline on five or more alternative seeds and
on three or more alternative `p_positive` levels (e.g.,
{0.00, 0.02, 0.05}), then quantify the cross-configuration
variance in (i) the dollar uplift point estimates, (ii) the
cut-off gap distributions, and (iii) the anchor scenario
classifications. If the four headline findings survive the
multi-seed sweep with narrow cross-configuration variance, the
single-seed conclusions are validated; if they exhibit large
cross-seed variance, the thesis's scope claims would need to be
narrowed accordingly.

### Direction 4 — Declining-hazard alternative

The constant-hazard assumption (§5.5) admits a natural
alternative: a parametric declining-hazard schedule fitted to the
simulator's empirical defaults by loan age. A future study could
fit a Weibull or log-logistic hazard curve to the per-month
default counts in the simulator output, then re-run the locked
LT_EL formula with the declining-hazard schedule replacing the
constant `h`. The expected qualitative outcome is that lifetime
EL on 36-month loans falls (because hazards decline after the
first year), which is expected to reduce lifetime EL on
long-tenor loans, but the net effect on the cut-off gap and on
the profit-uplift metric requires empirical testing. The
declining-hazard extension would quantify how much of the
dollar uplift in §4.4 and §4.7 is attributable to the hazard
assumption versus the underlying profit-vs-Youden mechanism.

### Direction 5 — Market-calibrated APR tier validation

The locked APR tier table (Table 3.5) maps PD bands to APR values
using ranges informed by published consumer-credit pricing
ranges but not directly calibrated against any specific market.
A future study could survey published APR by PD band for a
specific market (US, EU, emerging-market segments are the
natural slices), calibrate the tier table to that market, and
test whether the thesis's profit-vs-Youden finding survives the
recalibration. The expected outcome is that the dollar uplift
magnitude shifts but the dollar-anchored claim survives in
sign; quantification of the magnitude shift is the contribution.

### Direction 6 — External validation via transfer scoring

A more ambitious future direction combines Directions 2 and 3:
fit the dual-track PD models (§4.1) on the simulator data and
*score* them on a real public dataset without refitting. Measure
how (i) discrimination metrics translate from simulator to real
data, (ii) the calibration drift behaves under transfer, and
(iii) the profit-vs-Youden uplift survives the transfer. This
external-validation experiment is the strongest available test of
whether the synthetic-data methodology developed here generalises
to production deployment in a real bank.

---

The chapter has interpreted the empirical evidence of Chapter 4 as a
substantive contribution to the profit-driven credit scoring
literature, located that contribution against existing work,
articulated the methodological design choices that shape the
contribution's character, recorded the boundary conditions that
delimit its scope, and identified the future-research directions
that would extend it. Chapter 6 catalogues those boundary
conditions formally as Limitations and the future-research
directions as Future Work items F1 through F7, completing the
thesis's substantive presentation.
