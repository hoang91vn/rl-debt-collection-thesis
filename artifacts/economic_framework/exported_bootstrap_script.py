#!/usr/bin/env python
# coding: utf-8

# # Phase 4.1 — Bootstrap Confidence Intervals on Anchor Scenarios
# 
# **Goal**: 1000-resample bootstrap CIs around profit-optimal cut-offs and
# profit-vs-Youden gaps for 4 anchor scenarios. Stratified by tenor, on the
# OOT economics-eligible subset (24m + 36m only).
# 
# **Pre-checks** (Sections 1-2):
# - CHECK 1: refine anchors (add `moderate_interior`)
# - CHECK 2: op_cost ablation (Phase 3.2 grid omitted op_cost; run small ablation)
# 
# **Bootstrap** (Sections 3-6):
# - N = 1000 resamples
# - Stratified by `n_installments ∈ {24, 36}`
# - Primary PD: LightGBM tuned + Platt
# - Per-iteration metrics: total profit at k*, k*, PD threshold at k*,
#   total profit at Youden, Youden approve %, cutoff gap, profit uplift, uplift %

# In[1]:


import sys, time, json, joblib, warnings
from pathlib import Path

import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

REPO_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.economics import (
    batch_lifetime_economics, apr_tier_lookup_vec, apr_tier_lookup_capped_vec,
)
from src.evaluation import compute_gini

ECO_PATH = REPO_ROOT / "artifacts/economic_framework/economics_per_account.parquet"
STRESS_PATH = REPO_ROOT / "artifacts/economic_framework/economic_stress_grid.parquet"
OUT_DIR  = REPO_ROOT / "artifacts/economic_framework"

eco = pd.read_parquet(ECO_PATH)
stress = pd.read_parquet(STRESS_PATH)
print(f"eco: {eco.shape}; stress grid: {stress.shape}")
PRIMARY_PD = "pd_lgb_platt"
T0 = time.time()


# ## 1. CHECK 1 — Anchor refinement
# 
# `realistic_central` previously classified as approve_all (k*=99.25%) — relabel as
# `realistic_central_boundary`. Search the stress grid for a `moderate_interior`
# anchor with `94% <= k* <= 97%`, total profit > 0, gap > 0, and balanced
# parameter levels (PD multiplier in {2, 3}, LGD in {0.65, 0.75}).

# In[2]:


mask = (
    (stress["k_star_approve_pct"] >= 94)
    & (stress["k_star_approve_pct"] <= 97)
    & (stress["total_Expected_Profit"] > 0)
    & (stress["cutoff_gap_profit_minus_youden"] > 0)
    & (stress["pd_multiplier"].isin([2.0, 3.0]))
    & (stress["lgd"].isin([0.65, 0.75]))
)
candidates = stress[mask].copy()
print(f"Balanced moderate_interior candidates: {len(candidates)}")

# Pick the most representative — closest to k=95.5, prefer flat_18 + LGD=0.65 + COF=3%
def score(row):
    s = abs(row["k_star_approve_pct"] - 95.5) * 10
    s += 5 if row["apr_strategy"] != "flat_18" else 0  # prefer flat_18
    s += 5 if row["lgd"] != 0.65 else 0
    s += 3 if row["cost_of_funds_annual"] != 0.03 else 0
    s += 3 if row["acquisition_cost"] != 250 else 0
    s += 3 if row["pd_multiplier"] != 3.0 else 0
    return s
candidates["sel_score"] = candidates.apply(score, axis=1)
chosen = candidates.sort_values("sel_score").iloc[0]
print()
print("Chosen moderate_interior:")
for k in ["pd_multiplier","apr_strategy","cost_of_funds_annual","acquisition_cost","lgd",
          "k_star_approve_pct","mean_Expected_Profit","total_Expected_Profit",
          "share_profit_gt_0","cutoff_gap_profit_minus_youden","category"]:
    v = chosen[k]
    if isinstance(v, float):
        print(f"  {k:<35} {v:>15.4f}")
    else:
        print(f"  {k:<35} {v}")

MODERATE_INTERIOR = chosen.to_dict()


# In[3]:


