#!/usr/bin/env python
# coding: utf-8

# # Phase 2: PD Model Feature Selection
# 
# **Author:** Hoang
# **Date:** 2026-05-07
# **Inputs:** `artifacts/phase2_rerun_v2/modeling_abt.parquet`
# **Outputs:** `artifacts/phase2_rerun_v2/{stage1, stage2, stage3, final_model.pkl}`
# 
# Three-stage feature selection on the 800/day production wide ABT (post Phase 1.5
# feature factory, post `synth_credit_score_*` -> `synth_bureau_score_*` rename):
# 
# 1. **Stage 1** — univariate prescreening (sparsity, variance, signal, stability)
# 2. **Stage 2** — Lasso (L1-penalised logistic regression, 5-fold CV)
# 3. **Stage 3** — statsmodels logit refinement + VIF + p-value filter

# In[1]:


# Set up sys.path so 'from src import ...' works from a notebook in notebooks/
import sys
from pathlib import Path
REPO_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import os
import time

import joblib
import numpy as np
import pandas as pd

from src.governance import (
    filter_pd_eligible, validate_no_score_columns,
    validate_no_loan_term_in_pd, get_meta_columns, summarise_eligible_pool,
)
from src.modeling import (
    run_stage1_prescreening, run_lasso_selection,
    fit_logit_statsmodels, compute_vif,
)
from src.evaluation import (
    compute_gini, compute_ks, compute_brier, compute_calibration_metrics,
)

np.random.seed(42)

T0 = time.time()


# In[2]:


ABT_PATH     = REPO_ROOT / "artifacts/phase2_rerun_v2/modeling_abt.parquet"
CATALOG_PATH = REPO_ROOT / "artifacts/phase2_rerun_v2/modeling_feature_catalog.csv"
OUTPUT_DIR   = REPO_ROOT / "artifacts/phase2_rerun_v2"
CACHE_DIR    = REPO_ROOT / "artifacts/notebook_cache"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

print(f"ABT_PATH    : {ABT_PATH}")
print(f"CATALOG_PATH: {CATALOG_PATH}")
print(f"OUTPUT_DIR  : {OUTPUT_DIR}")
print(f"CACHE_DIR   : {CACHE_DIR}")


# ## Dry-Run Validation
# 
# Load catalog, filter PD-eligible features, then load only those columns + meta
# from the ABT. Verify shapes, DRs, score-column absence, and loan-term exclusion.

# In[3]:


catalog = pd.read_csv(CATALOG_PATH)
print(f"Catalog: {len(catalog):,} rows, {len(catalog.columns)} cols")

pd_eligible = filter_pd_eligible(catalog)
print(f"PD-eligible features: {len(pd_eligible)}")

# Per-family breakdown of the eligible pool
elig_summary = summarise_eligible_pool(catalog)
print("\nPD-eligible by family:")
print(elig_summary.to_string(index=False))

columns_to_load = pd_eligible + get_meta_columns()
df = pd.read_parquet(ABT_PATH, columns=columns_to_load)
print(f"\nLoaded shape : {df.shape}")
print(f"Memory       : {df.memory_usage(deep=True).sum() / 1e9:.2f} GB")
print(f"Train rows   : {(df['split']=='train').sum():,}")
print(f"OOT rows     : {(df['split']=='oot').sum():,}")
print(f"Train DR     : {df.loc[df['split']=='train', 'default_flag_12m'].mean():.4%}")
print(f"OOT DR       : {df.loc[df['split']=='oot', 'default_flag_12m'].mean():.4%}")

f6d_count = sum(f.startswith('random_') for f in pd_eligible)
print(f"F6D pure-random in PD-eligible pool: {f6d_count} "
      f"({100*f6d_count/len(pd_eligible):.1f}%)")

# Defensive checks
assert validate_no_score_columns(df), "score/scorem leak detected!"
assert validate_no_loan_term_in_pd(df, catalog), "loan-term leak in PD pool!"
print("\nDefensive checks: PASS (no score/scorem, no loan-term in PD)")


# ## Stage 1 — Univariate Prescreening
# 
# Filter rules (per `src.modeling.run_stage1_prescreening`):
# - **Sparsity:** `pct_nan <= 0.5`
# - **Variance:** train stddev > 0
# - **Signal:** train_gini >= 0.02
# - **Stability:** `|train_gini - oot_gini| / max(train_gini, eps) <= 0.20`
# 
# Cached at `artifacts/notebook_cache/stage1_results.pkl` for re-runs.

# In[4]:


cache_path = CACHE_DIR / "stage1_results.pkl"
if cache_path.exists():
    stage1 = joblib.load(cache_path)
    print(f"Loaded cached Stage 1 from {cache_path}")
else:
    t0 = time.time()
    stage1 = run_stage1_prescreening(
        df, target_col="default_flag_12m", features=pd_eligible
    )
    print(f"Stage 1 wall: {time.time() - t0:.1f}s")
    joblib.dump(stage1, cache_path)

print(f"Stage 1 survivors: {len(stage1)}")


# In[5]:


