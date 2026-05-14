# Thesis Limitations + Future Work

**Purpose**: 10 explicit limitations to record honestly in the thesis
Limitations chapter, plus 7 future-work directions. Each limitation has a
specific phrasing and a pointer to the in-thesis location where it should
appear.

---

## 1. Synthetic simulator data, not real-world data

**Statement**: All results derive from a single synthetic simulator
(`rl-debt-collection`) configured with seed=42, p_positive=0.00, 800
clients/day, 60 periods. Real-world consumer-credit portfolios may show
different behaviour patterns, default trajectories, and feature
distributions. The simulator's transition mechanism (deterministic
quota-based with Bernoulli reaction draws) approximates but does not
replicate any specific institution's data.

**Where to place**: Limitations §1 (data provenance).

## 2. 12-month loans excluded from economic analysis

**Statement**: Loans with `n_installments = 12` were excluded from the
economic-analysis population because the simulator's writeoff trigger
(`due_installments ≥ 12`) is structurally unreachable within the
`default_flag_12m` target window (offsets 12-23 from origination). The
observed default rate of 0/298,346 = 0.000% on 12m loans is an artifact of
the simulator's target-definition timing, not a real-world conclusion that
12m loans are risk-free. Real institutions with 12m unsecured products
observe non-trivial default rates.

**Where to place**: Limitations §2 (population scope) AND Methodology §3 (population definition).

## 3. APR is exogenous, not market-observed

**Statement**: The simulator does not include any pricing field. APR is
applied as a thesis-side methodological assumption using a 5-tier risk-priced
schedule (12% Prime → 30% Deep-subprime) plus flat-APR sensitivity
alternatives (12%, 18%, 24%, 30%). Real markets price loans through
competitive dynamics, regulatory caps, and segment-specific underwriting;
the locked tier table is not market-validated.

**Where to place**: Limitations §3 (assumption set), Methodology §6 (APR scheme).

## 4. LGD is exogenous, not empirically recovered

**Statement**: Loss Given Default is set at 0.65 in the base case with a
sensitivity grid {0.45, 0.55, 0.65, 0.75, 0.85}. Empirical LGD could be
derived from the simulator's `transactions.csv` post-default repayment trace
(estimated 5-10 minute compute), but this was deferred. Real consumer-credit
LGD varies materially by collection process, secured/unsecured status, and
recovery legal regime.

**Where to place**: Limitations §4 (LGD), Future Work item 1.

## 5. Constant monthly hazard from PD_12m to lifetime horizon

**Statement**: The lifetime EL formula extrapolates the monthly hazard
`h = 1 - (1 - PD_12m)^(1/12)` across all months 1..n_installments. For 36m
loans, this implies cumulative PD = 1 - (1-h)^36 (vs the original 12m PD).
Empirical hazards typically decline with loan age (curing effect), so this
constant-hazard assumption likely OVERSTATES lifetime EL on long-tenor
loans. The Phase 4 PD-multiplier sensitivity partially reflects this
uncertainty but does not directly test a declining-hazard schedule.

**Where to place**: Limitations §5 (formula assumption), Future Work item 4.

## 6. LightGBM under-prediction on the economics-OOT subset

**Statement**: The LightGBM tuned + Platt model was calibrated on cohorts
202611-202612 whose base default rate (~0.85%) is approximately half the
economics-OOT subset's base rate (1.92%, after excluding 12m loans). On the
eco-OOT subset, the Platt-calibrated mean predicted PD is 0.94% vs observed
1.92% (mean_pred / observed = 0.49). The Phase 3 PD-multiplier scenarios
(×2, ×3, ×5) approximately bracket this calibration drift. The
profit-vs-Youden hypothesis survives every multiplier, so this caveat does
not invalidate the thesis result, but it is documented for transparency.

**Where to place**: Limitations §6 (calibration), Methodology §4 (calibration design).

## 7. Operational cost sensitivity strong; base case excludes recurring op_cost

**Statement**: The base case sets `op_cost_annual = 0`, which is unrealistic
for real lending operations. Phase 4.2 PART B shows op_cost is a powerful
lever: at op_cost = 0.04 combined with adverse stress, the framework
collapses to reject-most (k\* < 1%). Real banks operate with op_cost in the
1-5% range; thesis Discussion should highlight that real-world calibration
of op_cost is critical to the framework's interior-vs-reject classification.

**Where to place**: Limitations §7 (base assumption), Discussion §3 (op_cost sensitivity).

## 8. Scorem / demographic over-determinism in simulator

