#!/usr/bin/env python
# coding: utf-8

# # Phase 3.1B — Full Production Economics Run
# 
# **Locked conditions** (per `phase3_formula_lock.md` + Phase 3.1A acceptance):
# - Exclude 12-month loans (structural artifact). Population = 24m + 36m only ≈ 235,968 rows.
# - Primary PD: LightGBM tuned + Platt-calibrated.
# - Robustness PDs: LR full-F6E + Platt, LR no-F6E + Platt, Scorecard no-F6E + Platt.
# - Use locked formulas (`src.economics`).
# - APR scenarios: 1 tiered (locked tier table) + 4 fixed (12%, 18%, 24%, 30%).
# - LGD grid: {0.45, 0.55, 0.65, 0.75, 0.85}.
# - Discount grid: {0.00, 0.05}; op_cost grid: {0.00, 0.01, 0.02}.
# - Sensitivity total: 5 × 5 × 2 × 3 = 150 cells (primary PD only).
# - Base scenario (tiered APR, LGD=0.65, disc=0, op=0): all 4 PD models.
# - ASB one-period profit is benchmark only.

# In[1]:


import sys, time, json, joblib, warnings, math
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
warnings.filterwarnings("ignore")

REPO_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.governance import filter_pd_eligible, get_meta_columns
from src.calibration import (
    make_calibration_split, fit_platt, fit_isotonic, apply_calibrator,
)
from src.economics import (
    amortization_schedule, monthly_hazard_from_pd12, marginal_pd_schedule,
    lifetime_expected_loss, expected_interest_margin, expected_net_profit,
    apr_tier_lookup, apr_tier_lookup_vec,
    asb_one_period_profit_reference, asb_one_period_profit_reference_vec,
    batch_lifetime_economics,
)
from src.evaluation import compute_gini

ABT_PATH     = REPO_ROOT / "artifacts/phase2_rerun_v2/modeling_abt.parquet"
CATALOG_PATH = REPO_ROOT / "artifacts/phase2_rerun_v2/modeling_feature_catalog.csv"
LGB_MODEL    = REPO_ROOT / "artifacts/pd_model/lightgbm_tuned_model.pkl"
WOE_ABT      = REPO_ROOT / "artifacts/scorecard/woe_transformed_abt.parquet"
DIAG_T1      = REPO_ROOT / "artifacts/phase2_rerun_v2/diagnostics/test1_f6e_ablation.json"
FINAL_FEATS  = REPO_ROOT / "artifacts/phase2_rerun_v2/final_feature_set.csv"

OUT_DIR = REPO_ROOT / "artifacts/economic_framework"
OUT_DIR.mkdir(parents=True, exist_ok=True)
T0 = time.time()


# ## 1. Load economics population (24m + 36m only)

# In[2]:


catalog = pd.read_csv(CATALOG_PATH)
pd_eligible = filter_pd_eligible(catalog)
print(f"PD-eligible features: {len(pd_eligible)}")

# Load only the columns we need for ALL PD models (union of all features)
LR_FULL_F6E_FEATS = pd.read_csv(FINAL_FEATS)["feature"].tolist()  # 22 features
LR_NO_F6E_FEATS = json.load(open(DIAG_T1))["final_features"]  # 7 features
print(f"LR full-F6E features: {len(LR_FULL_F6E_FEATS)}")
print(f"LR no-F6E features: {len(LR_NO_F6E_FEATS)}")

cols_needed = sorted(set(pd_eligible) | set(LR_FULL_F6E_FEATS) | set(LR_NO_F6E_FEATS) | set(get_meta_columns()) | {"n_installments", "loan_amount"})
print(f"Total columns to load: {len(cols_needed)}")

t = time.time()
df = pd.read_parquet(ABT_PATH, columns=cols_needed)
print(f"Loaded ABT: {df.shape} in {time.time()-t:.1f}s")

# Filter to 24m + 36m
df_eco = df[df["n_installments"].isin([24, 36])].copy().reset_index(drop=True)
print(f"\nEconomics population (24m + 36m): {df_eco.shape}")
print(f"  24m: {(df_eco['n_installments']==24).sum():,}")
print(f"  36m: {(df_eco['n_installments']==36).sum():,}")

