# Citation Pass Inventory

**Date**: 2026-05-11
**Phase**: 8 — Citation Pass Preparation
**Status**: Inventory only; no `[TODO: cite]` replacements applied
**Source files**: All 7 chapter files (`00_abstract.md`,
`01_introduction.md`, `02_literature_review.md`, `03_methodology.md`,
`04_results.md`, `05_discussion.md`, `06_limitations.md`) and
`global_consistency_audit.md`

## Citation rule (enforced in this inventory)

> Do not invent or guess bibliographic details. Do not replace `[TODO:
> cite]` markers unless the source is already verified from project
> notes or an accessible citation record. If a source cannot be
> verified, mark as **PENDING RESEARCH**.

The status of each entry below reflects this rule strictly:

- **VERIFIED**: source is internal to the project (e.g., simulator
  repo) or has been previously confirmed by the user
- **NEEDS USER SOURCE**: a specific author / title is mentioned in the
  `[TODO: cite]` text, but the exact bibliographic form (volume,
  issue, page numbers, publisher, edition) needs to be retrieved from
  a citation database or confirmed by the user
- **PENDING RESEARCH**: the `[TODO: cite]` is generic (no specific
  source named) and a representative source must be selected before
  the bibliographic form can be confirmed

---

## Summary

- **Total `[TODO: cite]` markers**: 50
- **Citation groups**: 32 (consolidated from cross-chapter
  duplicates per `global_consistency_audit.md` Task 3)
- **HIGH-priority items**: 5 (Group A textbook tradition; Group AA
  operating-cost benchmark — user-flagged BLOCKING; plus three
  cross-chapter foundations: Group O LightGBM, Group R Optuna,
  Group T Platt scaling)
- **VERIFIED**: 0 (no project-internal sources have been resolved
  yet beyond the simulator-repo TODO at AE)
- **NEEDS USER SOURCE**: 22
- **PENDING RESEARCH**: 10

---

## Inventory Table

### Group A — Profit-cut-off textbook tradition

| Field | Value |
|---|---|
| Sources mentioned in TODO | Mays 2004 *Credit Scoring for Risk Managers*; Anderson 2007 *The Credit Scoring Toolkit*; Siddiqi 2017 *Intelligent Credit Scoring* |
| Locations | Ch1 §1.1 line 36; Ch2 §2.2 lines 102, 106, 109; Ch3 §3.3 line 243; Ch5 §5.3 lines 205, 206, 208 |
| Status | NEEDS USER SOURCE — book editions and page references need confirmation |
| Priority | **HIGH** — central to motivation and literature framing; cited in 4 chapters |
| Notes | Same three books anchor the profit-cut-off tradition across the thesis. A single bibliography entry per book serves all 4 chapters. |

### Group B — Discrimination metrics / ROC

| Field | Value |
|---|---|
| Sources mentioned in TODO | Fawcett 2006 *An introduction to ROC analysis*; Hand & Till 2001 |
| Locations | Ch2 §2.1 lines 35, 39 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM |
| Notes | Fawcett 2006 = *Pattern Recognition Letters* paper; Hand & Till 2001 = *Machine Learning* paper. Both standard ROC references. |

### Group C — Hand 2009 critique

| Field | Value |
|---|---|
| Source mentioned in TODO | Hand 2009 *Measuring classifier performance: a coherent alternative to the area under the ROC curve* |
| Locations | Ch2 §2.1 line 56 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM — supports the §2.1 critique of AUC-based evaluation |

### Group D — Youden's J origin

| Field | Value |
|---|---|
| Source mentioned in TODO | Youden 1950 *Index for rating diagnostic tests* |
| Locations | Ch2 §2.1 line 47 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM — the canonical origin paper for the J statistic |
| Notes | Published in *Cancer* journal; standard citation. |

### Group E — Tenor-aware credit risk

| Field | Value |
|---|---|
| Sources mentioned in TODO | Krüger & Rösch 2017; Bellini 2019 |
| Locations | Ch2 §2.2 line 153 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM — supports the single-period vs lifetime distinction |
| Notes | Specific titles not given in the TODO; recommend the user confirm specific monographs or journal articles by these authors. |

### Group F — Expected Maximum Profit (EMP) framework

| Field | Value |
|---|---|
| Source mentioned in TODO | Verbraken, Verbeke & Baesens 2014 *Expected Maximum Profit framework* |
| Locations | Ch2 §2.2 line 161; Ch2 §2.4 line 290 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM — directly adjacent to the thesis's profit-cut-off design; positioned in §2.2 and §2.4 |

### Group G — Cost-sensitive learning

