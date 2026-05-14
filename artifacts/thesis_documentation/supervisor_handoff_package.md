# Supervisor Handoff Package

**Date**: 2026-05-11
**Phase**: 8 — Supervisor Handoff Preparation
**Author**: [thesis author]
**Supervisor**: [supervisor name]

---

## Thesis title

**Profit-Driven Credit Scoring: Optimizing Cut-off Strategies for
Maximum Lending Profitability**

## Status

- ✅ Full content draft complete (Abstract + 6 chapters)
- ✅ Global consistency audit complete (`global_consistency_audit.md`)
- ✅ Post-audit fixes applied (Figure 1 citation in Ch4 §4.4; Ch6 §6.1
  hedge-opening sentence)
- ⏸ **Citation finalization pending** — see open issue below
- ⏸ Supervisor methodology / content review pending

---

## Chapter inventory

| File | Title | Word count | Status |
|---|---|---|---|
| `00_abstract.md` | Abstract | 346 | ✅ approved |
| `01_introduction.md` | Introduction | 3,395 | ✅ approved |
| `02_literature_review.md` | Literature Review | 4,363 | ✅ approved |
| `03_methodology.md` | Methodology | 5,673 | ✅ approved |
| `04_results.md` | Results | 5,803 | ✅ approved |
| `05_discussion.md` | Discussion | 4,402 | ✅ approved |
| `06_limitations.md` | Limitations and Future Work | 4,259 | ✅ approved |
| **Total** | | **~28,241** | |

All 9 publication figures (`fig1_profit_curves` through
`fig9_sensitivity_hierarchy`) are saved at 300 DPI in PDF + PNG and
are referenced in chapter prose post-audit.

---

## Main research question

> *Under what conditions do profit-driven cut-offs outperform
> discrimination-driven cut-offs in expected dollar profit?*

The "under what conditions" framing is deliberate: the question is
not whether profit-driven cut-offs ever outperform Youden's J (the
textbook literature establishes this on principled grounds), but
whether the outperformance is robust across the joint space of
economic assumptions, PD-signal regimes, and operating cost levels
that a real institution would face.

The main question decomposes into four sub-questions, addressed by
distinct phases of the empirical analysis in Chapter 4:

1. How do profit-driven cut-offs differ from Youden's J cut-offs in
   approval-rate and dollar-profit terms? *(Ch4 §4.2-§4.4)*
2. How does PD signal informativeness affect the
   profit-versus-Youden cut-off gap? *(Ch4 §4.5)*
3. How sensitive are the optimal cut-offs to APR pricing strategy,
   LGD, acquisition cost, funding cost, and operating cost?
   *(Ch4 §4.3, §4.6)*
4. Does the tenor-aware Lifetime Net Margin framework materially
   differ from a simpler single-period benchmark? *(Ch4 §4.2)*

---

## Refined thesis claim (from Ch4 §4.7, restated in Ch1 §1.3)

> *Within the tested scenario space, profit-driven cut-offs strictly
> beat Youden's J in dollar terms, regardless of whether the
> profit-optimal cut-off is more or less permissive than Youden's in
> approval-rate terms.*

This is **not** claimed as a universal real-market law; it is an
empirical finding under the locked simulator (Ch3 §3.1), the locked
PD model (Ch3 §3.3, with the LightGBM tuned + Platt model as
primary), the locked Lifetime Net Margin formula stack (Ch3 §3.4),
and the explicit stress-test design (Ch3 §3.5). The boundary
conditions under which the claim is valid are enumerated in Ch5 §5.5
and treated formally as Limitations in Ch6 §6.1. The replication
directions that would extend the claim's scope are catalogued as
Future Work F1-F7 in Ch6 §6.2.

---

## Four contributions

1. **Tenor-aware Lifetime Net Margin framework for cut-off
   optimisation** (Ch3 §3.4; reference implementation in
   `src/economics.py`). The simpler ASB single-period benchmark
   understates the lifetime metric by approximately 40% on 36-month
   loans because amortization and survival weighting are
   systematically ignored.

2. **Multi-dimensional stress-test design** — a 576-cell economic
   stress grid (Ch4 §4.3) plus a 64-cell Phase 4.2 PD-signal ×
   operating-cost stress space (Ch4 §4.5-§4.7). Motivated by the
   finding that the only reject-most regime in the entire 64-cell
   space appears at the simultaneous extreme of all six stress
   dimensions — a regime that no single-axis study would have
   detected.

3. **PD-signal inversion finding** *(highlighted as the most novel)*
   — the cut-off gap between profit-driven and Youden's J cut-offs
   widens monotonically as PD signal informativeness falls, from
   approximately +15.5 percentage points at the LightGBM raw Gini ≈
   0.80 to approximately +35.7 pp at Gini 0.30. To the author's
   knowledge, this inversion has not been explicitly reported in
   the published profit-driven credit-scoring literature.

