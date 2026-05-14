#!/usr/bin/env python
# coding: utf-8

# # Phase 4.2 — PD-quality stress + op_cost robustness
# 
# **Goal**: test whether the profit-vs-Youden finding survives under (A) lower
# PD discrimination and (B) higher operational-cost stress.
# 
# **Population**: OOT economics-eligible subset (24m + 36m only) — same as
# Phase 4.1 bootstrap. **64,027 rows** (CHECK 0 correction: Phase 4.1 report had
# a transcription error claiming 144,789).
# 
# **PD source**: LightGBM tuned + Platt-calibrated (raw OOT Gini ≈ 0.795).

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
from src.calibration import perturb_to_target_gini

ECO_PATH = REPO_ROOT / "artifacts/economic_framework/economics_per_account.parquet"
PD_QUAL_DIR = REPO_ROOT / "artifacts/pd_quality_stress"
OP_DIR      = REPO_ROOT / "artifacts/op_cost_robustness"
ECO_DIR     = REPO_ROOT / "artifacts/economic_framework"
PD_QUAL_DIR.mkdir(parents=True, exist_ok=True)
OP_DIR.mkdir(parents=True, exist_ok=True)

eco = pd.read_parquet(ECO_PATH)
oot = eco[eco["split_new"] == "oot"].copy().reset_index(drop=True)
print(f"OOT rows: {len(oot):,}  (24m: {(oot['n_installments']==24).sum():,}; 36m: {(oot['n_installments']==36).sum():,})")
print(f"OOT base default rate: {(oot['default_flag_12m']==1).mean():.5%}")

PRIMARY_PD = "pd_lgb_platt"
T0 = time.time()


# ## CHECK 0 — Phase 4.1 bootstrap population correction
# 
# The Phase 4.1 bootstrap report claimed 144,789 OOT rows. The actual code used
# `eco[eco["split_new"] == "oot"]` which yields **64,027 rows** (24m: 36,775;
# 36m: 27,252). The 144,789 figure was a transcription error (it appears to
# mix the OOT-of-full-wide-ABT count). The bootstrap results themselves are
# correct (they were computed on the actual 64,027 rows). The label is:
# **"OOT validation bootstrap (64,027 rows)"**, not portfolio-level.

# In[2]:


# CHECK 0 confirmation cell
n_oot = len(oot)
print(f"CHECK 0 — Phase 4.1 bootstrap used split_new == 'oot' = {n_oot:,} rows")
print(f"Tenor split: 24m={(oot['n_installments']==24).sum():,}, 36m={(oot['n_installments']==27252).sum() if False else (oot['n_installments']==36).sum():,}")
print("Label: OOT validation bootstrap (NOT full portfolio).")


# ## PART A — PD-quality stress
# 
# Use `perturb_to_target_gini` to create PD variants at target Gini levels
# [0.30, 0.45, 0.60, raw]. Each variant is re-calibrated to the OOT base rate
# so the comparison isolates *discrimination* shift, not *level* shift.

# In[3]:


y_oot = oot["default_flag_12m"].astype(int).to_numpy()
pd_raw = oot[PRIMARY_PD].fillna(0.0).to_numpy()
raw_gini = compute_gini(y_oot, pd_raw)
print(f"Raw OOT Gini (LightGBM Platt): {raw_gini:.4f}")

# Generate PD variants
TARGET_GINIS = [0.30, 0.45, 0.60]
pd_variants = {"raw": (pd_raw, {"sigma": 0.0, "achieved_gini": float(raw_gini), "note": "raw"})}
for tg in TARGET_GINIS:
    sp, meta = perturb_to_target_gini(pd_raw, y_oot, tg, seed=42, tolerance=0.005, sigma_max=5.0, n_iter=40, re_calibrate=True)
    pd_variants[f"gini_{int(tg*100)}"] = (sp, meta)
    print(f"  target Gini={tg:.2f}: sigma={meta['sigma']:.3f}, achieved={meta['achieved_gini']:.4f}, mean_pd={float(sp.mean()):.4%} (base_rate={float(y_oot.mean()):.4%})")
print()
# Save variants
variants_df = pd.DataFrame({"aid": oot["aid"].values, "n_installments": oot["n_installments"].values,
                             "loan_amount": oot["loan_amount"].values, "default_flag_12m": y_oot})
variants_df["pd_raw"] = pd_raw
for k, (sp, _) in pd_variants.items():
    if k != "raw":
        variants_df[f"pd_{k}"] = sp
print(f"PD variants shape: {variants_df.shape}")
variants_df.to_parquet(PD_QUAL_DIR / "pd_variants.parquet", index=False)
print(f"Saved: {PD_QUAL_DIR / 'pd_variants.parquet'}")


# In[4]:


# Anchor scenario definitions (4)
ANCHORS = {
    "optimistic_base": {
        "pd_multiplier": 1.0, "cost_of_funds_annual": 0.00,
        "acquisition_cost": 0, "lgd": 0.55,
        "apr_strategy": "tiered_uncapped",
    },
    "realistic_central_boundary": {
        "pd_multiplier": 2.0, "cost_of_funds_annual": 0.03,
        "acquisition_cost": 250, "lgd": 0.65,
        "apr_strategy": "tiered_cap_24",
    },
    "moderate_interior": {
        "pd_multiplier": 3.0, "cost_of_funds_annual": 0.03,
        "acquisition_cost": 250, "lgd": 0.65,
        "apr_strategy": "flat_18",
    },
    "adverse_stress": {
        "pd_multiplier": 5.0, "cost_of_funds_annual": 0.06,
        "acquisition_cost": 500, "lgd": 0.85,
        "apr_strategy": "flat_18",
    },
}

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
    raise ValueError(strategy)

def compute_anchor_economics_arr(pd_base, anchor, op_cost_override=None):
    pd_str = np.clip(pd_base * anchor["pd_multiplier"], 0.0, 0.999)
    apr_arr = apr_array(pd_str, anchor["apr_strategy"])
    op = op_cost_override if op_cost_override is not None else 0.0
    out = batch_lifetime_economics(
        pd_12m=pd_str, loan_amount=oot["loan_amount"].to_numpy(),
        n_installments=oot["n_installments"].to_numpy(),
        apr=apr_arr, lgd=anchor["lgd"],
        op_cost_annual=op,
        cost_of_funds_annual=anchor["cost_of_funds_annual"],
        acquisition_cost=float(anchor["acquisition_cost"]),
    )
    return pd_str, out

def compute_cutoff_metrics(pd_str, profit, y_true):
    """Return dict of cutoff metrics."""
    from sklearn.metrics import roc_curve
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
    # Youden on stressed PD
    fpr, tpr, thr = roc_curve(y_true, pd_str)
    j_idx = int(np.argmax(tpr - fpr))
    thr_y = float(thr[j_idx])
    accepted_y = pd_str <= thr_y
    profit_at_youden = float(profit[accepted_y].sum())
    approve_pct_y = float(accepted_y.mean() * 100)
    cutoff_gap = approve_pct_kstar - approve_pct_y
    profit_uplift = profit_at_kstar - profit_at_youden
    profit_uplift_pct = profit_uplift / abs(profit_at_youden) if profit_at_youden != 0 else float("nan")
    if approve_pct_kstar >= 99:
        cat = "approve_all"
    elif approve_pct_kstar >= 50:
        cat = "interior"
    else:
        cat = "reject_most"
    return {
        "k_star_approve_pct": approve_pct_kstar,
        "cutoff_pd_star": cutoff_pd_star,
        "profit_at_kstar": profit_at_kstar,
        "profit_at_youden": profit_at_youden,
        "approve_pct_youden": approve_pct_y,
        "cutoff_gap": cutoff_gap,
        "profit_uplift": profit_uplift,
        "profit_uplift_pct": profit_uplift_pct,
        "category": cat,
    }


# In[5]:


# PART A: PD variants × anchors (no op_cost stress; op=0)
part_a = []
for variant_name, (pd_base, meta) in pd_variants.items():
    for anchor_name, a in ANCHORS.items():
        pd_str, out = compute_anchor_economics_arr(pd_base, a)
        m = compute_cutoff_metrics(pd_str, out["Expected_Profit"], y_oot)
        m["pd_variant"] = variant_name
        m["pd_variant_gini"] = meta["achieved_gini"]
        m["anchor"] = anchor_name
        m["mean_profit"] = float(out["Expected_Profit"].mean())
        m["share_profit_gt_0"] = float((out["Expected_Profit"] > 0).mean())
        part_a.append(m)

pa_df = pd.DataFrame(part_a)
print("PART A — PD-quality stress (4 variants × 4 anchors = 16 cells):")
cols = ["pd_variant","pd_variant_gini","anchor","k_star_approve_pct",
        "approve_pct_youden","cutoff_gap","profit_at_kstar","profit_uplift",
        "profit_uplift_pct","share_profit_gt_0","category"]
print(pa_df[cols].round(4).to_string(index=False))
pa_df.to_csv(PD_QUAL_DIR / "cutoffs_by_gini.csv", index=False)
print(f"\nSaved: {PD_QUAL_DIR / 'cutoffs_by_gini.csv'}")


# ## PART B — op_cost robustness
# 
# Apply op_cost_annual ∈ {0.00, 0.01, 0.02, 0.04} to 3 anchors using the raw PD.

# In[6]:


OP_COST_GRID = [0.00, 0.01, 0.02, 0.04]
OP_ANCHORS = ["realistic_central_boundary", "moderate_interior", "adverse_stress"]

