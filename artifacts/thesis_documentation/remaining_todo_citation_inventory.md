# Remaining TODO Citation Inventory

**Date**: 2026-05-14
**Phase**: Citation pass — classification inventory (no chapter files modified)
**Citation style**: APA 7th edition
**Source files**: All 7 chapter files (`00_abstract.md` through `06_limitations.md`); citation_pass_inventory.md
**Constraint**: Do NOT modify chapter files; do NOT replace TODO markers; do NOT invent bibliographic details.

---

## Summary

- **Total TODO markers found**: **54**
  *(Note: the previous count of 50 in `citation_pass_inventory.md` was computed with the pattern `TODO: cite` which misses markers where `[TODO:` and `cite` fall on different lines. Using the broader pattern `\[TODO` produces the true count of 54.)*
- **LOCKED_SOURCE markers**: **33**
- **WORDING_FIX markers**: **4**
- **NEEDS_RESEARCH markers**: **17**
- **Unique NEEDS_RESEARCH groups**: **17**
- **Chapters with zero TODO markers**: Abstract (`00_abstract.md`)
- **Per-chapter distribution**: Ch1 = 2, Ch2 = 32, Ch3 = 11, Ch4 = 2, Ch5 = 6, Ch6 = 1

---

## Cross-reference: LOCKED SOURCES (provided by user — APA 7th first reference form)

| Lock | Author(s) (year) | Notes |
|---|---|---|
| 1 | Mays (2004) | *Credit Scoring for Risk Managers* |
| 2 | Anderson (2007) | *The Credit Scoring Toolkit* |
| 3 | Siddiqi (2017) | *Intelligent Credit Scoring* |
| 4 | Akiba et al. (2019) | Optuna |
| 5 | Ke et al. (2017) | LightGBM |
| 6 | Platt (1999) | Platt scaling |
| 7 | Youden (1950) | Youden's J |
| 8 | Fawcett (2006) | ROC analysis |
| 9 | Hand and Till (2001) | AUC / multi-class |
| 10 | Hand (2009) | AUC critique |
| 11 | Řezáč and Řezáč (2011) | Credit-scoring metrics (KS / Gini / Lift) — used for KS marker |
| 12 | Elkan (2001) | Cost-sensitive learning |
| 13 | IASB (2014) | IFRS 9 standard |
| 14 | Beerbaum (2015) | IFRS 9 SICR |
| 15 | Schuermann (2004) | LGD survey |
| 16 | Bellotti and Crook (2009) | Macro / survival single-axis stress |
| 17 | Bellotti and Crook (2012) | LGD unsecured consumer credit (keep order) |
| 18 | Bohn and Stein (2009) | Broad credit portfolio management ONLY — flag when used for synthetic-data methodology |
| 19 | Niculescu-Mizil and Caruana (2005) | Discrimination vs calibration |
| 20 | Thomas et al. (2002) | Credit scoring textbook |
| 21 | Verbraken et al. (2014) | EMP framework — **correct author list is Verbraken, Bravo, Weber & Baesens; not "Verbraken, Verbeke & Baesens"** |

---

## LOCKED_SOURCE markers (33)