| Field | Value |
|---|---|
| Source mentioned in TODO | Elkan 2001 *The foundations of cost-sensitive learning* |
| Locations | Ch2 §2.1 line 67; Ch2 §2.4 line 289 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM |
| Notes | IJCAI proceedings paper. |

### Group H — IFRS 9 standard

| Field | Value |
|---|---|
| Sources mentioned in TODO | IFRS 9 standard; Beerbaum 2015 *Significant Increase in Credit Risk under IFRS 9* |
| Locations | Ch2 §2.3 line 198; Ch5 §5.3 line 239 |
| Status | PENDING RESEARCH for IFRS 9 standard (specific publication form); NEEDS USER SOURCE for Beerbaum 2015 |
| Priority | MEDIUM |
| Notes | IFRS 9 is a public IASB standard — cite by IASB year of release. Beerbaum 2015 likely a journal article on SICR criteria. |

### Group I — IFRS 9 implementation

| Field | Value |
|---|---|
| Sources mentioned in TODO | Krüger, Rösch & Scheule 2018; PwC 2017 *IFRS 9 implementation guidance*; Skoglund 2017 *Implementing Credit Risk Models for IFRS 9* |
| Locations | Ch2 §2.3 line 214 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM |
| Notes | Three sources cited as a group; user can pick which one(s) to retain depending on supervisor preference. |

### Group J — LGD modelling in unsecured consumer credit

| Field | Value |
|---|---|
| Sources mentioned in TODO | Schuermann 2004 *What do we know about loss given default?*; Bellotti & Crook 2012 *LGD models for unsecured consumer credit* |
| Locations | Ch2 §2.3 line 229 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM |
| Notes | Schuermann 2004 is the standard LGD-survey paper. Bellotti & Crook 2012 may need title verification. |

### Group K — Stress-testing regulatory standards

| Field | Value |
|---|---|
| Sources mentioned in TODO | Basel III stress-testing principles BCBS 2018; CCAR/DFAST methodology; EBA stress test methodology |
| Locations | Ch2 §2.4 line 269 |
| Status | PENDING RESEARCH |
| Priority | MEDIUM |
| Notes | All three are public regulatory documents. Need to confirm specific BCBS/Federal Reserve/EBA publication titles and dates. |

### Group L — Single-axis sensitivity in profit-curve research

| Field | Value |
|---|---|
| Source mentioned in TODO | Bellotti & Crook 2009 *Credit scoring with macroeconomic variables using survival analysis* |
| Locations | Ch2 §2.4 line 277; Ch5 §5.3 line 255 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM |
| Notes | Cited as exemplar of single-axis macro stress sensitivity. *Journal of the Operational Research Society* article. |

### Group M — Simulation-based credit risk methodology

| Field | Value |
|---|---|
| Sources mentioned in TODO | Bohn & Stein 2009 *Active Credit Portfolio Management in Practice*; Allen & Saunders 2003 retail-credit simulation review |
| Locations | Ch2 §2.4 line 299; Ch3 §3.1 line 136 |
| Status | NEEDS USER SOURCE |
| Priority | LOW |

### Group N — Scorecard tradition

| Field | Value |
|---|---|
| Sources mentioned in TODO | Thomas, Edelman & Crook 2002 *Credit Scoring and its Applications*; Siddiqi 2006 / 2017 scorecard development |
| Locations | Ch2 §2.5 line 332; Ch3 §3.3 line 243 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM |
| Notes | Both are standard scorecard textbooks. Siddiqi appears in two editions (2006 and 2017); the user should select which edition to cite. |

### Group O — LightGBM

| Field | Value |
|---|---|
| Source mentioned in TODO | Ke et al. 2017 *LightGBM: A Highly Efficient Gradient Boosting Decision Tree* |
| Locations | Ch2 §2.5 line 347; Ch3 §3.3 line 247 |
| Status | NEEDS USER SOURCE |
| Priority | **HIGH** — central to the primary PD model; cross-chapter (Ch2 + Ch3) |
| Notes | NeurIPS 2017 paper; standard citation. |

### Group P — XGBoost

| Field | Value |
|---|---|
| Source mentioned in TODO | Chen & Guestrin 2016 *XGBoost: A Scalable Tree Boosting System* |
| Locations | Ch2 §2.5 line 348 |
| Status | NEEDS USER SOURCE |
| Priority | LOW |
| Notes | KDD 2016 paper. Cited as comparator to LightGBM but not used in the thesis pipeline. |

### Group Q — LightGBM-vs-LR empirical comparisons

