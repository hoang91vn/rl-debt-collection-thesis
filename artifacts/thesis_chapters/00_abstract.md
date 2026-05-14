# Abstract

Lending decisions are economic decisions, but credit-scoring
evaluation has historically relied on discrimination metrics —
AUC, Gini, KS, and cut-off rules such as Youden's J. The
published evidence base for profit-driven cut-off selection is
principled but thin on controlled empirical comparisons under
combined economic, PD-signal, and operating-cost stress. The
thesis asks: under what conditions do profit-driven cut-offs
outperform discrimination-driven cut-offs in expected dollar
profit?

The empirical experiment uses the synthetic rl-debt-collection
simulator under controlled APR and LGD assumptions and a known
data-generating process. The modelling population contains
534,314 rows. After excluding 12-month loans whose writeoff
trigger is unreachable within the 12-month forward target
window, the economic-analysis population contains 235,968 rows.
PD modelling is dual-track: a tuned, Platt-calibrated LightGBM
as primary, plus Logistic Regression and a Weight-of-Evidence
Scorecard. A tenor-aware Lifetime Net Margin formula stack
drives the economic framework. The empirical chain spans a
576-cell economic stress grid, a 64-cell PD-signal ×
operating-cost stress space, and a 1,000-resample bootstrap on
64,027 out-of-time rows at four anchor scenarios.

Within the tested scenario space, profit-driven cut-offs
strictly beat Youden's J in dollar terms. Point-estimate dollar
uplift was positive in 64 of 64 stress cells; uplift was
positive in 4,000 of 4,000 anchor × bootstrap combinations,
with per-anchor 95% bootstrap CIs not crossing zero. The
approval-rate cut-off gap widens as PD signal informativeness
falls — from approximately +15.5 pp at raw Gini ≈ 0.80 to
approximately +35.7 pp at Gini 0.30. A single reject-most
regime appears only at the joint extreme of all six stress
dimensions, indicating an adaptive optimisation rule. The
tenor-aware Lifetime framework yields portfolio profit
approximately 40% higher than the simpler Adjusted Single-period
Benchmark on 36-month loans.

The thesis advances four contributions: a tenor-aware Lifetime
Net Margin framework; a multi-dimensional stress-test design;
the PD-signal inversion finding (the cut-off gap widens as PD
discrimination falls), highlighted as the most novel; and a
bootstrap-versus-assumption uncertainty discipline. The
findings are conditional on the synthetic simulator, the locked
formulas, and the tested scenario space; replication on real
public data and on alternative simulator configurations is the
priority future-research direction.