# Final anchor set (4 scenarios)
ANCHORS = {
    "optimistic_base": {
        "pd_multiplier": 1.0, "cost_of_funds_annual": 0.00,
        "acquisition_cost": 0, "lgd": 0.55,
        "apr_strategy": "tiered_uncapped", "op_cost_annual": 0.0,
    },
    "realistic_central_boundary": {
        "pd_multiplier": 2.0, "cost_of_funds_annual": 0.03,
        "acquisition_cost": 250, "lgd": 0.65,
        "apr_strategy": "tiered_cap_24", "op_cost_annual": 0.0,
    },
    "moderate_interior": {
        "pd_multiplier": float(MODERATE_INTERIOR["pd_multiplier"]),
        "cost_of_funds_annual": float(MODERATE_INTERIOR["cost_of_funds_annual"]),
        "acquisition_cost": int(MODERATE_INTERIOR["acquisition_cost"]),
        "lgd": float(MODERATE_INTERIOR["lgd"]),
        "apr_strategy": MODERATE_INTERIOR["apr_strategy"],
        "op_cost_annual": 0.0,
    },
    "adverse_stress": {
        "pd_multiplier": 5.0, "cost_of_funds_annual": 0.06,
        "acquisition_cost": 500, "lgd": 0.85,
        "apr_strategy": "flat_18", "op_cost_annual": 0.0,
    },
}
print("Final anchor set:")
for name, params in ANCHORS.items():
    print(f"\n  {name}:")
    for k, v in params.items():
        print(f"    {k}: {v}")


# ## 2. CHECK 2 — op_cost ablation
# 
# The 576-cell Phase 3.2 grid held `op_cost_annual = 0` to keep grid size
# manageable (focus was on PD/COF/acq/LGD/APR). Phase 3.1B had already covered
# op_cost ∈ {0, 0.01, 0.02} in its 150-cell grid. Here we run a focused ablation
# on `realistic_central_boundary` and `adverse_stress` over `op_cost_annual ∈
# {0.00, 0.01, 0.02, 0.04}` to confirm the effect.

# In[4]:


def apr_array(pd_arr, strategy):
    if strategy == "tiered_uncapped":
        return apr_tier_lookup_vec(pd_arr)
    if strategy == "tiered_cap_24":
        return apr_tier_lookup_capped_vec(pd_arr, cap=0.24)
    if strategy == "tiered_cap_18":
        return apr_tier_lookup_capped_vec(pd_arr, cap=0.18)
    if strategy.startswith("flat_"):
        v = int(strategy.split("_")[1]) / 100.0
        return np.full_like(pd_arr, v, dtype=np.float64)
    raise ValueError(f"unknown strategy {strategy}")

def compute_anchor_economics(eco_subset, anchor, pd_col=PRIMARY_PD,
                              op_cost_override=None):
    pd_base = eco_subset[pd_col].fillna(0.0).to_numpy()
    pd_stressed = np.clip(pd_base * anchor["pd_multiplier"], 0.0, 0.999)
    apr_arr = apr_array(pd_stressed, anchor["apr_strategy"])
    op = op_cost_override if op_cost_override is not None else anchor.get("op_cost_annual", 0.0)
    out = batch_lifetime_economics(
        pd_12m=pd_stressed,
        loan_amount=eco_subset["loan_amount"].to_numpy(),
        n_installments=eco_subset["n_installments"].to_numpy(),
        apr=apr_arr, lgd=anchor["lgd"],
        op_cost_annual=op,
        cost_of_funds_annual=anchor["cost_of_funds_annual"],
        acquisition_cost=float(anchor["acquisition_cost"]),
    )
    return pd_stressed, out

# Run ablation on 2 anchors x 4 op_cost levels
ablation = []
for name in ["realistic_central_boundary", "adverse_stress"]:
    a = ANCHORS[name]
    for op in [0.00, 0.01, 0.02, 0.04]:
        pd_str, out = compute_anchor_economics(eco, a, op_cost_override=op)
        profit = out["Expected_Profit"]
        order = np.argsort(pd_str)
        cum = np.cumsum(profit[order])
        if cum.max() <= 0:
            k_star, max_p = 0, 0.0
        else:
            k_star = int(np.argmax(cum)) + 1
            max_p = float(cum[k_star - 1])
        ablation.append({
            "anchor": name,
            "op_cost_annual": op,
            "mean_profit": float(profit.mean()),
            "total_profit": float(profit.sum()),
            "share_profit_gt_0": float((profit > 0).mean()),
            "k_star_approve_pct": 100.0 * k_star / len(profit),
            "max_total_profit_at_k_star": max_p,
        })
ab_df = pd.DataFrame(ablation)
print("op_cost ablation (4 op_cost levels x 2 anchors):")
print(ab_df.round(2).to_string(index=False))
ab_df.to_csv(OUT_DIR / "op_cost_ablation.csv", index=False)
print(f"\nSaved: {OUT_DIR / 'op_cost_ablation.csv'}")


# ## 3. Bootstrap setup
# 
# - Population: OOT economics-eligible (24m + 36m only)
# - N_BOOTSTRAP = 1000
# - Stratified by tenor (24m, 36m)
# - random_state = 42
# - Primary PD: LightGBM Platt

# In[5]:


N_BOOTSTRAP = 1000
SEED = 42