4. **Bootstrap-versus-assumption uncertainty discipline** — the
   Phase 4.1 1,000-resample stratified bootstrap on the OOT
   economics population quantifies sampling uncertainty within a
   fixed locked pipeline; assumption uncertainty is addressed
   separately by the multi-dimensional stress grids. The discipline
   prevents the bootstrap CIs from being misread as estimates of
   total uncertainty.

---

## Four headline findings (from Ch5 §5.1)

1. **Profit-driven cut-offs strictly beat Youden's J in dollar
   terms** — point-estimate uplift positive in 64 of 64 stress
   cells; uplift positive in 4,000 of 4,000 anchor × bootstrap
   combinations; per-anchor 95% bootstrap CIs do not cross zero in
   any of the four anchor scenarios. Dollar magnitude ranges from
   approximately $0.46M (adverse_stress anchor) to approximately
   $30.75M (optimistic_base anchor) on the 64,027-row OOT
   economics population.

2. **The cut-off gap widens as the PD signal weakens** — from
   approximately +15.5 pp at the raw Gini of 0.80 to approximately
   +35.7 pp at Gini 0.30 (mean cut-off gap, Phase 4.2 PART A).

3. **The framework adapts to severe stress** — one reject-most cell
   in the 64-cell stress space (adverse_stress at op_cost = 0.04;
   `k*` = 0.31%; mean profit −$387; total profit −$24.8M) confirms
   that the framework is an adaptive optimisation rule rather than
   a uniformly permissive recommendation.

4. **Tenor-aware Lifetime Net Margin formula outperforms ASB by
   approximately 40% on 36-month loans** — the locked Lifetime total
   ($352.3M) exceeds the simpler ASB total ($250.9M) on the
   235,968-row economics-eligible population; the gap grows with
   tenor (ASB/Lifetime ratio = 0.91 on 24-month loans, 0.60 on
   36-month loans).

---

## Key caveats (from Ch5 §5.5 and Ch6 §6.1)

1. **Synthetic-simulator data, not real-world data.** All empirical
   results derive from a single production run of the
   `rl-debt-collection` simulator (seed 42, `p_positive = 0.00`,
   800 clients/day, 60-month window). Quantitative magnitudes are
   not expected to transfer numerically to real data; qualitative
   findings are expected to transfer in direction (Future Work F2
   and F7 test this).

2. **12-month loan exclusion.** The simulator's writeoff trigger is
   structurally unreachable within the 12-month forward target
   window for `n_installments = 12`. The economic-analysis
   population is therefore restricted to 24-month and 36-month
   loans (235,968 rows of 534,314 modelling rows). Future Work F3
   addresses the alternative-default-definition extension.

3. **APR and LGD as exogenous assumptions.** The simulator does
   not produce APR or LGD; both are supplied as locked thesis
   assumptions (Ch3 §3.4). LGD is exogenous (0.65 base case,
   sensitivity grid {0.45-0.85}); empirical LGD recovery is
   catalogued as Future Work F1.

4. **LightGBM under-prediction on the eco-OOT subset** —
   predicted-to-observed ratio approximately 0.49 on the 64,027-row
   OOT economics population (calibration drift between the
   202611-202612 calibration slice base rate ≈0.85% and the
   eco-OOT base rate ≈1.92%). The PD-multiplier scenarios in Phase
   3 and 4 bracket this calibration drift; the profit-vs-Youden
   hypothesis survives at every multiplier.

5. **Constant monthly hazard assumption.** The lifetime-EL formula
   extrapolates `h = 1 − (1 − PD₁₂ₘ)^(1/12)` across the full
   amortization schedule. Real-world hazards typically decline with
   loan age. The net effect on the profit-uplift metric is an
   empirical question for Future Work F4.

6. **Bootstrap captures sampling uncertainty only.** Assumption
   uncertainty is addressed separately by the multi-dimensional
   stress grids; cross-configuration variance (alternative seeds /
   `p_positive` levels) is deferred to Future Work F6.

The full enumeration is at Ch6 §6.1 (10 limitations).

---

## Open citation issue

**Operating-cost benchmark (Group AA in `citation_pass_inventory.md`)
— PENDING RESEARCH.** The thesis cites a "1-5% operating cost range"
in Ch4 §4.6 and Ch6 §6.1 Limitation 7. Neither location currently
backs the empirical claim with a verified source. This is the only
HIGH-PRIORITY citation gap identified by the global consistency
audit and is the single open citation issue that may merit attention
before the supervisor methodology review.