# Confirm 12m excluded
assert (df_eco['n_installments'] == 12).sum() == 0, "12m loans found in eco pop!"
print("✓ 12-month loans EXCLUDED")

# Categorical conversion for LightGBM
CAT_FEATURES = ["app_nom_branch","app_nom_gender","app_nom_job_code",
                "app_nom_marital_status","app_nom_city","app_nom_home_status"]
cat_in_pool = [c for c in CAT_FEATURES if c in pd_eligible]
for c in cat_in_pool:
    df_eco[c] = df_eco[c].astype("category")

# Set up temporal split for refitting LR variants
TRAIN_FOR_MODEL = list(range(202509, 202611))
CALIB_PERIODS   = [202611, 202612]
df_eco["split_new"] = make_calibration_split(df_eco, TRAIN_FOR_MODEL, CALIB_PERIODS)
print("\nNew split counts (eco pop):")
print(df_eco["split_new"].value_counts().to_string())


# ## 2. Score with 4 PD models
# 
# Primary: LightGBM tuned + Platt. Three robustness variants refit on
# 202509-202610, Platt on 202611-202612.

# In[3]:


def score_lightgbm(df_in):
    """Score with the saved tuned LightGBM model + Platt."""
    pkg = joblib.load(LGB_MODEL)
    booster = pkg["booster"]
    feat_list = pkg["feature_list"]
    platt = pkg["platt"]
    # Score
    s_raw = booster.predict(df_in[feat_list], num_iteration=pkg["best_iteration"])
    s_platt = apply_calibrator(s_raw, platt, "platt")
    return s_raw, s_platt

print("Scoring with LightGBM tuned...")
t = time.time()
df_eco["pd_lgb_raw"], df_eco["pd_lgb_platt"] = score_lightgbm(df_eco)
print(f"  done in {time.time()-t:.1f}s")
print(f"  pd_lgb_platt mean: {df_eco['pd_lgb_platt'].mean():.4%}")


# In[4]:


def refit_lr_with_platt(df_in, features, label):
    """Refit LR on train_for_model + Platt on calib; score full df_in."""
    mask_tr  = df_in["split_new"] == "train_for_model"
    mask_cal = df_in["split_new"] == "calib"
    medians = df_in.loc[mask_tr, features].median(numeric_only=True)
    X_tr = df_in.loc[mask_tr, features].fillna(medians)
    y_tr = df_in.loc[mask_tr, "default_flag_12m"].astype(int)
    keep = ~X_tr.isna().any(axis=1)
    X_tr_const = sm.add_constant(X_tr.loc[keep], has_constant="add")
    model = sm.Logit(y_tr.loc[keep], X_tr_const).fit(disp=False, maxiter=200)
    # Score full population
    X_full = sm.add_constant(df_in[features].fillna(medians), has_constant="add")
    s_raw = model.predict(X_full).to_numpy()
    # Platt on calib
    s_cal = s_raw[mask_cal.to_numpy()]
    y_cal = df_in.loc[mask_cal, "default_flag_12m"].astype(int).to_numpy()
    platt = fit_platt(s_cal, y_cal)
    s_platt = apply_calibrator(s_raw, platt, "platt")
    print(f"  {label}: refit OK, OOT mean_pred={s_platt[df_in['split_new']=='oot'].mean():.4%}")
    return s_raw, s_platt

print("Refitting LR full-F6E + Platt...")
t = time.time()
df_eco["pd_lr_full_raw"], df_eco["pd_lr_full_platt"] = refit_lr_with_platt(
    df_eco, LR_FULL_F6E_FEATS, "LR_full_F6E")
print(f"  wall: {time.time()-t:.1f}s")

print("\nRefitting LR no-F6E + Platt...")
t = time.time()
df_eco["pd_lr_nof6e_raw"], df_eco["pd_lr_nof6e_platt"] = refit_lr_with_platt(
    df_eco, LR_NO_F6E_FEATS, "LR_no_F6E")
print(f"  wall: {time.time()-t:.1f}s")


# In[5]:


# Scorecard PD: load from woe_transformed_abt.parquet (Phase 2B output)
print("Joining scorecard PD from Phase 2B...")
sc_df = pd.read_parquet(WOE_ABT, columns=["aid", "pd_woe_raw", "pd_woe_platt"])
sc_df = sc_df.rename(columns={"pd_woe_raw": "pd_sc_raw", "pd_woe_platt": "pd_sc_platt"})
df_eco = df_eco.merge(sc_df, on="aid", how="left")
print(f"  scorecard PD null after merge: {int(df_eco['pd_sc_platt'].isna().sum()):,}")
print(f"  pd_sc_platt mean: {df_eco['pd_sc_platt'].mean():.4%}")


# In[6]:


# Multi-model PD comparison (sanity check)
PD_COLS = ["pd_lgb_platt", "pd_lr_full_platt", "pd_lr_nof6e_platt", "pd_sc_platt"]
oot = df_eco[df_eco["split_new"] == "oot"]
print(f"OOT rows: {len(oot):,}, OOT base rate: {(oot['default_flag_12m']==1).mean():.4%}")
print()
print(f"{'PD model':<22}  {'mean_pred':>10}  {'OOT_AUC':>8}  {'OOT_Gini':>8}")
for c in PD_COLS:
    if oot[c].notna().all():
        gini = compute_gini(oot["default_flag_12m"], oot[c])
        print(f"{c:<22}  {oot[c].mean():>10.4%}  {(gini+1)/2:>8.4f}  {gini:>8.4f}")


# ## 3. Base economics (primary LightGBM PD, tiered APR, LGD=0.65, disc=0, op=0)

# In[7]:


LGD_BASE = 0.65
DISC_BASE = 0.0
OP_BASE = 0.0
PRIMARY_PD = "pd_lgb_platt"

# Per-row APR via tiered lookup (locked Section 10)
df_eco["apr_tiered"] = apr_tier_lookup_vec(df_eco[PRIMARY_PD].fillna(0).to_numpy())

# Base economics (primary PD, tiered APR, LGD=0.65)
print(f"Computing base economics (primary={PRIMARY_PD}, tiered APR, LGD={LGD_BASE})...")
t = time.time()
base = batch_lifetime_economics(
    pd_12m=df_eco[PRIMARY_PD].fillna(0).to_numpy(),
    loan_amount=df_eco["loan_amount"].to_numpy(),
    n_installments=df_eco["n_installments"].to_numpy(),
    apr=df_eco["apr_tiered"].to_numpy(),
    lgd=LGD_BASE, op_cost_annual=OP_BASE, discount_annual=DISC_BASE,
)
df_eco["LT_EL_base"] = base["LT_EL"]
df_eco["LT_margin_base"] = base["LT_margin"]
df_eco["Expected_Profit_base"] = base["Expected_Profit"]
print(f"  wall: {time.time()-t:.1f}s")
print()
print("Base scenario distribution (full eco pop):")
for col in ["LT_EL_base", "LT_margin_base", "Expected_Profit_base"]:
    s = df_eco[col]
    print(f"  {col:<22}  mean={s.mean():>10.2f}  median={s.median():>10.2f}  "
          f"std={s.std():>10.2f}  p1={s.quantile(0.01):>10.2f}  "
          f"p99={s.quantile(0.99):>10.2f}")

# Profit > 0 share
print(f"\nProfit > 0 share: {(df_eco['Expected_Profit_base'] > 0).mean():.4%}")


# In[8]:


# Multi-PD comparison at base scenario (tiered APR, LGD=0.65, disc=0, op=0)
print("\n=== Base-scenario multi-PD comparison ===")
multi_pd_results = {}
for pd_col in PD_COLS:
    pd_arr = df_eco[pd_col].fillna(0).to_numpy()
    apr_arr = apr_tier_lookup_vec(pd_arr)
    out = batch_lifetime_economics(
        pd_12m=pd_arr,
        loan_amount=df_eco["loan_amount"].to_numpy(),
        n_installments=df_eco["n_installments"].to_numpy(),
        apr=apr_arr, lgd=LGD_BASE,
    )
    multi_pd_results[pd_col] = {
        "mean_pd": float(np.nanmean(pd_arr)),
        "mean_LT_EL": float(out["LT_EL"].mean()),
        "mean_LT_margin": float(out["LT_margin"].mean()),
        "mean_Expected_Profit": float(out["Expected_Profit"].mean()),
        "total_Expected_Profit": float(out["Expected_Profit"].sum()),
        "share_profit_gt_0": float((out["Expected_Profit"] > 0).mean()),
    }
