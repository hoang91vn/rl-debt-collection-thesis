# Global Consistency Audit — Thesis Pre-Submission Report

**Date**: 2026-05-11
**Phase**: 7 (Global Consistency Pass)
**Scope**: Abstract + Chapters 1-6 (7 markdown files; ~28,000 words)
**Verification only — no chapter files modified during this audit**

---

## Overall verdict

**READY for supervisor handoff after two consistency fixes were
applied (Fix 1 + Fix 3 — see Applied Fixes section at the end).**
The HIGH-PRIORITY operating-cost benchmark citation (Fix 2) is
deferred to the broader citation pass per the user's instruction.
The thesis is internally consistent on numbers, section references,
hedge wording, and Table/Figure references; all 9 publication
figures are now referenced in chapter prose.

---

## Task 1 — Section Reference Audit

### Section structure (verified)

All chapter sections verified to exist as expected from the writing
briefings:

| Chapter | Sections present | Match expected? |
|---|---|---|
| Ch1 Introduction | §1.1 Motivation; §1.2 Research Question; §1.3 Thesis Claim; §1.4 Contributions; §1.5 Methodology Overview; §1.6 Findings Preview; §1.7 Thesis Structure | ✅ |
| Ch2 Literature Review | §2.1 Discrimination-driven cut-off selection; §2.2 Profit-driven cut-off selection; §2.3 Lifetime Expected Loss and IFRS 9; §2.4 Stress testing methodology; §2.5 PD modelling and calibration; §2.6 Synthetic data; §2.7 Summary of literature gap | ✅ |
| Ch3 Methodology | §3.1 Data Generation; §3.2 Feature Engineering; §3.3 PD Modelling; §3.4 Economic Framework; §3.5 Stress Testing Design; §3.6 Bootstrap Validation; §3.7 Software Architecture | ✅ |
| Ch4 Results | §4.1 PD Modelling Results; §4.2 Base Economic Results; §4.3 Stress Test Results (Phase 3.2); §4.4 Bootstrap CI Results (Phase 4.1); §4.5 PD Quality Stress (PART A); §4.6 Operating-cost Robustness (PART B); §4.7 Combined Stress (PART C) | ✅ |
| Ch5 Discussion | §5.1 Synthesis; §5.2 Implications; §5.3 Comparison with Existing Literature; §5.4 Methodological Positioning; §5.5 Boundary Conditions; §5.6 Future Research Directions | ✅ |
| Ch6 Limitations & Future Work | §6.1 Limitations; §6.2 Future Work; §6.3 Summary of Future Work prioritisation; §6.4 Closing remark | ✅ |

### Phantom-section scan

Searched for §X.8, §X.9 (i.e., references beyond the actual section
counts), §7.X, and "Chapter 7": **0 matches**. No phantom sections.

### Cross-reference scan

- 170 `§X.Y` references across 5 chapters (Ch3 has none, which is
  consistent — Ch3 is the methodology chapter and does not
  forward-reference Ch4-6).
- All `Chapter X §X.Y` forward references in Ch1 (~40) and Ch2 (~25)
  land on existing sections. Sample:
  - Ch1 §1.7 references Chapter 4 §4.1 through §4.7 — all exist
  - Ch1 §1.7 references Chapter 5 §5.2 through §5.6 — all exist
  - Ch1 §1.7 references Chapter 6 §6.1, §6.2 — all exist
  - Ch2 §2.7 Gap-to-Contribution map references Ch3 §3.4, §3.6;
    Ch4 §4.2-§4.7; Ch6 §6.2 — all exist

### Section-reference scheme compliance (cumulative wording lock)

Verified per-section meanings remain consistent across all chapters:

| Section | Topic | Verified across |
|---|---|---|
| §3.1 | Data generation | Ch1, Ch2, Ch3, Ch6 — consistent |
| §3.2 | Feature engineering / wide ABT / score-scorem exclusion | Ch1, Ch5, Ch6 — consistent |
| §3.3 | PD modelling + calibration | Ch1, Ch2, Ch4, Ch5, Ch6 — consistent |
| §3.4 | Economic framework / APR / LGD / formulas | Ch1, Ch2, Ch4, Ch5, Ch6 — consistent (no residual §3.6 or §3.7 mis-references) |
| §3.5 | Stress testing design | Ch1, Ch2, Ch4 — consistent |
| §3.6 | Bootstrap validation | Ch1, Ch2, Ch4, Ch5, Ch6 — consistent |
| §3.7 | Software architecture | Ch1, Ch2, Ch6 — consistent |

**Verdict for Task 1: ✅ PASS — no inconsistencies.**

---

## Task 2 — Number Audit

Each headline number traced across all chapters where it appears.
Where a chapter doesn't reference a particular number, the number
appears in the row but not the chapter column.

| Number | Source value | Abstract | Ch1 | Ch2 | Ch3 | Ch4 | Ch5 | Ch6 | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Modelling rows | 534,314 | ✓ | ✓ | ✓ | ✓ (Table 3.2) | ✓ | — | ✓ | ✅ consistent |
| Economic-analysis rows | 235,968 | ✓ | ✓ | ✓ | ✓ | ✓ (Table 4.2/4.3) | ✓ | ✓ | ✅ consistent |
| OOT economics rows | 64,027 | ✓ | ✓ | ✓ | ✓ (Table 3.4b) | ✓ (Tables 4.6-4.8) | ✓ | ✓ | ✅ consistent |
| 12-month loans excluded | 298,346 | — | — | — | ✓ (line 418, 421) | — | — | ✓ (line 62) | ✅ consistent (only 2 chapters use this number) |
| Full OOT split | 144,789 | — | — | — | ✓ (line 115, 323, 346) | ✓ (line 60) | — | — | ✅ consistent (only Ch3 Table 3.4a + Ch4 §4.1) |
| Economic stress grid | 576-cell | — | ✓ | ✓ | ✓ | ✓ (Table 4.4) | ✓ | — | ✅ consistent |
| Phase 4.2 stress space | 64-cell | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ consistent |
| Bootstrap-anchor combinations | 4,000 | ✓ | ✓ | — | — | ✓ | ✓ | — | ✅ consistent |
| Resamples per anchor | 1,000 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ consistent |
| Cut-off gap @ raw Gini | +15.5 pp | ✓ | ✓ | — | ✓ (line 591) | ✓ (Table 4.7) | ✓ | — | ✅ consistent |
| Cut-off gap @ Gini 0.30 | +35.7 pp | ✓ | ✓ | — | ✓ (line 591) | ✓ (Table 4.7) | ✓ | — | ✅ consistent |
| ASB understatement on 36m | ~40% | ✓ | ✓ | — | — | ✓ (derived from line 174 ratio: 71% combined; 0.60 on 36m → 40% understatement) | ✓ | — | ✅ consistent |
| Calibration ratio (LightGBM) | 0.49 | — | ✓ | ✓ | ✓ (Table 3.4b) | ✓ | ✓ | ✓ | ✅ consistent |
| Dollar uplift range | $0.46M to $30.75M | — | ✓ | — | — | ✓ (Table 4.6) | ✓ | — | ✅ consistent |
| Reject-most k* | 0.31% | — | ✓ | — | ✓ (line 604) | ✓ (Table 4.8) | ✓ | — | ✅ consistent |
| Reject-most mean profit | −$387 | — | ✓ | — | — | ✓ (Table 4.8) | ✓ | — | ✅ consistent |
| Reject-most total profit | −$24.8M | — | ✓ | — | — | ✓ (Table 4.8) | ✓ | — | ✅ consistent |
| Lifetime portfolio profit | $352.3M | — | ✓ | — | — | ✓ (line 151, Table 4.3) | ✓ | — | ✅ consistent |
| ASB portfolio profit | $250.9M | — | ✓ | — | — | ✓ (line 174) | ✓ | — | ✅ consistent |
| ASB/Lifetime ratio (24m) | 0.91 | — | ✓ | — | — | ✓ (Table 4.3) | ✓ | — | ✅ consistent |
| ASB/Lifetime ratio (36m) | 0.60 | — | ✓ | — | — | ✓ (Table 4.3) | ✓ | — | ✅ consistent |
| APR-strategy spread on k* | 2.32 pp | — | — | — | ✓ (line 551) | ✓ (Table 4.5, line 273, 307) | ✓ | ✓ | ✅ consistent |
| LGD spread on k* | 1.28 pp | — | — | — | ✓ (line 551) | ✓ (Table 4.5, line 274, 309) | — | ✓ | ✅ consistent |
| Mean profit per account | $1,493 | — | — | — | — | ✓ (line 144, 166) | — | ✓ (line 226) | ✅ consistent |