Candidate canonical sources to verify (none invented, none
selected — see `citation_pass_inventory.md` for details):
- McKinsey global banking benchmark report
- Federal Reserve cost-to-income ratio statistics for retail banks
- EBA retail-bank operating-cost statistics
- A consultant practitioner report on consumer-lending operating-
  cost ranges

The remaining 49 `[TODO: cite]` markers are catalogued in
`citation_pass_inventory.md` as 32 source groups (5 HIGH-priority,
14 MEDIUM, 13 LOW) and primarily require user / library lookup
rather than independent research; they do not block supervisor
methodology review.

---

## Recommended supervisor review focus

Listed in priority order — supervisor input on (1)-(4) is most
valuable; input on (5) determines the next-phase workflow.

### 1. Research framing

- Does the central question — "under what conditions do
  profit-driven cut-offs outperform discrimination-driven cut-offs
  in expected dollar profit?" — match the field's open question?
- Is the four-sub-question decomposition complete, and is the
  scope appropriate for a Master's thesis?
- Is the synthetic-data positioning (Ch1 §1.1, Ch2 §2.6, Ch5 §5.4)
  defensible, particularly given the unusual choice to bypass real
  public credit datasets?

### 2. Methodology appropriateness

- Is the locked tenor-aware Lifetime Net Margin formula stack
  (Ch3 §3.4; reference implementation in `src/economics.py`)
  appropriate for cut-off optimisation rather than provisioning?
- Is the dual-track PD modelling design (LightGBM primary +
  Logistic Regression + Scorecard) defensible? Is the leak-free
  Platt calibration on cohorts 202611-202612 a sound design?
- Is the multi-dimensional stress design (576-cell + 64-cell
  Phase 4.2 stress space) proportionate, or does the supervisor see
  redundancy or coverage gaps?
- Does the bootstrap-versus-assumption uncertainty separation
  (Ch3 §3.6, Ch5 §5.4) cleanly delineate sampling vs assumption
  uncertainty?

### 3. Strength of the empirical claim

- Is the dollar-anchored refined claim ("strictly beat Youden's J in
  dollar terms regardless of approval-rate direction") an
  appropriate substitute for the earlier direction-anchored claim
  that the empirical evidence did not uniformly support?
- Is 64-of-64 stress cells + 4,000-of-4,000 bootstrap-anchor
  combinations + per-anchor CIs not crossing zero an evidence base
  that the supervisor finds compelling?
- Is the PD-signal inversion finding (Contribution 3) sufficiently
  novel to be highlighted as the central methodological
  contribution? The inversion is described in approval-rate-gap
  terms (not directly tabulated relative dollar uplift) — is this
  hedge appropriate?

### 4. Limitations / Future Work framing

- Is the boundary-condition discipline (Ch5 §5.5 + Ch6 §6.1) honest
  enough? Are any limitations missing from the 10-item list?
- Is the Future Work catalogue (Ch6 §6.2) appropriately
  prioritised, with F1 (empirical LGD recovery) and F2 (real-data
  replication) as the two HIGH-priority directions?
- Does the LightGBM under-prediction caveat (Limitation 6;
  predicted-to-observed ratio 0.49 on eco-OOT) need a more
  prominent treatment, or is the current bracketing-by-PD-multiplier
  framing sufficient?

### 5. Citation finalization sequencing

- Should citation finalization happen **before** the supervisor
  methodology review (so the supervisor reads the thesis with full
  citations), or **after** the supervisor methodology review (so
  citation work is concentrated in a single pass after any
  methodology revisions)?
- The 49 non-blocking `[TODO: cite]` markers can be resolved in
  approximately one focused citation-pass session (estimated
  effort 2-4 hours) by a research assistant or by the author with
  citation-database access.
- The 1 HIGH-PRIORITY operating-cost benchmark (Group AA) requires
  a substantive source-research decision and is the only citation
  whose absence affects the empirical interpretation of Ch4 §4.6 /
  Ch6 §6.1 Limitation 7.

---

## Companion documents

- `global_consistency_audit.md` — full Phase 7 audit report
  (numbers, section references, hedge enforcement, Tables/Figures
  inventory, forward references)
- `citation_pass_inventory.md` — full Phase 8 Task 1 citation
  inventory (32 groups, 50 markers, status + priority)
- `thesis_evidence_map.md` — every claim mapped to artifact +
  figure + numerical value + caveat
- `thesis_methodology_lock.md` — locked decisions across the
  empirical chain
- `thesis_results_summary.md` — every numerical result consolidated
  into thesis-ready tables
- `thesis_limitations.md` — enumeration of 10 limitations + 7
  Future Work items (mirrors Ch6 §6.1 + §6.2)
- `artifact_inventory.md` — every file path + size + purpose +
  chapter mapping
- `writing_readiness_report.md` — pre-writing readiness assessment

---

**End of supervisor handoff package.**