print(pd.DataFrame(multi_pd_results).T.round(4).to_string())


# ## 4. Sensitivity grid (150 cells, primary PD only)

# In[9]:


APR_SCENARIOS = {
    "tiered": None,  # use apr_tier_lookup_vec
    "fixed_12": 0.12,
    "fixed_18": 0.18,
    "fixed_24": 0.24,
    "fixed_30": 0.30,
}
LGD_GRID = [0.45, 0.55, 0.65, 0.75, 0.85]
DISC_GRID = [0.00, 0.05]
OP_GRID = [0.00, 0.01, 0.02]

print(f"Grid size: {len(APR_SCENARIOS)} × {len(LGD_GRID)} × {len(DISC_GRID)} × {len(OP_GRID)} = "
      f"{len(APR_SCENARIOS) * len(LGD_GRID) * len(DISC_GRID) * len(OP_GRID)}")

pd_arr_primary = df_eco[PRIMARY_PD].fillna(0).to_numpy()
L_arr = df_eco["loan_amount"].to_numpy()
n_arr = df_eco["n_installments"].to_numpy()

grid_rows = []
t = time.time()
for apr_label, apr_val in APR_SCENARIOS.items():
    if apr_val is None:
        apr_arr = apr_tier_lookup_vec(pd_arr_primary)
    else:
        apr_arr = np.full_like(L_arr, apr_val, dtype=np.float64)
    for lgd in LGD_GRID:
        for disc in DISC_GRID:
            for op in OP_GRID:
                out = batch_lifetime_economics(
                    pd_12m=pd_arr_primary, loan_amount=L_arr,
                    n_installments=n_arr, apr=apr_arr, lgd=lgd,
                    op_cost_annual=op, discount_annual=disc,
                )
                grid_rows.append({
                    "apr_scenario": apr_label,
                    "lgd": lgd,
                    "discount_annual": disc,
                    "op_cost_annual": op,
                    "mean_LT_EL": float(out["LT_EL"].mean()),
                    "mean_LT_margin": float(out["LT_margin"].mean()),
                    "mean_Expected_Profit": float(out["Expected_Profit"].mean()),
                    "total_Expected_Profit": float(out["Expected_Profit"].sum()),
                    "share_profit_gt_0": float((out["Expected_Profit"] > 0).mean()),
                    "n_rows": len(out["LT_EL"]),
                })
sensitivity = pd.DataFrame(grid_rows)
print(f"Grid wall: {time.time()-t:.1f}s; rows: {len(sensitivity)}")
print()
print("Top 10 most-profitable cells (mean Expected_Profit):")
print(sensitivity.nlargest(10, "mean_Expected_Profit").round(2).to_string(index=False))
print()
print("Bottom 10 (mean Expected_Profit):")
print(sensitivity.nsmallest(10, "mean_Expected_Profit").round(2).to_string(index=False))


# ## 5. Cut-off analysis
# 
# For each PD model and APR scenario, find the profit-maximizing PD threshold
# and compare with Youden's J cutoff (TPR-FPR) on OOT.

# In[10]:


def youden_threshold(y_true, y_score):
    """Find threshold maximizing TPR - FPR."""
    from sklearn.metrics import roc_curve
    fpr, tpr, thr = roc_curve(y_true, y_score)
    j = tpr - fpr
    return float(thr[np.argmax(j)])

# Limit thresholds: percentiles 50, 60, 70, 75, 80, 85, 90, 95, 99
thresholds_pct = [50, 60, 70, 75, 80, 85, 90, 95, 99, 100]