# OOT subset (already 24m+36m only since eco was filtered in Phase 3.1B)
oot = eco[eco["split_new"] == "oot"].copy().reset_index(drop=True)
print(f"OOT rows: {len(oot):,}")
print(f"  tenor 24m: {(oot['n_installments']==24).sum():,}")
print(f"  tenor 36m: {(oot['n_installments']==36).sum():,}")
print(f"  default rate: {(oot['default_flag_12m']==1).mean():.4%}")

# Pre-compute per-row Expected_Profit per anchor (constant across bootstrap iters)
print("\nPre-computing per-row Expected_Profit + stressed PD per anchor...")
anchor_eco = {}
for name, a in ANCHORS.items():
    pd_str, out = compute_anchor_economics(oot, a)
    anchor_eco[name] = {
        "pd_stressed": pd_str,
        "profit": out["Expected_Profit"],
        "lt_el": out["LT_EL"],
        "lt_margin": out["LT_margin"],
    }
    pos_share = (out["Expected_Profit"] > 0).mean()
    print(f"  {name:<28}  share_profit>0={pos_share:.4%}  mean_profit={out['Expected_Profit'].mean():>10.2f}  "
          f"mean_pd_stressed={pd_str.mean():.4%}")

# Pre-compute Youden threshold ONCE per anchor (uses stressed PD vs default flag)
from sklearn.metrics import roc_curve
youden_per_anchor = {}
for name, a in ANCHORS.items():
    pd_str = anchor_eco[name]["pd_stressed"]
    fpr, tpr, thr = roc_curve(oot["default_flag_12m"], pd_str)
    j_idx = int(np.argmax(tpr - fpr))
    thr_y = float(thr[j_idx])
    youden_per_anchor[name] = thr_y
    print(f"  Youden thr {name}: {thr_y:.4f}  approve%={float((pd_str <= thr_y).mean()*100):.2f}%")


# ## 4. Run bootstrap (4 anchors × 1000 resamples)

# In[6]:


def stratified_bootstrap_indices(n_per_stratum, rng):
    """Return concatenated indices for a stratified resample with replacement."""
    parts = []
    for indices in n_per_stratum:
        parts.append(rng.choice(indices, size=len(indices), replace=True))
    return np.concatenate(parts)

# Build stratum index lists
idx_24 = oot.index[oot["n_installments"] == 24].to_numpy()
idx_36 = oot.index[oot["n_installments"] == 36].to_numpy()
print(f"Stratum sizes: 24m={len(idx_24):,}, 36m={len(idx_36):,}")
strata = [idx_24, idx_36]

rng = np.random.default_rng(SEED)
all_results = []

t0 = time.time()
for b in range(N_BOOTSTRAP):
    sample_idx = stratified_bootstrap_indices(strata, rng)
    for name in ANCHORS:
        pd_str = anchor_eco[name]["pd_stressed"][sample_idx]
        profit = anchor_eco[name]["profit"][sample_idx]
        # Profit-optimal cutoff: sort by stressed PD, find max cumulative profit
        order = np.argsort(pd_str)
        cum_profit = np.cumsum(profit[order])
        if cum_profit.max() <= 0:
            k_star = 0
            cutoff_pd_star = 0.0
            profit_at_kstar = 0.0
        else:
            k_star = int(np.argmax(cum_profit)) + 1
            cutoff_pd_star = float(pd_str[order[k_star - 1]])
            profit_at_kstar = float(cum_profit[k_star - 1])
        approve_pct_kstar = 100.0 * k_star / len(profit)
        # Youden cutoff (precomputed on full OOT, applied to bootstrap sample)
        thr_y = youden_per_anchor[name]
        accepted_y = pd_str <= thr_y
        profit_at_youden = float(profit[accepted_y].sum())
        approve_pct_y = float(accepted_y.mean() * 100)
        all_results.append({
            "bootstrap": b,
            "anchor": name,
            "profit_at_kstar": profit_at_kstar,
            "approve_pct_kstar": approve_pct_kstar,
            "cutoff_pd_star": cutoff_pd_star,
            "profit_at_youden": profit_at_youden,
            "approve_pct_youden": approve_pct_y,
            "cutoff_gap": approve_pct_kstar - approve_pct_y,
            "profit_uplift": profit_at_kstar - profit_at_youden,
            "profit_uplift_pct": (profit_at_kstar - profit_at_youden) / abs(profit_at_youden) if profit_at_youden != 0 else float("nan"),
        })
    if (b + 1) % 200 == 0:
        print(f"  {b+1}/{N_BOOTSTRAP} done ({time.time()-t0:.1f}s elapsed)")