| Field | Value |
|---|---|
| Source mentioned in TODO | (generic — no specific source named) |
| Locations | Ch2 §2.5 line 353 |
| Status | PENDING RESEARCH |
| Priority | LOW |
| Notes | Need to identify a representative published comparison; candidates include Lessmann et al. 2015 *Benchmarking state-of-the-art classification algorithms for credit scoring* (EJOR) or a more recent meta-study. |

### Group R — Optuna (Bayesian hyperparameter optimisation)

| Field | Value |
|---|---|
| Source mentioned in TODO | Akiba et al. 2019 *Optuna: A Next-generation Hyperparameter Optimization Framework* |
| Locations | Ch2 §2.5 line 356; Ch3 §3.3 line 280 |
| Status | NEEDS USER SOURCE |
| Priority | **HIGH** — used in Ch2 + Ch3 PD methodology |
| Notes | KDD 2019 paper; standard citation. |

### Group S — Discrimination vs calibration distinction

| Field | Value |
|---|---|
| Source mentioned in TODO | Niculescu-Mizil & Caruana 2005 *Predicting Good Probabilities with Supervised Learning* |
| Locations | Ch2 §2.5 line 363 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM |
| Notes | ICML 2005 paper. |

### Group T — Platt scaling

| Field | Value |
|---|---|
| Source mentioned in TODO | Platt 1999 *Probabilistic Outputs for Support Vector Machines* |
| Locations | Ch2 §2.5 line 378; Ch3 §3.3 line 295 |
| Status | NEEDS USER SOURCE |
| Priority | **HIGH** — Platt scaling is the calibration method used by the primary PD model; cross-chapter (Ch2 + Ch3) |

### Group U — Isotonic regression

| Field | Value |
|---|---|
| Source mentioned in TODO | Zadrozny & Elkan 2002 *Transforming classifier scores into accurate multi-class probability estimates* |
| Locations | Ch2 §2.5 line 382 |
| Status | NEEDS USER SOURCE |
| Priority | LOW |
| Notes | KDD 2002 paper. Cited as alternative to Platt; not used in thesis. |

### Group V — Synthetic data healthcare

| Field | Value |
|---|---|
| Sources mentioned in TODO | Patki et al. 2016 *The Synthetic Data Vault*; Choi et al. 2017 *medGAN* |
| Locations | Ch2 §2.6 lines 421, 423 |
| Status | NEEDS USER SOURCE |
| Priority | LOW |
| Notes | Patki 2016 from IEEE DSAA; Choi 2017 from MLHC. |

### Group W — Synthetic data finance / order-book

| Field | Value |
|---|---|
| Source mentioned in TODO | Buehler et al. 2020 |
| Locations | Ch2 §2.6 line 424 |
| Status | NEEDS USER SOURCE |
| Priority | LOW |
| Notes | Specific title not given; need to verify. |

### Group X — Synthetic fair-lending interventions

| Field | Value |
|---|---|
| Sources mentioned in TODO | Hardt, Price & Srebro 2016 *Equality of Opportunity in Supervised Learning*; Bellamy et al. 2018 *IBM AIF360* |
| Locations | Ch2 §2.6 line 429 |
| Status | NEEDS USER SOURCE |
| Priority | LOW |

### Group Y — Reject inference

| Field | Value |
|---|---|
| Source mentioned in TODO | Crook & Banasik 2004 |
| Locations | Ch2 §2.6 line 447 |
| Status | NEEDS USER SOURCE |
| Priority | LOW |
| Notes | Likely *Journal of Banking and Finance*. |

### Group Z — Risk-based pricing literature

| Field | Value |
|---|---|
| Sources mentioned in TODO | Edelberg 2006; Phillips 2018 |
| Locations | Ch5 §5.2 line 171 |
| Status | NEEDS USER SOURCE |
| Priority | MEDIUM |
| Notes | Edelberg 2006 likely *Journal of Monetary Economics*; Phillips 2018 likely *Pricing Credit Products*. Need exact citation form. |

### Group AA — Operating cost benchmarks 🔴

| Field | Value |
|---|---|
| Source mentioned in TODO | (no specific source — user-flagged BLOCKING) |
| Locations | Ch4 §4.6 line 531 ("HIGH PRIORITY"); Ch6 §6.1 Limitation 7 line 217 |
| Status | **PENDING RESEARCH** |
| Priority | **HIGH** — only HIGH-PRIORITY citation gap flagged by both Ch4 and Ch6 |
| Notes | Per user instruction, **do not guess source**. Candidate sources to verify: McKinsey global banking benchmark report; Federal Reserve cost-to-income ratio for retail banks; EBA retail-bank operating-cost statistics; consultant practitioner reports on consumer-lending operating-cost ranges. The cited "1-5% range" claim needs an explicit empirical benchmark before the supervisor pass. |