cutoff_rows = []
optimal_cutoffs = {}
for pd_col in PD_COLS:
    pd_arr = df_eco[pd_col].fillna(1.0).to_numpy()  # NaN → reject (PD=1)
    L = df_eco["loan_amount"].to_numpy()
    n = df_eco["n_installments"].to_numpy()
    for apr_label, apr_val in APR_SCENARIOS.items():
        apr_arr = apr_tier_lookup_vec(pd_arr) if apr_val is None else np.full_like(L, apr_val, dtype=np.float64)
        out = batch_lifetime_economics(
            pd_12m=pd_arr, loan_amount=L, n_installments=n, apr=apr_arr, lgd=LGD_BASE,
        )
        profit = out["Expected_Profit"]
        # Sort by PD ascending (lowest PD first = best)
        order = np.argsort(pd_arr)
        pd_sorted = pd_arr[order]
        profit_sorted = profit[order]
        cum_profit = np.cumsum(profit_sorted)
        for tp in thresholds_pct:
            k = int(len(pd_arr) * tp / 100)
            if k <= 0: continue
            cutoff_pd = pd_sorted[k - 1]
            accepted = k
            total_p = cum_profit[k - 1]
            cutoff_rows.append({
                "pd_model": pd_col,
                "apr_scenario": apr_label,
                "approve_pct": tp,
                "n_accepted": int(accepted),
                "cutoff_pd": float(cutoff_pd),
                "total_Expected_Profit": float(total_p),
                "mean_Expected_Profit_accepted": float(total_p / max(accepted, 1)),
            })
        # Optimal threshold = max cumulative profit
        k_star = int(np.argmax(cum_profit)) + 1
        cutoff_pd_star = pd_sorted[k_star - 1]
        # Youden (only on OOT)
        oot_mask = (df_eco["split_new"] == "oot").to_numpy()
        if oot_mask.any():
            try:
                youden = youden_threshold(
                    df_eco.loc[oot_mask, "default_flag_12m"].to_numpy(),
                    pd_arr[oot_mask],
                )
            except Exception:
                youden = float("nan")
        else:
            youden = float("nan")
        optimal_cutoffs[f"{pd_col}__{apr_label}"] = {
            "k_star": int(k_star),
            "approve_pct_star": round(100 * k_star / len(pd_arr), 2),
            "cutoff_pd_star": float(cutoff_pd_star),
            "max_total_profit": float(cum_profit[k_star - 1]),
            "youden_threshold_oot": float(youden),
            "youden_approve_pct": round(100 * (pd_arr <= youden).mean(), 2) if not np.isnan(youden) else float("nan"),
        }

cutoff_df = pd.DataFrame(cutoff_rows)
print(f"Cut-off result rows: {len(cutoff_df)}")
print()
print("Sample cut-off table (LightGBM tuned, tiered APR):")
sample = cutoff_df[(cutoff_df["pd_model"]=="pd_lgb_platt") & (cutoff_df["apr_scenario"]=="tiered")]
print(sample.round(2).to_string(index=False))
print()
print("Optimal cut-offs across all (PD model × APR scenario):")
for k, v in list(optimal_cutoffs.items())[:6]:
    print(f"  {k:<35}  k*={v['approve_pct_star']:>6.2f}%  PD*={v['cutoff_pd_star']:.4f}  "
          f"profit={v['max_total_profit']:>14,.2f}  Youden_thr={v['youden_threshold_oot']:.4f}")


# ## 6. Tenor-stratified analysis (24m vs 36m vs combined)

# In[11]:


tenor_rows = []
for tenor_set, label in [([24], "24m"), ([36], "36m"), ([24, 36], "24m+36m")]:
    sub = df_eco[df_eco["n_installments"].isin(tenor_set)]
    if len(sub) == 0: continue
    pd_arr = sub[PRIMARY_PD].fillna(0).to_numpy()
    apr_arr = apr_tier_lookup_vec(pd_arr)
    out = batch_lifetime_economics(
        pd_12m=pd_arr, loan_amount=sub["loan_amount"].to_numpy(),
        n_installments=sub["n_installments"].to_numpy(), apr=apr_arr,
        lgd=LGD_BASE,
    )
    tenor_rows.append({
        "tenor": label,
        "n_rows": len(sub),
        "mean_pd": float(np.nanmean(pd_arr)),
        "mean_loan_amount": float(sub["loan_amount"].mean()),
        "mean_LT_EL": float(out["LT_EL"].mean()),
        "mean_LT_margin": float(out["LT_margin"].mean()),
        "mean_Expected_Profit": float(out["Expected_Profit"].mean()),
        "total_Expected_Profit": float(out["Expected_Profit"].sum()),
        "share_profit_gt_0": float((out["Expected_Profit"] > 0).mean()),
    })