print("Top 20 Stage 1 survivors by train Gini:")
print(stage1.head(20).to_string(index=False))


# ## Stage 2 — Lasso Selection
# 
# `LogisticRegressionCV` with L1 penalty, SAGA solver, 5-fold CV, 10 candidate
# inverse regularisation strengths. Inputs are standardised; NaNs filled with
# train medians. Returns features with non-zero coefficient at the CV-best `C`.

# In[6]:


cache_path = CACHE_DIR / "stage2_results.pkl"
if cache_path.exists():
    stage2 = joblib.load(cache_path)
    print(f"Loaded cached Stage 2 from {cache_path}")
else:
    t0 = time.time()
    stage2 = run_lasso_selection(
        df, features=stage1["feature"].tolist(),
        target_col="default_flag_12m",
        cv=5, n_cs=10, random_state=42,
    )
    print(f"Stage 2 wall: {time.time() - t0:.1f}s")
    joblib.dump(stage2, cache_path)

print(f"Stage 2 Lasso survivors: {len(stage2)}")


# In[7]:


print("Stage 2 survivors:")
for f in stage2:
    g = stage1.loc[stage1['feature']==f, 'train_gini']
    g_val = float(g.iloc[0]) if len(g) else float('nan')
    print(f"  {f:<45}  train_gini={g_val:.4f}")


# ## Stage 3 — Refinement (statsmodels Logit + VIF + p-value)
# 
# Fit unpenalised logit on Stage 2 survivors, inspect VIF, drop high-VIF features
# (threshold 10), then drop p-values >= 0.05 and refit.

# In[8]:


final_features = list(stage2)

vif_df = compute_vif(df, final_features)
print(f"VIF (top 15 by VIF):")
print(vif_df.head(15).to_string(index=False))

# Drop features with VIF > 10 (multicollinear)
high_vif = vif_df.loc[vif_df['vif'] > 10, 'feature'].tolist()
if high_vif:
    print(f"\nDropping {len(high_vif)} high-VIF features:")
    for f in high_vif:
        print(f"  - {f}")
    final_features = [f for f in final_features if f not in high_vif]
else:
    print("\nNo high-VIF features to drop.")

print(f"\nFeatures after VIF filter: {len(final_features)}")

model = fit_logit_statsmodels(df, final_features, "default_flag_12m")
print("\n" + str(model.summary()))


# In[9]:


significant = model.pvalues[model.pvalues < 0.05].index.tolist()
final_features = [f for f in significant if f != "const"]
print(f"Final feature set after p<0.05 filter: {len(final_features)} features")
for f in final_features:
    coef = model.params[f]
    pval = model.pvalues[f]
    print(f"  {f:<45}  coef={coef:+.5f}  p={pval:.4g}")


# In[10]:


final_model = fit_logit_statsmodels(df, final_features, "default_flag_12m")
joblib.dump(final_model, OUTPUT_DIR / "final_model.pkl")
print(f"Saved: {OUTPUT_DIR / 'final_model.pkl'}")
print("\nFinal model summary:")
print(final_model.summary())


# ## Performance Evaluation
# 
# Compute Gini, KS, Brier on train and OOT splits.

# In[11]:


import statsmodels.api as sm
X_full = sm.add_constant(df[final_features].fillna(df[final_features].median(numeric_only=True)),
                         has_constant="add")
df["pd_score"] = final_model.predict(X_full)

train_mask = df["split"] == "train"
oot_mask   = df["split"] == "oot"

metrics = {
    "train": {
        "gini" : compute_gini(df.loc[train_mask, "default_flag_12m"], df.loc[train_mask, "pd_score"]),
        "ks"   : compute_ks  (df.loc[train_mask, "default_flag_12m"], df.loc[train_mask, "pd_score"]),
        "brier": compute_brier(df.loc[train_mask, "default_flag_12m"], df.loc[train_mask, "pd_score"]),
        "auc"  : (compute_gini(df.loc[train_mask, "default_flag_12m"], df.loc[train_mask, "pd_score"]) + 1) / 2,
    },
    "oot": {
        "gini" : compute_gini(df.loc[oot_mask, "default_flag_12m"], df.loc[oot_mask, "pd_score"]),
        "ks"   : compute_ks  (df.loc[oot_mask, "default_flag_12m"], df.loc[oot_mask, "pd_score"]),
        "brier": compute_brier(df.loc[oot_mask, "default_flag_12m"], df.loc[oot_mask, "pd_score"]),
        "auc"  : (compute_gini(df.loc[oot_mask, "default_flag_12m"], df.loc[oot_mask, "pd_score"]) + 1) / 2,
    },
}
print(json.dumps(metrics, indent=2))


# In[12]:


cal_train = compute_calibration_metrics(df.loc[train_mask, "default_flag_12m"], df.loc[train_mask, "pd_score"])
cal_oot   = compute_calibration_metrics(df.loc[oot_mask,   "default_flag_12m"], df.loc[oot_mask,   "pd_score"])
cal_df = pd.DataFrame({"train": cal_train, "oot": cal_oot})
print("Calibration metrics:")
print(cal_df.to_string())