**Verdict for Task 2: ✅ PASS — all 22 audited numbers consistent
across chapters. No drift, no typos, no rounding inconsistencies.**

---

## Task 3 — TODO Citation Consolidation

**Total `[TODO: cite]` markers found: 50** across the 7 files.
Distribution:

| Chapter | TODO cite count |
|---|---|
| Abstract | 0 (by rule) |
| Ch1 | 2 |
| Ch2 | 30 |
| Ch3 | ~10 |
| Ch4 | 2 |
| Ch5 | 5 |
| Ch6 | 1 |

### Grouped citation table (cross-chapter consolidation)

| Group | Sources cited | Chapters | Cross-ref priority |
|---|---|---|---|
| **A — Profit-cut-off textbook tradition** | Mays 2004; Anderson 2007; Siddiqi 2017 | Ch1 §1.1; Ch2 §2.1, §2.2; Ch3 §3.3; Ch5 §5.3 | Same source group cited in 4 chapters — single bibliography entries |
| **B — Discrimination metrics / ROC** | Fawcett 2006; Hand & Till 2001 | Ch2 §2.1 | Single chapter |
| **C — Hand 2009 critique** | Hand 2009 (AUC critique) | Ch2 §2.1 | Single chapter |
| **D — Youden's J origin** | Youden 1950 | Ch2 §2.1 | Single chapter |
| **E — Tenor-aware credit risk** | Krüger & Rösch 2017; Bellini 2019 | Ch2 §2.2 | Single chapter |
| **F — EMP framework** | Verbraken, Verbeke & Baesens 2014 | Ch2 §2.2 + §2.4 | Same source cited twice in same chapter |
| **G — Cost-sensitive learning** | Elkan 2001 | Ch2 §2.1 + §2.4 | Same source cited twice in same chapter |
| **H — IFRS 9 standard** | IFRS 9; Beerbaum 2015 | Ch2 §2.3; Ch5 §5.3 | Cross-chapter — single bibliography entry |
| **I — IFRS 9 implementation** | Krüger, Rösch & Scheule 2018; PwC 2017; Skoglund 2017 | Ch2 §2.3 | Single chapter |
| **J — LGD modelling** | Schuermann 2004; Bellotti & Crook 2012 | Ch2 §2.3 | Single chapter |
| **K — Stress-testing regulatory** | Basel III BCBS 2018; CCAR/DFAST; EBA stress test | Ch2 §2.4 | Single chapter |
| **L — Single-axis sensitivity in profit-curve research** | Bellotti & Crook 2009 | Ch2 §2.4; Ch5 §5.3 | Cross-chapter |
| **M — Simulation-based credit risk** | Bohn & Stein 2009; Allen & Saunders 2003 | Ch2 §2.4; Ch3 §3.1 | Cross-chapter |
| **N — Scorecard tradition** | Thomas, Edelman & Crook 2002; Siddiqi 2006 | Ch2 §2.5; Ch3 §3.3 | Cross-chapter — Siddiqi 2006/2017 may be same author multi-edition |
| **O — LightGBM** | Ke et al. 2017 | Ch2 §2.5; Ch3 §3.3 | Cross-chapter |
| **P — XGBoost** | Chen & Guestrin 2016 | Ch2 §2.5 | Single chapter |
| **Q — LightGBM-vs-LR empirical comparisons** | TBD | Ch2 §2.5 | Generic — need a representative paper |
| **R — Optuna** | Akiba et al. 2019 | Ch2 §2.5; Ch3 §3.3 | Cross-chapter |
| **S — Discrimination vs calibration** | Niculescu-Mizil & Caruana 2005 | Ch2 §2.5 | Single chapter |
| **T — Platt scaling** | Platt 1999 | Ch2 §2.5; Ch3 §3.3 | Cross-chapter |
| **U — Isotonic regression** | Zadrozny & Elkan 2002 | Ch2 §2.5 | Single chapter |
| **V — Synthetic data healthcare** | Patki et al. 2016; Choi et al. 2017 medGAN | Ch2 §2.6 | Single chapter |
| **W — Synthetic data finance** | Buehler et al. 2020 | Ch2 §2.6 | Single chapter |
| **X — Synthetic fair-lending** | Hardt, Price & Srebro 2016; Bellamy et al. 2018 (IBM AIF360) | Ch2 §2.6 | Single chapter |
| **Y — Reject inference** | Crook & Banasik 2004 | Ch2 §2.6 | Single chapter |
| **Z — Risk-based pricing** | Edelberg 2006; Phillips 2018 | Ch5 §5.2 | Single chapter |
| **AA — Operating cost benchmarks** | TBD | **Ch4 §4.6 + Ch6 §6.1 Limitation 7** | **🔴 HIGH PRIORITY (flagged in 2 chapters; required for empirical interpretation)** |
| **AB — APR market survey** | Federal Reserve G.19 | Ch3 §3.4 | Single chapter |
| **AC — Basel III PD framework** | Basel III PD definitions | Ch3 §3.3 | Single chapter |
| **AD — Lasso / sparse regression** | Hastie, Tibshirani & Friedman | Ch3 §3.3 | Single chapter |
| **AE — Simulator repository** | TBD (own simulator) | Ch3 §3.1 | Possibly own work — needs author/repo URL |
| **AF — Zero-interest assumption** | TBD | Ch3 §3.1 | Need representative paper |