| # | Group | Locked source(s) | File | Line | Exact TODO text | Sentence context | Suggested APA in-text citation |
|---|---|---|---|---|---|---|---|
| 1 | A | Mays (2004); Anderson (2007); Siddiqi (2017) | `01_introduction.md` | 36 | `[TODO: cite Mays 2004; Anderson 2007; Siddiqi 2017]` | "The textbook profit-cut-off literature [TODO] treats profit-curve analysis as a primary scorecard-validation tool…" | `(Mays, 2004; Anderson, 2007; Siddiqi, 2017)` |
| 2 | L+F | Bellotti and Crook (2009); Verbraken et al. (2014) | `01_introduction.md` | 207 | `[TODO: cite Bellotti & Crook 2009; Verbraken et al. 2014]` | "Contribution 2 — A multi-dimensional stress-test design. The bulk of published stress-testing analyses for retail credit profit frameworks vary one or two parameters at a time [TODO]." | `(Bellotti & Crook, 2009; Verbraken et al., 2014)` ⚠ verify Verbraken author list (see flag below) |
| 3 | B | Fawcett (2006) | `02_literature_review.md` | 35 | `[TODO: cite Fawcett 2006 "An introduction to ROC analysis"]` | "…the probability that a randomly chosen positive case is assigned a higher score than a randomly chosen negative case [TODO]." | `(Fawcett, 2006)` |
| 4 | B | Hand and Till (2001) | `02_literature_review.md` | 39 | `[TODO: cite Hand & Till 2001]` | "The AUC is monotonically related to the Gini coefficient via Gini = 2·AUC − 1, so the two metrics measure the same underlying quality and are interchangeable up to a linear transform [TODO]." | `(Hand & Till, 2001)` |
| 5 | (new) | Řezáč and Řezáč (2011) | `02_literature_review.md` | 43 | `[TODO: cite KS treatment in Siddiqi 2017 or Anderson 2007]` | "The Kolmogorov-Smirnov statistic… is a third widely used discrimination metric in the credit-scoring tradition [TODO]." | `(Řezáč & Řezáč, 2011)` — user-locked source for KS / Gini / Lift in credit scoring (per user instruction, do NOT use Hand & Henley 1997) |
| 6 | D | Youden (1950) | `02_literature_review.md` | 47 | `[TODO: cite Youden 1950 "Index for rating diagnostic tests"]` | "The Youden's J statistic [TODO] is the canonical example: J = TPR − FPR…" | `(Youden, 1950)` |
| 7 | G | Elkan (2001) | `02_literature_review.md` | 67 | `[TODO: cite Elkan 2001 "The foundations of cost-sensitive learning"]` | "…the discrimination tradition predates the cost-sensitive learning literature [TODO] by several decades…" | `(Elkan, 2001)` |
| 8 | C | Hand (2009) | `02_literature_review.md` | 72 | `[TODO: cite Hand 2009 "Measuring classifier performance: a coherent alternative to the area under the ROC curve"]` | "The limitations of discrimination-only evaluation have, however, been recognised in the literature for at least two decades [TODO]." | `(Hand, 2009)` |
| 9 | A | Mays (2004) | `02_literature_review.md` | 102 | `[TODO: cite Mays "Credit Scoring for Risk Managers"]` | "Mays (2004) [TODO] devotes a chapter to profit-curve analysis…" | `(Mays, 2004)` (or just `Mays (2004)` since author already in narrative form) |
| 10 | A | Anderson (2007) | `02_literature_review.md` | 106 | `[TODO: cite Anderson "The Credit Scoring Toolkit"]` | "Anderson (2007) [TODO] develops the methodology in more depth…" | `(Anderson, 2007)` / narrative `Anderson (2007)` |
| 11 | A | Siddiqi (2017) | `02_literature_review.md` | 109 | `[TODO: cite Siddiqi "Intelligent Credit Scoring"]` | "Siddiqi (2017) [TODO] extends the framework to risk-based pricing portfolios…" | `(Siddiqi, 2017)` / narrative `Siddiqi (2017)` |
| 12 | F | Verbraken et al. (2014) | `02_literature_review.md` | 161 | `[TODO: cite Verbraken, Verbeke & Baesens 2014 "Expected Maximum Profit framework"]` | "The Expected Maximum Profit (EMP) framework of Verbraken et al. (2014) [TODO] integrates over a probability distribution of cost parameters…" | `(Verbraken et al., 2014)` ⚠ **see FLAG below** — thesis text in the TODO says "Verbraken, Verbeke & Baesens" which is INCORRECT; the actual author list is Verbraken, Bravo, Weber, & Baesens (2014). |
| 13 | H | IASB (2014); Beerbaum (2015) | `02_literature_review.md` | 198 | `[TODO: cite IFRS 9 standard; Beerbaum 2015 "Significant Increase in Credit Risk under IFRS 9"]` | "Lifetime Expected Loss (ECL) measurement entered the regulatory mainstream through the IFRS 9 financial reporting standard… effective from 2018 [TODO]." | `(IASB, 2014; Beerbaum, 2015)` |
| 14 | J | Schuermann (2004); Bellotti and Crook (2012) | `02_literature_review.md` | 229 | `[TODO: cite Schuermann 2004 "What do we know about loss given default?"; Bellotti & Crook 2012 LGD models for unsecured consumer credit]` | "A parallel literature on LGD modelling in unsecured consumer credit [TODO] documents the empirical difficulties of estimating LGD…" | `(Schuermann, 2004; Bellotti & Crook, 2012)` — **keep Bellotti & Crook order; do not reverse** |
| 15 | L | Bellotti and Crook (2009) | `02_literature_review.md` | 277 | `[TODO: cite Bellotti & Crook 2009 "Credit scoring with macroeconomic variables using survival analysis"]` | "First, most published stress-testing analyses vary one or two parameters at a time [TODO]." | `(Bellotti & Crook, 2009)` |
| 16 | G | Elkan (2001) | `02_literature_review.md` | 289 | `[TODO: cite Elkan 2001]` | "Second, cost-sensitive learning [TODO] and cost-sensitive evaluation…" | `(Elkan, 2001)` |
| 17 | F | Verbraken et al. (2014) | `02_literature_review.md` | 290 | `[TODO: cite Verbraken et al. 2014 EMP framework]` | "…cost-sensitive evaluation [TODO] have produced a parallel literature…" | `(Verbraken et al., 2014)` ⚠ same Verbraken author-list FLAG |
| 18 | M (broad use) | Bohn and Stein (2009); Allen & Saunders 2003 unresolved | `02_literature_review.md` | 299 | `[TODO: cite Bohn & Stein 2009 "Active Credit Portfolio Management in Practice"; Allen & Saunders 2003 retail-credit simulation review]` | "Simulation-based credit-risk methodology [TODO] forms a third strand of relevant literature. Simulation has been used to quantify the impact of correlated defaults on portfolio loss distributions…" | `(Bohn & Stein, 2009)` for broad credit portfolio management context — fits user-permitted use case here (broad simulation-based credit-risk methodology, not synthetic-data-isolation argument). Allen & Saunders (2003) remains NEEDS_RESEARCH; can be dropped. |
| 19 | N | Thomas et al. (2002) | `02_literature_review.md` | 332 | `[TODO: cite Thomas, Edelman & Crook 2002 "Credit Scoring and its Applications"; Siddiqi 2006/2017 scorecard development]` | "PD modelling for retail credit has historically been dominated by logistic-regression scorecards [TODO]." | `(Thomas et al., 2002; Siddiqi, 2017)` |
| 20 | O | Ke et al. (2017) | `02_literature_review.md` | 346 | `[TODO: cite Ke et al. 2017 "LightGBM: A Highly Efficient Gradient Boosting Decision Tree"]` | "LightGBM [TODO] and XGBoost…" | `(Ke et al., 2017)` |
| 21 | R | Akiba et al. (2019) | `02_literature_review.md` | 356 | `[TODO: cite Akiba et al. 2019 "Optuna: A Next-generation Hyperparameter Optimization Framework"]` | "Hyperparameter optimisation for the gradient-boosted track is typically performed with a Bayesian-optimisation framework such as Optuna [TODO]." | `(Akiba et al., 2019)` |
| 22 | S | Niculescu-Mizil and Caruana (2005) | `02_literature_review.md` | 363 | `[TODO: cite Niculescu-Mizil & Caruana 2005 "Predicting Good Probabilities with Supervised Learning"]` | "…calibration measures how closely the model's predicted PDs match the empirical default frequencies in equally-binned score ranges [TODO]." | `(Niculescu-Mizil & Caruana, 2005)` |
| 23 | T | Platt (1999) | `02_literature_review.md` | 378 | `[TODO: cite Platt 1999 "Probabilistic Outputs for Support Vector Machines"]` | "Platt scaling [TODO] fits a logistic regression of the binary outcome on the model's raw score…" | `(Platt, 1999)` |
| 24 | A/N | Anderson (2007) and/or Siddiqi (2017) and/or Thomas et al. (2002) | `03_methodology.md` | 243 | `[TODO: cite scorecard literature, e.g. Anderson 2007 or Siddiqi 2017]` | "…the linear track is interpretable and remains familiar to credit-risk regulators and auditors [TODO]." | `(Anderson, 2007; Siddiqi, 2017)` or `(Thomas et al., 2002)` |
| 25 | O | Ke et al. (2017) | `03_methodology.md` | 247 | `[TODO: cite Ke et al. 2017 LightGBM paper]` | "…the LightGBM track captures non-linear interactions… providing an upper bound on the discriminative power available within the locked governance regime [TODO]." | `(Ke et al., 2017)` |
| 26 | R | Akiba et al. (2019) | `03_methodology.md` | 280 | `[TODO: cite Akiba et al. 2019 Optuna]` (TODO continues across lines) | "The retune used Optuna [TODO] with the temporal calibration cohorts as a held-out validation slice…" | `(Akiba et al., 2019)` |
| 27 | T | Platt (1999) | `03_methodology.md` | 295 | `[TODO: cite Platt 1999 "Probabilistic Outputs for Support Vector Machines"]` | "All four base models are calibrated with Platt scaling [TODO]…" | `(Platt, 1999)` |
| 28 | J | Schuermann (2004); Bellotti and Crook (2012) | `03_methodology.md` | 518 | `[TODO: cite Schuermann 2004 or equivalent LGD literature]` | "The 0.65 value reflects an industry baseline for unsecured consumer credit with informal collections [TODO]." | `(Schuermann, 2004; Bellotti & Crook, 2012)` — keep Bellotti & Crook order |
| 29 | A | Mays (2004) | `05_discussion.md` | 205 | `[TODO: cite Mays "Credit Scoring for Risk Managers"]` | "Mays (2004) [TODO] and Anderson (2007) [TODO] both treat profit curves as a primary scorecard-validation tool…" | `Mays (2004)` (already in narrative form) |
| 30 | A | Anderson (2007) | `05_discussion.md` | 206 | `[TODO: cite Anderson "The Credit Scoring Toolkit"]` | (same paragraph as #29) | `Anderson (2007)` (narrative form) |
| 31 | A | Siddiqi (2017) | `05_discussion.md` | 208 | `[TODO: cite Siddiqi "Intelligent Credit Scoring"]` | "…and Siddiqi (2017) [TODO] explicitly recommends profit-based cut-off selection…" | `Siddiqi (2017)` (narrative form) |
| 32 | H | IASB (2014); Beerbaum (2015) | `05_discussion.md` | 239 | `[TODO: cite IFRS 9 ECL literature, e.g., Beerbaum 2015 or Krüger et al. 2018]` | "This extension is also a contribution to the IFRS 9 lifetime expected loss literature [TODO]." | `(IASB, 2014; Beerbaum, 2015)` — keep IASB+Beerbaum; drop the unresolved Krüger reference here |
| 33 | L+F | Bellotti and Crook (2009); Verbraken et al. (2014) | `05_discussion.md` | 255 | `[TODO: cite single-axis sensitivity examples, e.g., Bellotti & Crook 2009 or Verbraken et al. 2014]` | "The bulk of published stress-testing analyses for retail credit profit frameworks vary one or two parameters at a time [TODO]." | `(Bellotti & Crook, 2009; Verbraken et al., 2014)` ⚠ Verbraken author-list FLAG |

---

## WORDING_FIX markers (4)

| # | Group | File | Line | Current sentence | Problem | Suggested wording fix |
|---|---|---|---|---|---|---|
| 1 | (meta) | `02_literature_review.md` | 16 | "Citations are flagged as `[TODO: cite]` placeholders throughout; the citation map will be finalised before submission." | After the citation pass replaces all real TODO markers, this sentence describing the convention becomes self-contradictory. | Replace with a static description, e.g. "Citation entries follow APA 7th edition; the full reference list appears at the end of the thesis." Apply during citation pass. |
| 2 | M (Bohn & Stein context) | `03_methodology.md` | 136 | "A simulated portfolio isolates the methodological question from data-quality, regulatory, and proprietary-data confounds that would dominate any single real-world dataset [TODO: cite simulation-based credit-risk methodology, e.g. Bohn & Stein 2009]." | The sentence frames Bohn & Stein (2009) as supporting **synthetic-data methodology / methodology-isolation**, but per user instruction Bohn & Stein (2009) is locked only for **broad credit portfolio management / quantitative credit-risk methodology**. Citing it for the methodology-isolation argument exceeds the source's scope. | Two options: (a) Soften wording to "Simulation has been used in credit-risk portfolio management for related purposes [TODO: cite Bohn & Stein 2009]" and remove the methodology-isolation claim from the cited sentence; or (b) Drop the citation here and treat the methodology-isolation claim as an internal positioning statement supported by Chapter 5 §5.4. Recommended: option (a). |
| 3 | AA | `04_results.md` | 541 | "Op_cost levels were chosen to span the practical range of consumer-lending operations (1-4% of outstanding per year is a common range cited in industry literature [TODO: cite banking operating-cost benchmarks — HIGH PRIORITY])." | No verified source exists for the "1-5% operating-cost range" claim. Per user instruction Group AA, do NOT force a weak citation; instead soften the wording. | Replace "is a common range cited in industry literature" with "is the practical range tested in this thesis"; or "approximates the operating-cost band typically reported for consumer-lending operations" with no citation. The 1-4% (or 1-5%) numerical range is retained but the empirical-benchmark claim is removed. |
| 4 | AA | `06_limitations.md` | 222 | "Real lending operations typically incur op_cost in the 1-5% range [TODO: cite banking operating-cost benchmarks; same source as Chapter 4 §4.6]; the base case's `op_cost = 0` is unrealistic for production deployment." | Same as #3 — Group AA. Per user instruction, no source available; soften wording. | Replace "Real lending operations typically incur op_cost in the 1-5% range [TODO …]" with "Operating-cost ranges between 1% and 5% are the regime examined under Future Work F5 / the Phase 4.2 PART B sensitivity grid"; or drop the empirical-range claim and refer the reader to the Phase 4.2 PART B grid for the explicit op_cost levels tested. |

---

## NEEDS_RESEARCH markers (17)

Grouped by topic. Each group represents a true remaining LOW-priority research item where no approved source is yet available.

### Group E — Tenor-aware credit risk

- **Likely source type needed**: book / journal article
- **Markers**:
  - `02_literature_review.md`, line 153: "More recent work in tenor-aware credit-risk modelling has emphasised that this single-period approximation systematically under-weights longer-tenor loans because amortization and survival weighting are ignored [TODO: cite tenor-aware credit risk literature, e.g., Krüger & Rösch 2017 or Bellini 2019]."
- **Research notes**: TODO names two candidate sources (Krüger & Rösch 2017; Bellini 2019) but exact titles / venues are not given. If neither source is confirmable, soften wording to "...systematically under-weights longer-tenor loans..." with no citation (the claim is mechanical and self-evident from the formula).

### Group I — IFRS 9 implementation

- **Likely source type needed**: book / regulator-adjacent publication
- **Markers**:
  - `02_literature_review.md`, line 214: "The IFRS 9 standard has produced a substantial implementation literature in retail credit modelling [TODO: cite Krüger, Rösch & Scheule 2018 IFRS 9 implementation; PwC 2017 IFRS 9 implementation guidance; Skoglund 2017 'Implementing Credit Risk Models for IFRS 9']."
- **Research notes**: Three candidates named. If a single canonical text is selected (Krüger, Rösch & Scheule is a likely candidate), the other two can be dropped. Alternatively, if none is confirmable, generalise to "produced a substantial implementation literature" with no citation.

### Group K — Stress-testing regulatory standards

- **Likely source type needed**: regulatory document (BCBS / Federal Reserve / EBA)
- **Markers**:
  - `02_literature_review.md`, line 269: "Stress testing in retail credit risk is a long-established practice, both for regulatory capital purposes (Basel II/III stress tests, CCAR/DFAST in the United States, EBA stress tests in Europe) [TODO: cite Basel stress-testing principles BCBS 2018; CCAR/DFAST methodology; EBA stress test methodology]."
- **Research notes**: Need specific BCBS / Federal Reserve / EBA document references. Public documents but exact citation form (year, document number, title) must be confirmed. If none confirmable in time, drop the parenthetical citation; the regulatory practices are common knowledge and the sentence stands.

### Group P — XGBoost

- **Likely source type needed**: conference paper
- **Markers**:
  - `02_literature_review.md`, line 348: "LightGBM [TODO: cite Ke et al. 2017 …] and XGBoost [TODO: cite Chen & Guestrin 2016 'XGBoost: A Scalable Tree Boosting System']…"
- **Research notes**: KDD 2016 paper widely known. If not confirmable, may drop the XGBoost citation entirely since XGBoost is mentioned only as a comparator to LightGBM and is not used in the thesis pipeline.

### Group Q — LightGBM-vs-LR empirical comparisons

- **Likely source type needed**: journal / conference paper (representative meta-comparison)
- **Markers**:
  - `02_literature_review.md`, line 353: "…both consistently outperform logistic-regression scorecards on discrimination metrics by a measurable margin in published benchmarks [TODO: cite credit-risk LightGBM-versus-LR empirical comparisons]."
- **Research notes**: No specific source named. Candidate: Lessmann et al. (2015) *Benchmarking state-of-the-art classification algorithms for credit scoring* (European Journal of Operational Research). If neither Lessmann 2015 nor a similar meta-study is confirmable, soften wording to "outperform logistic-regression scorecards on discrimination metrics in published benchmarks" with no citation.

### Group U — Isotonic regression

- **Likely source type needed**: conference paper
- **Markers**:
  - `02_literature_review.md`, line 382: "Isotonic regression [TODO: cite Zadrozny & Elkan 2002 'Transforming classifier scores into accurate multi-class probability estimates']…"
- **Research notes**: KDD 2002 paper. If not confirmable, may drop the citation since isotonic regression is mentioned only as an alternative to Platt and is not used in the thesis.

### Group V — Synthetic-data methodology in healthcare

- **Likely source type needed**: conference paper
- **Markers**:
  - `02_literature_review.md`, line 421: "…canonical examples are healthcare (HIPAA-restricted patient data) [TODO: cite Patki et al. 2016 'The Synthetic Data Vault'; Choi et al. 2017 medGAN]…"
- **Research notes**: Two candidates (IEEE DSAA 2016 + MLHC 2017). If not confirmable, the sentence can stand as a general assertion about synthetic-data adoption in healthcare with no citation.

### Group W — Synthetic-data methodology in finance / order books

- **Likely source type needed**: working paper / preprint
- **Markers**:
  - `02_literature_review.md`, line 423: "…high-frequency finance (proprietary order-book data) [TODO: cite Buehler et al. 2020 synthetic order-book generators]."
- **Research notes**: No exact title supplied. If unconfirmable, drop the citation; the parenthetical example is illustrative only.

### Group X — Synthetic-data methodology for fair-lending

- **Likely source type needed**: conference paper
- **Markers**:
  - `02_literature_review.md`, line 429: "…to evaluate fair-lending interventions or to stress-test scoring algorithms against rare adverse scenarios that real data does not contain [TODO: cite synthetic-data fair-lending literature, e.g., Hardt, Price & Srebro 2016 or Bellamy et al. 2018 IBM AIF360]."
- **Research notes**: Two candidates. If neither confirmable, drop the citation; the claim about fair-lending interventions is a survey statement that can stand on its own.

### Group Y — Reject inference

- **Likely source type needed**: journal article
- **Markers**:
  - `02_literature_review.md`, line 447: "…not the full applicant population. The cut-off optimisation question … is structurally hard to answer on a sample-selected dataset without reject-inference techniques whose own assumptions are difficult to validate [TODO: cite Crook & Banasik 2004]."
- **Research notes**: Likely *Journal of Banking and Finance* (Crook & Banasik 2004 "Does reject inference really improve the performance of application scoring models?"). If unconfirmable, soften to "…without reject-inference techniques whose assumptions are difficult to validate." with no citation.

### Group Z — Risk-based pricing literature

- **Likely source type needed**: journal article and/or book
- **Markers**:
  - `05_discussion.md`, line 170: "…tiered risk-priced APR generates higher portfolio profit than flat pricing at comparable nominal APR levels because the tiered scheme charges higher APR on higher-PD borrowers. This finding is directionally consistent with conventional risk-based pricing literature [TODO: cite risk-based pricing literature, e.g., Edelberg 2006 or Phillips 2018]…"
- **Research notes**: Two candidates (Edelberg 2006 = *Journal of Monetary Economics*; Phillips 2018 = *Pricing Credit Products* book). If neither confirmable, soften to "directionally consistent with conventional risk-based pricing reasoning" with no citation.

### Group AB — APR market survey (Federal Reserve G.19)

- **Likely source type needed**: regulatory statistical release
- **Markers**:
  - `03_methodology.md`, line 498: "The tier values are informed by typical published APR ranges for unsecured consumer credit [TODO: cite real-market APR survey, e.g., Federal Reserve G.19 release or EU equivalent]…"
- **Research notes**: Federal Reserve Statistical Release G.19 *Consumer Credit Outstanding* is public; exact citation form (year, release date) needed. If preferred, the thesis can cite a year-specific G.19 release or replace with a softened wording: "typical published APR ranges for unsecured consumer credit" with no specific source.

### Group AC — Basel III PD horizon

- **Likely source type needed**: BCBS document
- **Markers**:
  - `03_methodology.md`, line 109: "This 12-month forward target is the empirical operationalisation of 'default within one year of observation' used throughout the thesis [TODO: cite Basel III Probability of Default horizon convention]."
- **Research notes**: BCBS publication needed (e.g., BCBS 2017 *Basel III: Finalising post-crisis reforms*). If unconfirmable, soften to "the empirical operationalisation of 'default within one year of observation', a standard convention in retail credit risk."

### Group AD — Lasso / sparse regression methodology

- **Likely source type needed**: textbook
- **Markers**:
  - `03_methodology.md`, line 266: "…Cross-Validated Lasso which is well-known to exhibit instability for selection at low default rates [TODO: cite Hastie, Tibshirani & Wainwright 2015]."
- **Research notes**: Hastie, Tibshirani & Wainwright (2015) *Statistical Learning with Sparsity: The Lasso and Generalizations* (CRC Press). Standard reference; if confirmable, use this exact form. If not, fall back to Hastie, Tibshirani & Friedman (2009) *The Elements of Statistical Learning* (2nd ed.).

### Group AE — Simulator repository

- **Likely source type needed**: software / repository self-citation
- **Markers**:
  - `03_methodology.md`, line 33: "All empirical results in this thesis derive from a single production run of the synthetic `rl-debt-collection` simulator [TODO: cite simulator repository / authoring]…"
- **Research notes**: If the simulator is the thesis author's own work, a self-citation to a GitHub / Zenodo DOI is appropriate. If the simulator is third-party, the original author / repository URL is needed. User decision required.

### Group AF — Zero-interest simulator assumption

- **Likely source type needed**: not necessarily a citation
- **Markers**:
  - `03_methodology.md`, line 70: "…the simulator does not implement interest on the loan economic stage [TODO: cite zero-interest assumption discussion in simulator design document or related literature]."
- **Research notes**: No clear external source. Recommended: drop the citation and replace with an internal reference to the simulator's design documentation (or a single sentence noting that the simulator omits interest income and that APR is supplied exogenously by the thesis's economic framework).