# ## Safety Checks
# 
# Final-feature acceptance gate:
# - No score/scorem under any name
# - No `default_flag_12m` self-reference
# - No loan-term transforms
# - F6D pure-random count + tiered alert

# In[13]:


# Check 1: no simulator score (synth_bureau_* allowed)
for f in final_features:
    fl = f.lower()
    if "score" in fl and "bureau" not in fl and "synth_int" not in fl:
        raise AssertionError(f"Score variable found: {f}")
print("Check 1 (no simulator score): PASS")

# Check 2: no target self-reference
assert "default_flag_12m" not in final_features
print("Check 2 (no target self-reference): PASS")

# Check 3: no loan-term transforms (look at raw string + catalog source_columns)
loan_terms = ("loan_amount", "n_installments", "installment", "principal", "tenor")
cat_idx = catalog.set_index("feature_name")
for f in final_features:
    fl = f.lower()
    # forbid raw-name match unless feature is a synthetic bureau-score derivative
    if f.startswith("synth_"):
        continue
    for lt in loan_terms:
        if lt in fl:
            raise AssertionError(f"Loan-term transform found: {f}")
    # cross-check against catalog source_columns
    if f in cat_idx.index:
        sources = str(cat_idx.at[f, "source_columns"] or "").lower()
        for lt in loan_terms:
            if lt in sources and not f.startswith("synth_"):
                raise AssertionError(f"Loan-term sourcing found in {f}: source_columns={sources}")
print("Check 3 (no loan-term transforms): PASS")

# Check 4: F6D negative-control assessment (tiered)
f6d_in_final = [f for f in final_features if f.startswith("random_")]
print(f"Check 4: F6D pure-random features surviving = {len(f6d_in_final)}")
if len(f6d_in_final) == 0:
    print("  IDEAL: zero F6D survived -> Lasso correctly rejects pure noise")
elif len(f6d_in_final) == 1:
    print(f"  WARNING: 1 F6D survived -> investigate but not auto-failure  -> {f6d_in_final[0]}")
else:
    print(f"  SERIOUS: {len(f6d_in_final)} F6D survived  -> investigate pipeline  -> {f6d_in_final}")


# ## Save Artifacts

# In[14]:


stage1.to_csv(OUTPUT_DIR / "stage1_selected_features.csv", index=False)
pd.Series(stage2, name="feature").to_csv(OUTPUT_DIR / "stage2_selected_features.csv", index=False, header=True)
pd.Series(final_features, name="feature").to_csv(OUTPUT_DIR / "final_feature_set.csv", index=False, header=True)

df_scores = df[["aid", "split", "default_flag_12m", "pd_score"]].copy()
df_scores.to_parquet(OUTPUT_DIR / "pd_scores.parquet", index=False)

with open(OUTPUT_DIR / "model_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

# Persist final coefficient table
coef_table = pd.DataFrame({
    "feature": ["const"] + final_features,
    "coef": [final_model.params["const"]] + [final_model.params[f] for f in final_features],
    "std_err": [final_model.bse["const"]] + [final_model.bse[f] for f in final_features],
    "p_value": [final_model.pvalues["const"]] + [final_model.pvalues[f] for f in final_features],
})
coef_table.to_csv(OUTPUT_DIR / "final_coefficients.csv", index=False)

# Calibration outputs
cal_df.to_csv(OUTPUT_DIR / "calibration_metrics.csv")

print("Saved artifacts:")
for p in sorted(OUTPUT_DIR.glob("*")):
    sz = p.stat().st_size
    print(f"  {p.name:<40}  {sz:>10,} bytes")
print(f"\nWall (Phase 2 total): {time.time() - T0:.1f}s")


# ## Final Report
# 
# | Metric | Train | OOT |
# |--------|------:|----:|
# | Gini   | see metrics dict above | |
# | KS     | | |
# | AUC    | | |
# | Brier  | | |
# | ECE    | see calibration metrics | |
# 
# See `model_metrics.json`, `calibration_metrics.csv`, and
# `final_coefficients.csv` for the canonical numbers used by the thesis.
# 
# **F6D negative-control assessment:** see safety checks above.
# 
# **Comparison to old SET A':** SET A' (4 numeric + 5 categorical: `app_income`,
# `app_number_of_children`, `app_spendings`, `act_age`, plus the five
# categoricals) is the prior art baseline. The expected overlap with the new
# final feature set is computed in the next cell.

# In[15]:


SET_A_PRIME = {
    "app_income", "app_number_of_children", "app_spendings", "act_age",
    "app_nom_gender", "app_nom_marital_status", "app_nom_home_status",
    "app_nom_cars", "app_nom_job_code",
}
overlap = SET_A_PRIME & set(final_features)
new_only = set(final_features) - SET_A_PRIME
print(f"SET A' size: {len(SET_A_PRIME)}")
print(f"Final feature set size: {len(final_features)}")
print(f"Overlap with SET A': {len(overlap)}")
print(f"  overlap features: {sorted(overlap)}")
print(f"New-feature-factory features in final: {len(new_only)}")
print(f"  (showing first 30): {sorted(new_only)[:30]}")