part_b = []
for anchor_name in OP_ANCHORS:
    a = ANCHORS[anchor_name]
    for op in OP_COST_GRID:
        pd_str, out = compute_anchor_economics_arr(pd_raw, a, op_cost_override=op)
        m = compute_cutoff_metrics(pd_str, out["Expected_Profit"], y_oot)
        m["anchor"] = anchor_name
        m["op_cost_annual"] = op
        m["mean_profit"] = float(out["Expected_Profit"].mean())
        m["total_profit"] = float(out["Expected_Profit"].sum())
        m["share_profit_gt_0"] = float((out["Expected_Profit"] > 0).mean())
        part_b.append(m)

pb_df = pd.DataFrame(part_b)
print("PART B — op_cost robustness (3 anchors × 4 op_cost = 12 cells):")
cols = ["anchor","op_cost_annual","k_star_approve_pct","approve_pct_youden",
        "cutoff_gap","mean_profit","total_profit","share_profit_gt_0",
        "profit_uplift","profit_uplift_pct","category"]
print(pb_df[cols].round(4).to_string(index=False))
pb_df.to_csv(OP_DIR / "cutoffs_by_op_cost.csv", index=False)
print(f"\nSaved: {OP_DIR / 'cutoffs_by_op_cost.csv'}")


# ## PART C — Combined Gini × op_cost × scenario mini-grid

# In[7]:


GINI_KEYS = ["raw", "gini_60", "gini_45", "gini_30"]
OP_GRID_C = [0.00, 0.02, 0.04]
SCN_C = ["realistic_central_boundary", "moderate_interior", "adverse_stress"]

part_c = []
for variant_name in GINI_KEYS:
    pd_base, meta = pd_variants[variant_name]
    for op in OP_GRID_C:
        for anchor_name in SCN_C:
            a = ANCHORS[anchor_name]
            pd_str, out = compute_anchor_economics_arr(pd_base, a, op_cost_override=op)
            m = compute_cutoff_metrics(pd_str, out["Expected_Profit"], y_oot)
            m["pd_variant"] = variant_name
            m["pd_variant_gini"] = meta["achieved_gini"]
            m["op_cost_annual"] = op
            m["anchor"] = anchor_name
            m["mean_profit"] = float(out["Expected_Profit"].mean())
            m["share_profit_gt_0"] = float((out["Expected_Profit"] > 0).mean())
            part_c.append(m)

pc_df = pd.DataFrame(part_c)
print(f"PART C — Combined mini-grid: {len(pc_df)} cells (4 Gini × 3 op_cost × 3 scenarios)")
cols = ["pd_variant","pd_variant_gini","op_cost_annual","anchor",
        "k_star_approve_pct","approve_pct_youden","cutoff_gap",
        "profit_uplift","profit_uplift_pct","share_profit_gt_0","category"]
print(pc_df[cols].round(4).to_string(index=False))
pc_df.to_csv(ECO_DIR / "phase4_2_combined_grid.csv", index=False)
print(f"\nSaved: {ECO_DIR / 'phase4_2_combined_grid.csv'}")


# ## Findings summary

# In[8]:


print("=" * 80)
print("FINDINGS")
print("=" * 80)

# A: profit > Youden under low Gini?
print("\nPART A — Does profit cutoff remain MORE permissive than Youden under low Gini?")
for variant_name in GINI_KEYS:
    sub = pa_df[pa_df["pd_variant"] == variant_name]
    n_more = int((sub["cutoff_gap"] > 0).sum())
    n_total = len(sub)
    achieved = float(sub["pd_variant_gini"].iloc[0])
    print(f"  Gini ≈ {achieved:.3f}: profit > Youden in {n_more}/{n_total} anchors")

# B: op_cost tipping points
print("\nPART B — op_cost tipping points:")
for anchor_name in OP_ANCHORS:
    sub = pb_df[pb_df["anchor"] == anchor_name].sort_values("op_cost_annual")
    print(f"\n  {anchor_name}:")
    for _, row in sub.iterrows():
        print(f"    op_cost={row['op_cost_annual']:.2f}: k*={row['k_star_approve_pct']:>6.2f}%  cat={row['category']}  gap={row['cutoff_gap']:+.2f} pp  profit_uplift={row['profit_uplift']:>14,.0f}")

# C: How many cells have profit-cutoff > Youden?
print(f"\nPART C — Combined grid:")
n_more = int((pc_df["cutoff_gap"] > 0).sum())
n_eq = int((pc_df["cutoff_gap"] == 0).sum())
n_less = int((pc_df["cutoff_gap"] < 0).sum())
print(f"  cells where profit cutoff > Youden: {n_more}/{len(pc_df)}")
print(f"  cells where profit cutoff = Youden: {n_eq}/{len(pc_df)}")
print(f"  cells where profit cutoff < Youden: {n_less}/{len(pc_df)}")
print(f"\n  Category counts:")
print(pc_df["category"].value_counts().to_string())

# Final wall time
print(f"\nTotal Phase 4.2 wall: {time.time()-T0:.1f}s")