**Statement**: The simulator's internal `score` and `scorem` columns are
nearly tautological with respect to default outcome (Phase 2A diagnostic
exp2 measured |Gini(score @ obs+12m, default)| ≈ 0.93-0.97). These columns
were excluded from the wide ABT by design (`build_wide_abt.py` FINAL_COLS
whitelist) so the PD models do not benefit from the leak. The downstream PD
models still capture strong demographic signals (`app_nom_job_code`,
`app_nom_marital_status`, `act_age`) because the simulator's score formula
weights demographics heavily. Real consumer-credit data may show weaker
demographic determinism.

**Where to place**: Limitations §8 (simulator structure), Methodology §3 (PD model).

## 9. Single simulator configuration, not multiple simulator worlds

**Statement**: All results come from one production run: seed=42,
p_positive=0.00, 800 clients/day, 60 periods, end_date=20290501. Cross-seed
robustness, alternative p_positive levels, and alternative simulator
configurations were NOT tested. Bootstrap CIs in Phase 4.1 capture
within-OOT sampling uncertainty only.

**Where to place**: Limitations §9 (single-seed), Future Work item 6.

## 10. Bootstrap captures sampling uncertainty only

**Statement**: The 1,000-resample bootstrap on the 64,027-row OOT economics
subset quantifies the within-population sampling uncertainty of the cutoff
metrics. It does NOT capture (a) PD model uncertainty (alternative
hyperparameters, alternative solver runs), (b) calibration drift uncertainty
across cohorts, (c) APR/LGD/cost-of-funds assumption uncertainty, or (d)
formula choice uncertainty (e.g., declining vs constant hazard). Per the
locked phrasing rule: present bootstrap results as "across N resamples, the
result held in K of N", not as "P(...) = K/N".

**Where to place**: Limitations §10 (uncertainty scope), Methodology §9 (bootstrap design).

---

## Future Work (7 directions)

### F1. Empirical LGD recovery from `transactions.csv`

The simulator's transaction trace allows reconstruction of post-default
principal recovery for every defaulted account. A Phase 5+ task could:
1. For each `default_flag_12m == 1` aid, find the writeoff period
2. Sum subsequent paid_installments × installment
3. Compute LGD = max(0, (loan_amount − recovered) / loan_amount)
4. Compare empirical LGD distribution to the exogenous 0.65 base assumption.

### F2. Real public lending dataset replication

Apply the same Phase 2 → Phase 3 → Phase 4 pipeline to a real public dataset
(e.g., Lending Club, Freddie Mac, BondoraIPL, Kaggle "Home Credit Default
Risk"). Specifically test whether the profit-vs-Youden hypothesis holds in
real data with real APR, real LGD recovery, and real cohort-by-cohort
behaviour.

### F3. Alternative default definitions for 12m loans

The current `default_flag_12m` definition (writeoff in offsets 12-23) is
structurally unreachable for 12m loans (Limitation 2). Alternative
definitions could include:
- `default_flag_first_30dpd_within_term`: any 30+ DPD event before loan
  closure
- `default_flag_writeoff_at_or_after_terminal`: include writeoff at month 12
  itself
- Comparison of how each definition affects the 12m cohort default rate.

### F4. Declining hazard / vintage hazard curve

The constant-hazard assumption (Limitation 5) is a known simplification.
Future work could:
1. Estimate empirical monthly hazards from the simulator's transaction
   trace
2. Fit a parametric hazard curve (e.g., Weibull, log-logistic)
3. Re-run the lifetime EL formula with declining hazard
4. Quantify the gap vs constant-hazard baseline.

### F5. Market-calibrated APR tiers

The locked APR tier table (Limitation 3) is a methodological assumption.
Future work could:
1. Survey published APR ranges from real lenders (US, EU, emerging markets)
2. Calibrate per-tier APR to market median + spread
3. Test whether the profit-vs-Youden finding survives market-calibrated APR.

### F6. Multi-simulator-seed robustness

Run the entire pipeline (Phase 1.5 → Phase 4.4) on 5+ alternative simulator
seeds and 3+ alternative `p_positive` levels (e.g., {0.00, 0.02, 0.05}).
Quantify cross-seed variance in (a) profit_uplift point estimate, (b) cutoff
gap, (c) anchor scenario classification. Report whether single-seed
conclusions generalise.

### F7. External validation on real data

Beyond F2 (replication on a single real dataset), conduct external
validation: fit the LightGBM + scorecard models on the simulator data and
SCORE on a real public dataset (without refitting). Measure how transfer
performance affects (a) discrimination metrics, (b) calibration drift, and
(c) the profit-vs-Youden conclusion.