bs = pd.DataFrame(all_results)
print(f"\nBootstrap wall: {time.time()-t0:.1f}s")
print(f"Result rows: {len(bs):,} ({N_BOOTSTRAP} × {len(ANCHORS)})")


# ## 5. Summary statistics + CIs per anchor

# In[7]:


metrics = ["profit_at_kstar","approve_pct_kstar","cutoff_pd_star",
           "profit_at_youden","approve_pct_youden","cutoff_gap",
           "profit_uplift","profit_uplift_pct"]
summary_rows = []
for anchor in ANCHORS:
    sub = bs[bs["anchor"] == anchor]
    for m in metrics:
        s = sub[m]
        summary_rows.append({
            "anchor": anchor,
            "metric": m,
            "mean": float(s.mean()),
            "median": float(s.median()),
            "std": float(s.std()),
            "ci_lo_2_5": float(s.quantile(0.025)),
            "ci_hi_97_5": float(s.quantile(0.975)),
        })
summary = pd.DataFrame(summary_rows)
print("=== Bootstrap summary (4 anchors × 8 metrics × 5 stats) ===")
for anchor in ANCHORS:
    print(f"\n{anchor}:")
    sub = summary[summary["anchor"] == anchor].drop(columns="anchor")
    print(sub.round(4).to_string(index=False))


# In[8]:


# Special probabilities
print("\n=== SPECIAL PROBABILITIES ===")
prob_rows = []
for anchor in ANCHORS:
    sub = bs[bs["anchor"] == anchor]
    p_approve_all = float((sub["approve_pct_kstar"] >= 99).mean())
    p_interior = float(((sub["approve_pct_kstar"] >= 50) & (sub["approve_pct_kstar"] < 99)).mean())
    p_reject_most = float((sub["approve_pct_kstar"] < 50).mean())
    p_profit_more_permissive = float((sub["cutoff_gap"] > 0).mean())
    p_uplift_pos = float((sub["profit_uplift"] > 0).mean())
    prob_rows.append({
        "anchor": anchor,
        "P(k* >= 99% / approve_all)": p_approve_all,
        "P(50% <= k* < 99% / interior)": p_interior,
        "P(k* < 50% / reject_most)": p_reject_most,
        "P(profit cutoff > Youden)": p_profit_more_permissive,
        "P(profit uplift > 0)": p_uplift_pos,
    })
prob_df = pd.DataFrame(prob_rows)
print(prob_df.round(4).to_string(index=False))


# ## 6. Save artifacts

# In[9]:


# Per-iteration parquet
bs.to_parquet(OUT_DIR / "bootstrap_anchor_results.parquet", index=False)
print(f"Saved: {OUT_DIR / 'bootstrap_anchor_results.parquet'}  ({len(bs):,} rows)")

# Summary CSV
summary.to_csv(OUT_DIR / "bootstrap_ci_summary.csv", index=False)
print(f"Saved: {OUT_DIR / 'bootstrap_ci_summary.csv'}")

# Cut-off distributions (k*, Youden % per anchor)
cutoff_dist_rows = []
for anchor in ANCHORS:
    sub = bs[bs["anchor"] == anchor]
    for col in ["approve_pct_kstar", "approve_pct_youden", "cutoff_gap"]:
        s = sub[col]
        cutoff_dist_rows.append({
            "anchor": anchor,
            "metric": col,
            "p2_5": float(s.quantile(0.025)),
            "p10": float(s.quantile(0.10)),
            "p25": float(s.quantile(0.25)),
            "p50": float(s.quantile(0.50)),
            "p75": float(s.quantile(0.75)),
            "p90": float(s.quantile(0.90)),
            "p97_5": float(s.quantile(0.975)),
            "mean": float(s.mean()),
            "std": float(s.std()),
        })
cd_df = pd.DataFrame(cutoff_dist_rows)
cd_df.to_csv(OUT_DIR / "bootstrap_cutoff_distributions.csv", index=False)
print(f"Saved: {OUT_DIR / 'bootstrap_cutoff_distributions.csv'}")

# Anchor definitions + special probs JSON
out_json = {
    "anchors": ANCHORS,
    "youden_thresholds": {k: float(v) for k, v in youden_per_anchor.items()},
    "special_probabilities": prob_df.to_dict(orient="records"),
    "n_bootstrap": N_BOOTSTRAP,
    "stratification": "by tenor (24m / 36m)",
    "primary_pd": PRIMARY_PD,
    "seed": SEED,
}
with open(OUT_DIR / "anchor_scenarios_v2.json", "w") as f:
    json.dump(out_json, f, indent=2, default=str)
print(f"Saved: {OUT_DIR / 'anchor_scenarios_v2.json'}")

print(f"\nTotal Phase 4.1 wall: {time.time()-T0:.1f}s")