### HIGH-PRIORITY citation flagged

**Group AA — Operating cost benchmarks** is the only group flagged
HIGH PRIORITY across two chapters:
- Chapter 4 §4.6 (line 531): "banking operating-cost benchmarks —
  HIGH PRIORITY: a defensible source for the 1-5% op_cost range"
- Chapter 6 §6.1 Limitation 7 (line 217): "[TODO: cite banking
  operating-cost benchmarks; same source as Chapter 4 §4.6]"

Both flag the same gap (no citation backing the "1-5% operating cost
range" empirical claim). A single canonical source — e.g., a McKinsey
banking cost benchmark, Federal Reserve cost-to-income ratio data, or
EBA retail-bank operating cost statistics — would resolve both.

**Verdict for Task 3: ✅ PASS — 50 markers consolidated into 32
groups; 1 HIGH-PRIORITY citation gap (op_cost benchmark).**

---

## Task 4 — "Within Tested Scenario Space" Enforcement

**Total occurrences: 16 lines** across all 7 files (Abstract: 1;
Ch1: 3; Ch2: 2; Ch3: 1; Ch4: 3; Ch5: 7; Ch6: 1).

| Required location (per user briefing) | Hedge present? | Line ref |
|---|---|---|
| Abstract | ✅ | line 27 |
| Chapter 1 §1.3 (Thesis Claim) | ✅ | lines 149, 171 |
| Chapter 4 §4.7 (refined claim) | ✅ | line 505 ("a profit-anchored cut-off*. Within the tested scenario space, banks…") |
| Chapter 5 §5.1 (Synthesis) | ✅ | line 64 ("Within the tested scenario space, the framework's dollar advantage…") |
| Chapter 5 §5.2 (Implications) | ✅ | line 166 ("Within the tested scenario space, tiered…"); also line 187 (Implication 4 boundary) |
| Chapter 5 §5.5 (Boundary Conditions) | ✅ | line 400 (first bullet header: "**Within the tested scenario space.**") |
| Chapter 6 §6.1 (Limitations) | ⚠ implicit | The phrase is not explicitly used in §6.1 — but each Limitation's "Scope of impact" enforces an equivalent boundary. The §6.4 Closing remark (line 637) does state the hedge explicitly. Acceptable. |
| Chapter 6 §6.4 (Closing remark) | ✅ | line 637 |

**Forbidden universal-claim scan**: 0 violations. The 4 surface-level
hits returned (Ch1 line 154 "universal real-market law"; Ch5 line 75
"always prescribed"; Ch4 line 303 "always approve" rule; Ch4 line 579
"framework that always") are all in negating contexts that explain
why the phrase is rejected — these are the user-approved boundary
statements, not violations.

**Verdict for Task 4: ✅ PASS — hedge enforcement complete; one
chapter (Ch6 §6.1) uses implicit per-Limitation boundary language
rather than the verbatim phrase, which is acceptable given the
Limitation structure.**

---

## Task 5 — 12-Month Consistency Check

**Search for `twelve-month` (case-insensitive): 0 matches** across
all 7 files.

**`12-month` form**: used consistently throughout for both the loan
tenor (12-month loans) and the target window (12-month forward
default flag).

**Verdict for Task 5: ✅ PASS — full consistency.**

---

## Task 6 — Tables / Figures Inventory

### Tables defined (in chapter prose, with `**Table X.Y —**` heading)

| Table | Location | Topic | Referenced where |
|---|---|---|---|
| Table 3.1 | Ch3 line 82 | Locked production-run configuration | Ch3 line 75 |
| Table 3.2 | Ch3 line 120 | Population definitions | Ch3 line 113 |
| Table 3.3 | Ch3 line 159 | Generated feature families | Ch3 line 155 |
| Table 3.4a | Ch3 line 346 | Discrimination on full OOT split | Ch3 line 322; Ch4 line 59 |
| Table 3.4b | Ch3 line 364 | Calibration on eco-OOT subset | Ch3 line 322, 361, 379; Ch4 lines 63, 68; Ch5 line 422; Ch6 line 187 |
| Table 3.5 | Ch3 line 502 | Locked APR tier table | Ch3 line 492; Ch5 lines 450, 542; Ch6 lines 89, 511 |
| Table 3.6 | Ch3 line 570 | Locked anchor scenarios | Ch3 line 561; Ch4 line 280 |
| Table 3.7 | Ch3 line 651 | Bootstrap CIs for cutoff gap | Ch3 line 641; Ch4 line 349 |
| Table 4.1 | Ch4 line 45 | Linear-track Stage 1/2/3 selection funnel | Ch4 line 37 |
| Table 4.2 | Ch4 line 134 | Base-scenario per-account distributions | Ch4 line 129 |
| Table 4.3 | Ch4 line 159 | Tenor-stratified base economics | Ch4 line 152 |
| Table 4.4 | Ch4 line 252 | Phase 3.2 576-cell stress grid summary | Ch4 line 241 |
| Table 4.5 | Ch4 line 268 | Driver hierarchy | Ch4 line 247; Ch5 line 159; Ch6 lines 101, 130, 524 |
| Table 4.6 | Ch4 line 352 | Bootstrap 95% CIs for cut-off metrics | Ch4 lines 349, 392, 728; Ch5 lines 45, 129; Ch6 lines 41, 325 |
| Table 4.7 | Ch4 line 452 | Cut-off gap by PD discrimination Gini | Ch4 line 446; Ch5 lines 58, 131 |
| Table 4.8 | Ch4 line 546 | Op_cost robustness | Ch4 lines 542, 566 |
| Table 4.9 | Ch4 line 662 | Phase 4.2 combined PART C grid | (referenced in §4.7 context line 661) |

**All 17 tables defined and all referenced. No orphan tables.**

### Figures saved on disk (`artifacts/figures/`)

| File | PDF size | PNG size | Referenced in chapter prose? |
|---|---|---|---|
| `fig1_profit_curves.{pdf,png}` | 41 KB / 111 KB | — | ❌ **ORPHAN — never cited as "Figure 1" in any chapter** |
| `fig2_cutoff_gap_vs_gini` | 22 KB / 97 KB | — | ✅ Ch4 line 463; Ch5 line 58 |
| `fig3_op_cost_vs_kstar` | 25 KB / 88 KB | — | ✅ Ch4 line 564 |
| `fig4_asb_vs_lifetime` | 21 KB / 52 KB | — | ✅ Ch4 line 168; Ch5 line 88 |
| `fig5_bootstrap_ci_density` | 34 KB / 129 KB | — | ✅ Ch3 line 662; Ch4 line 364 |
| `fig6_reliability_diagrams` | 24 KB / 175 KB | — | ✅ Ch3 line 341 |
| `fig7_feature_importance` | 22 KB / 173 KB | — | ✅ Ch3 line 343 |
| `fig8_stress_heatmap` | 36 KB / 97 KB | — | ✅ Ch4 line 676 |
| `fig9_sensitivity_hierarchy` | 18 KB / 46 KB | — | ✅ Ch4 lines 247, 278; Ch5 line 159 |

### 🔴 BLOCKING FINDING: Orphan Figure 1

`fig1_profit_curves.{pdf,png}` is saved as a publication-ready figure
but **is not cited as "Figure 1" anywhere in chapter prose**. The
file exists at `artifacts/figures/fig1_profit_curves.pdf`
(41 KB) and `.png` (111 KB), and is implicitly described in Ch4 §4.2
(which mentions "the cumulative profit curve" at lines 184 and 612)
but the explicit `Figure 1` reference is missing.

**Recommended fix**: add a single sentence in Ch4 §4.2 (the natural
home for the profit-curve visualisation) explicitly citing Figure 1.
Suggested insertion point: near line 168 (where Figure 4 is already
cited), or in the discussion of the cumulative profit curve at
line 184.

**Verdict for Task 6: ⚠ ONE BLOCKING ITEM — Figure 1 orphan;
all other 16 tables and 8 figures referenced correctly.**

---

## Task 7 — Forward Reference Closure

### Chapter 1 forward references (~40 unique cross-chapter refs)

Verified that every `Chapter X §X.Y` reference in Ch1 lands on an
existing section. Sample audit:
- §1.1 → "Future Work catalogue (Chapter 6, F2 and F7)" ✅
- §1.2 sub-questions → Ch4 §4.2, §4.3, §4.4, §4.5, §4.6; Ch5 §5.1 — all exist ✅
- §1.3 → Ch3 §3.1, §3.3, §3.4, §3.5; Ch4 §4.4, §4.7; Ch5 §5.5; Ch6 §6.1, §6.2 — all exist ✅
- §1.4 → Ch3 §3.4, §3.6; Ch4 §4.2, §4.3, §4.4, §4.5, §4.6, §4.7 — all exist ✅
- §1.5 → Ch3 §3.1 through §3.7 — all exist ✅
- §1.6 → Ch4 §4.2, §4.4, §4.5, §4.6, §4.7 — all exist ✅
- §1.7 → Ch2-6 with section-level enumeration — all exist ✅

### Chapter 2 forward references (~25 unique cross-chapter refs)

- §2.1 → Ch3 §3.4; Ch4 §4.1 — exist ✅
- §2.2 → Ch1 §1.4; Ch3 §3.4; Ch4 §4.2-§4.7 — all exist ✅
- §2.3 → Ch3 §3.4; Ch6 §6.1, §6.2 — all exist ✅
- §2.4 → Ch1 §1.4; Ch4 §4.5, §4.6, §4.7 — all exist ✅
- §2.5 → Ch3 §3.3; Ch4 §4.1; Ch6 §6.1 — all exist ✅
- §2.6 → Ch4 §4.7; Ch6 §6.2 — all exist ✅
- §2.7 → comprehensive Gap-to-Contribution map; Ch1 §1.4, Ch3 §3.1, §3.4, §3.6; Ch4 §4.2-§4.7; Ch6 §6.1, §6.2 — all exist ✅

### Phantom references

- "Chapter 7": **0 occurrences** ✅
- §X.8 / §X.9: **0 occurrences** ✅
- Sections beyond actual count (e.g., §5.7, §6.5): **0 occurrences** ✅

**Verdict for Task 7: ✅ PASS — no phantom forward references.**

---

## Cumulative wording-rule compliance scan

| Rule | Result |
|---|---|
| `twelve-month` form (forbidden) | 0 hits ✅ |
| `PD model quality` standalone (forbidden — should be "PD signal informativeness") | 0 violations (Ch4 lines 496-497 contain the phrase but only inside a contrastive disambiguation, explicitly explaining why it is NOT used — acceptable) ✅ |
| `prove` standalone | 0 hits ✅ |
| `universally` standalone | 0 hits ✅ |
| `always` standalone | 3 hits, all in contrastive contexts (Ch4 lines 303, 579; Ch5 line 75) describing what the framework would be if it always recommended approve — these are the negating context the user-approved boundary statements use ✅ |
| `universal real-market law` | 1 hit (Ch1 line 154) — this is the user-prescribed verbatim boundary statement explicitly negating universality ✅ |
| `Within the tested scenario space` framing present in required locations | 16 hits across all 7 files — all required locations covered ✅ |
| `controlled APR and LGD assumptions` (vs. `known APR/LGD`) | Used in Abstract Para 2; Ch1 §1.1; Ch2 §2.4. No `known APR` or `known LGD` violations ✅ |
| `12-month` consistency | Used throughout; 0 `twelve-month` ✅ |

---

## Optional polish items (non-blocking)

### Polish 1 — §2.5 Brier reporting note

**Status**: Already addressed in Phase 6 (the §2.5 sentence now reads
"Chapter 4 §4.1 reports both discrimination metrics (Gini, AUC, KS)
and calibration summaries (notably the predicted-to-observed ratio on
the eco-OOT subset)"). On verification, Brier values are actually
present in **Chapter 3** Tables 3.4a and 3.4b (and discussed in Ch3
§3.3 lines 326, 359, 361, 367, 378, 380, 383, 690), but Chapter 4
§4.1 does not narrate Brier in its prose. The current §2.5 wording is
accurate.

### Polish 2 — Chapter 6 §6.1 explicit hedge

The explicit phrase "within the tested scenario space" does not
appear inside §6.1; instead, every Limitation entry uses its own
"Scope of impact" boundary. This is structurally consistent but
could optionally be reinforced by adding a single opening sentence
to §6.1 that uses the phrase explicitly. Not blocking.

---

## Summary table — fixes recommended before supervisor handoff

| # | Severity | Item | Location | Recommended fix |
|---|---|---|---|---|
| 1 | 🔴 BLOCKING (low effort) | `fig1_profit_curves` orphan — saved as publication figure but never cited in chapter prose | Should be added to Ch4 §4.2 | Add one sentence near Ch4 §4.2 line 168 or line 184 explicitly citing "Figure 1" — e.g., "The cumulative profit curve for the base scenario is shown in Figure 1." |
| 2 | 🟡 HIGH PRIORITY citation gap | Operating-cost benchmark `[TODO: cite]` flagged in 2 chapters (Ch4 §4.6 + Ch6 §6.1 Limitation 7) | Identify a single canonical source (McKinsey banking benchmark, Federal Reserve cost-to-income data, or EBA retail-bank operating cost statistics) and cite once with cross-references | This is the only HIGH-PRIORITY citation flag identified by the audit. |
| 3 | 🟢 OPTIONAL | Ch6 §6.1 could open with an explicit "within the tested scenario space" sentence to mirror the Ch5 §5.5 framing | Ch6 §6.1 opening | One sentence — non-blocking |

All other audit checks pass. The thesis is internally consistent on
numbers (22/22), section references (no phantoms; 170 §X.Y refs
verified), Tables (17/17 with 0 orphans), Figures (8/9 referenced;
1 orphan to fix), 12-month consistency (100%), hedge enforcement
(all required locations covered), and forbidden-token compliance
(0 violations).

---

## Final verdict

**READY for supervisor handoff.** Fix #1 (Figure 1 citation, applied
to Ch4 §4.4) and Fix #3 (Ch6 §6.1 hedge opening sentence, applied)
have been completed. Fix #2 (operating-cost benchmark citation) is
deferred to the broader citation pass — it is the single
HIGH-PRIORITY citation gap identified by this audit but does not
block supervisor handoff because the empirical reasoning supporting
the "1-5% operating cost range" claim is internally consistent
across Ch4 §4.6 and Ch6 §6.1 Limitation 7; only the source
attribution remains.

The thesis is otherwise internally consistent, numerically traceable,
and rhetorically disciplined per the cumulative wording locks
established in Phases 5-6.

---

## Applied Fixes (post-audit)

### ✅ Fix 1 applied — Figure 1 explicit citation in Chapter 4 §4.4

**Decision rationale.** Verified via `thesis_results_summary.md`
line 211, `phase4_3_4_report.md` lines 72-84, and the generating
notebook `notebooks/07_visualization.ipynb` lines 119-198 that
`fig1_profit_curves` shows **cumulative profit per anchor across
the four anchor scenarios, with the profit-optimal `k*` (○) and
Youden's J (×) markers per anchor**. The most natural home is
therefore §4.4 (Bootstrap CI Results, which introduces the four
anchors and Table 4.6's per-anchor metrics), not §4.2 (which
covers single base-scenario results only).

**Location.** Ch4 §4.4 Results, lines 362-367 (immediately after
Table 4.6).

**Sentence added** (replaces the previous single "visualised in
Figure 5" closing of the Source line):

> Source: `artifacts/economic_framework/bootstrap_ci_summary.csv`.
> The underlying cumulative profit curves for the four anchors —
> with the profit-optimal `k*` (○) and Youden's J (×) markers
> identifying the two cut-off rules — are shown in Figure 1, and
> the per-anchor density of profit uplift with the 2.5%, 50%, and
> 97.5% percentile lines is visualised in Figure 5.

**Verification.** Grep confirms `Figure 1` now appears in
`04_results.md` line 365. The Tables/Figures inventory in Task 6
above is now updated: 9 of 9 figures referenced; 0 orphan figures.

### ✅ Fix 3 applied — Chapter 6 §6.1 explicit hedge opening

**Location.** Ch6 §6.1, lines 22-25 (between the `## 6.1
Limitations` heading and Limitation 1's heading).

**Sentence added** (verbatim from the user's suggested wording):

> The limitations below define the boundary conditions under which
> the empirical claims of Chapters 4 and 5 are supported; they
> delimit the tested scenario space rather than invalidate the
> findings.

**Verification.** Grep confirms `delimit the tested scenario space`
now appears in `06_limitations.md` line 24. The Task 4 hedge
enforcement scoreboard above is now updated: §6.1 has explicit
"tested scenario space" framing in the new opening sentence
(previously implicit through per-Limitation Scope-of-impact only).

### ⏸ Fix 2 deferred — Op_cost benchmark citation

Per user instruction, deferred to the broader citation pass.
Continues to be flagged as the single HIGH-PRIORITY citation gap
in Task 3's grouped citation table (Group AA). When applied, the
citation should be cross-referenced from Ch4 §4.6 (line 531) and
Ch6 §6.1 Limitation 7 (line 217).

---

## Updated post-fix scoreboard

| Task | Pre-fix | Post-fix |
|---|---|---|
| 1 — Section reference audit | ✅ PASS | ✅ PASS |
| 2 — Number audit | ✅ PASS | ✅ PASS |
| 3 — TODO citation consolidation | ✅ PASS (50 markers, 1 HIGH-PRIORITY) | ⏸ same — Fix 2 deferred to citation pass |
| 4 — "Within tested scenario space" enforcement | ✅ PASS (§6.1 implicit) | ✅ PASS (§6.1 now explicit) |
| 5 — 12-month consistency | ✅ PASS | ✅ PASS |
| 6 — Tables/Figures inventory | ⚠ 1 orphan (Figure 1) | ✅ PASS (9/9 figures referenced) |
| 7 — Forward reference closure | ✅ PASS | ✅ PASS |

**End of Phase 7 audit and applied-fix log. Two chapter files
modified during the post-audit fix application: `04_results.md`
and `06_limitations.md`. Citation pass not begun.**