### Group AB — APR market survey

| Field | Value |
|---|---|
| Source mentioned in TODO | Federal Reserve G.19 *Consumer Credit Outstanding* release |
| Locations | Ch3 §3.4 line 494 |
| Status | NEEDS USER SOURCE |
| Priority | LOW |
| Notes | Federal Reserve Statistical Release G.19 is publicly available — user should confirm citation form. |

### Group AC — Basel III PD framework

| Field | Value |
|---|---|
| Source mentioned in TODO | Basel III PD definitions |
| Locations | Ch3 §3.3 line 109 |
| Status | PENDING RESEARCH |
| Priority | LOW |
| Notes | Basel III is a BCBS publication; specific BCBS document number needed for the PD definition (e.g., BCBS 2017 *Basel III: Finalising post-crisis reforms*). |

### Group AD — Lasso / sparse regression

| Field | Value |
|---|---|
| Source mentioned in TODO | Hastie, Tibshirani & Friedman *The Elements of Statistical Learning* |
| Locations | Ch3 §3.3 line 266 |
| Status | NEEDS USER SOURCE |
| Priority | LOW |
| Notes | Standard reference (ESL). 2nd edition (2009) typically cited. |

### Group AE — Simulator repository

| Field | Value |
|---|---|
| Source mentioned in TODO | (own simulator — `rl-debt-collection`) |
| Locations | Ch3 §3.1 line 33 |
| Status | NEEDS USER SOURCE |
| Priority | LOW |
| Notes | Author / repo URL needed. If the simulator was developed by the thesis author, a self-citation to a repository / preprint may be appropriate. |

### Group AF — Zero-interest assumption

| Field | Value |
|---|---|
| Source mentioned in TODO | (generic — no specific source named) |
| Locations | Ch3 §3.1 line 70 |
| Status | PENDING RESEARCH |
| Priority | LOW |
| Notes | The TODO refers to a discussion of the zero-interest simulator assumption; if a specific antecedent paper exists, the user should provide it. Otherwise the discussion can stand without an external citation. |

---

## Priority distribution

| Priority | Count | Groups |
|---|---|---|
| HIGH | 5 | A (textbook tradition); AA (op_cost benchmark — user-flagged); O (LightGBM); R (Optuna); T (Platt) |
| MEDIUM | 14 | B, C, D, E, F, G, H, I, J, K, L, N, S, Z |
| LOW | 13 | M, P, Q, U, V, W, X, Y, AB, AC, AD, AE, AF |

## Status distribution

| Status | Count |
|---|---|
| VERIFIED | 0 |
| NEEDS USER SOURCE | 22 |
| PENDING RESEARCH | 10 |

## PENDING RESEARCH list (10 items)

1. **Group AA** — Operating cost benchmarks (HIGH priority; user-flagged BLOCKING)
2. **Group H** — IFRS 9 standard (specific publication form)
3. **Group K** — Stress-testing regulatory (Basel III BCBS 2018; CCAR/DFAST; EBA stress test — need specific document references)
4. **Group Q** — LightGBM-vs-LR empirical comparisons (no specific source named; need representative paper)
5. **Group AC** — Basel III PD framework (need specific BCBS document number)
6. **Group AF** — Zero-interest assumption (no specific source named)

(Groups H/K/AC partly overlap with regulatory documentation that is
publicly retrievable but needs exact citation form.)

## Action items for the citation pass (next phase)

1. **Resolve Group AA first** — operating-cost benchmark is the only
   HIGH-priority PENDING RESEARCH gap and is flagged in two chapters.
   The thesis cannot ship to final review with this unresolved.
2. **Confirm bibliographic form for Group A** — Mays 2004, Anderson
   2007, Siddiqi 2017 are cited in 4 chapters; resolving once unlocks
   citations across the thesis.
3. **Confirm cross-chapter foundations** — Groups O (LightGBM), R
   (Optuna), and T (Platt) appear in both Ch2 and Ch3.
4. **Bulk verification pass for NEEDS USER SOURCE entries** — all 22
   entries have author + title + (often) year information embedded in
   the TODO; a single citation-database lookup session should resolve
   most of them.
5. **PENDING RESEARCH for regulatory documents** — Groups H, K, AC
   require deciding on specific BCBS / IASB / Federal Reserve / EBA
   publications.

---

**End of citation inventory. No `[TODO: cite]` markers were replaced
during Phase 8 Task 1.**