### Group AG — Percentile bootstrap method (NEW group, not in `citation_pass_inventory.md`)

- **Likely source type needed**: textbook
- **Markers**:
  - `04_results.md`, line 392: "This is the strongest within-OOT sampling-based evidence the bootstrap framework can generate for the central thesis hypothesis [TODO: cite Efron & Tibshirani 1993 percentile bootstrap method]."
- **Research notes**: Efron & Tibshirani (1993) *An Introduction to the Bootstrap* (Chapman & Hall). Standard methodological reference for percentile bootstrap. Confirm exact citation form. If unconfirmable, the percentile-bootstrap methodology is standard enough that a citation may be omitted with no loss of rigour.

### Group M — Allen & Saunders (2003) — partial

- **Likely source type needed**: review article
- **Markers** (carry-over from LOCKED_SOURCE row #18 above): the LOCKED_SOURCE marker at `02_literature_review.md` line 299 cites both Bohn & Stein (2009) and Allen & Saunders (2003). Only Bohn & Stein (2009) is locked. Allen & Saunders (2003) "retail-credit simulation review" is **unresolved** and can be dropped without weakening the locked Bohn & Stein anchor.
- **Research notes**: If a "retail-credit simulation review" by Allen & Saunders (2003) is confirmable, retain; otherwise drop without replacement.

---

## FLAGS (require user decision)

| Flag | Detail |
|---|---|
| F1 | **Verbraken et al. (2014) author order** — the thesis text writes "Verbraken, Verbeke & Baesens" in the TODOs at Ch2 lines 161 and 290 (and via "Verbraken et al." at Ch1 line 207 and Ch5 line 255). The correct author list is **Verbraken, Bravo, Weber, & Baesens (2014)**. Citation pass must use the correct form, even though the TODO text is wrong. |
| F2 | **Bellotti and Crook (2012)** — keep this author order; do NOT reverse to "Crook & Bellotti". Applies to Ch2 line 229 and Ch3 line 518. |
| F3 | **Bohn and Stein (2009)** — locked source ONLY for broad credit portfolio management / quantitative credit-risk methodology. The use at Ch2 line 299 ("Simulation-based credit-risk methodology forms a third strand") fits this scope. The use at Ch3 line 136 ("A simulated portfolio isolates the methodological question from data-quality… confounds") exceeds this scope — classified as WORDING_FIX (see WORDING_FIX row #2). |
| F4 | **Group AA (op_cost benchmark)** — per user instruction, do NOT force a weak citation. Both occurrences (Ch4 line 541, Ch6 line 222) classified as WORDING_FIX. |
| F5 | **Meta-reference at Ch2 line 16** — `[TODO: cite]` inside backticks is the text explaining the convention itself. Classified as WORDING_FIX (rewrite the sentence during citation pass since the convention is no longer in force in the final version). |
| F6 | **KS metric (Ch2 line 43)** — TODO names "Siddiqi 2017 or Anderson 2007" but per user instruction, the canonical source for credit-scoring metrics including KS / Gini / Lift is **Řezáč and Řezáč (2011)** — used here. Do NOT use Hand & Henley (1997). |

---

## Verification

| Check | Result |
|---|---|
| Total TODO markers found | **54** (4 more than the `citation_pass_inventory.md` count of 50 due to multi-line-spanning TODOs missed by the narrow grep pattern) |
| Every TODO appears in exactly one of LOCKED_SOURCE / WORDING_FIX / NEEDS_RESEARCH | ✅ 33 + 4 + 17 = 54 |
| Chapter files modified | ❌ none |
| References list created | ❌ no |
| Citation replacements applied | ❌ no |
| New bibliographic details invented | ❌ no (all entries are either user-locked or marked NEEDS_RESEARCH) |
| Inventory only? | ✅ yes |

---

**End of inventory. No chapter files modified; no citations replaced; no References list created.**