tenor_df = pd.DataFrame(tenor_rows)
print("Tenor-stratified (base scenario, primary PD):")
print(tenor_df.round(2).to_string(index=False))


# ## 7. ASB benchmark vs tenor-aware Expected_Profit

# In[12]:


df_eco["ASB_profit"] = asb_one_period_profit_reference_vec(
    pd_12m=df_eco[PRIMARY_PD].fillna(0).to_numpy(),
    loan_amount=df_eco["loan_amount"].to_numpy(),
    apr=df_eco["apr_tiered"].to_numpy(),
    lgd=LGD_BASE,
)
df_eco["ASB_minus_LT"] = df_eco["ASB_profit"] - df_eco["Expected_Profit_base"]
df_eco["ASB_pct_bias"] = (df_eco["ASB_profit"] - df_eco["Expected_Profit_base"]) / df_eco["Expected_Profit_base"].abs()

asb_rows = []
for tenor_set, label in [([24], "24m"), ([36], "36m"), ([24, 36], "24m+36m")]:
    sub = df_eco[df_eco["n_installments"].isin(tenor_set)]
    asb_rows.append({
        "tenor": label,
        "n_rows": len(sub),
        "mean_LT_profit": float(sub["Expected_Profit_base"].mean()),
        "mean_ASB_profit": float(sub["ASB_profit"].mean()),
        "mean_ASB_minus_LT": float(sub["ASB_minus_LT"].mean()),
        "median_ASB_pct_bias": float(sub["ASB_pct_bias"].median()),
        "ASB_total_profit": float(sub["ASB_profit"].sum()),
        "LT_total_profit": float(sub["Expected_Profit_base"].sum()),
        "ASB_LT_total_ratio": float(sub["ASB_profit"].sum() / sub["Expected_Profit_base"].sum()),
    })
asb_df = pd.DataFrame(asb_rows)
print("ASB benchmark vs Lifetime Expected_Profit (base scenario):")
print(asb_df.round(4).to_string(index=False))


# ## 8. Save artifacts

# In[13]:


# economics_per_account.parquet (slim, primary economics)
slim_cols = ["aid", "n_installments", "loan_amount", "default_flag_12m", "split", "split_new",
             PRIMARY_PD, "pd_lr_full_platt", "pd_lr_nof6e_platt", "pd_sc_platt",
             "apr_tiered", "LT_EL_base", "LT_margin_base", "Expected_Profit_base", "ASB_profit"]
slim = df_eco[slim_cols].copy()
slim.to_parquet(OUT_DIR / "economics_per_account.parquet", index=False)
print(f"Saved: {OUT_DIR / 'economics_per_account.parquet'}  ({len(slim):,} rows × {len(slim.columns)} cols)")

# sensitivity_grid.parquet
sensitivity.to_parquet(OUT_DIR / "sensitivity_grid.parquet", index=False)
print(f"Saved: {OUT_DIR / 'sensitivity_grid.parquet'}  ({len(sensitivity)} cells)")

# cutoff_results.csv
cutoff_df.to_csv(OUT_DIR / "cutoff_results.csv", index=False)
print(f"Saved: {OUT_DIR / 'cutoff_results.csv'}  ({len(cutoff_df)} rows)")

# optimal_cutoffs.json
with open(OUT_DIR / "optimal_cutoffs.json", "w") as f:
    json.dump(optimal_cutoffs, f, indent=2)
print(f"Saved: {OUT_DIR / 'optimal_cutoffs.json'}")

# asb_comparison.csv
asb_df.to_csv(OUT_DIR / "asb_comparison.csv", index=False)
print(f"Saved: {OUT_DIR / 'asb_comparison.csv'}")

# tenor_economics.csv
tenor_df.to_csv(OUT_DIR / "tenor_economics.csv", index=False)
print(f"Saved: {OUT_DIR / 'tenor_economics.csv'}")

# Multi-model results
with open(OUT_DIR / "multi_pd_base_scenario.json", "w") as f:
    json.dump(multi_pd_results, f, indent=2)
print(f"Saved: {OUT_DIR / 'multi_pd_base_scenario.json'}")

print(f"\nTotal Phase 3.1B wall: {time.time()-T0:.1f}s")

