"""
Phase 3 -- Build PD Model
==========================
Fits a Logistic Regression PD model on SET A' demographics features
(population filtered to n_installments != 12).

Steps:
  1. Load ABT + apply population filter
  2. Build preprocessing pipeline (impute -> scale / OHE)
  3. Split TRAIN 80/20: model_train / calibration_holdout  (stratified)
  4. Fit LR on model_train
  5. Fit Platt calibrator on calibration_holdout
  6. Predict raw + calibrated probabilities on OOT
  7. Validation checks (Gini shift, calibration drift)
  8. Save all artifacts

Run:
    python scripts/phase3_build_pd_model.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

REPO_ROOT   = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "artifacts" / "phase3" / "run_config.json"
OUT_DIR     = REPO_ROOT / "artifacts" / "phase3"

TARGET    = "default_flag_12m"
SPLIT_COL = "split"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config():
    if not CONFIG_PATH.exists():
        sys.exit(f"ERROR: run_config.json not found at {CONFIG_PATH}. "
                 "Run phase3_config.py first.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def gini(y_true, y_score):
    return 2.0 * roc_auc_score(y_true, y_score) - 1.0


def build_preprocessor(numeric_cols, categorical_cols):
    """Build unfitted ColumnTransformer with imputation + scaling / OHE."""
    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
    ])
    try:
        ohe = OneHotEncoder(
            handle_unknown="ignore",
            min_frequency=0.005,
            sparse_output=False,
        )
    except TypeError:
        ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)

    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("ohe",     ohe),
    ])
    return ColumnTransformer([
        ("num", numeric_transformer, numeric_cols),
        ("cat", categorical_transformer, categorical_cols),
    ])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cfg = load_config()
    rng = cfg["reproducibility"]["global_seed"]
    np.random.seed(rng)

    # 1. Load + filter -------------------------------------------------
    abt_path = REPO_ROOT / cfg["data"]["abt_path"]
    print(f"[pd_model] loading ABT: {abt_path}")
    df = pd.read_csv(abt_path)
    print(f"[pd_model]   rows: {len(df):,}  cols: {df.shape[1]}")

    before = len(df)
    df = df[df["n_installments"] != 12].copy()
    print(f"[pd_model] population filter: {before:,} -> {len(df):,} "
          f"(dropped {before - len(df):,})")

    # 2. Split ---------------------------------------------------------
    df_train = df[df[SPLIT_COL] == "train"].copy()
    df_oot   = df[df[SPLIT_COL] == "oot"].copy()
    print(f"[pd_model] train: {len(df_train):,}  oot: {len(df_oot):,}")
    print(f"[pd_model] train default rate: "
          f"{df_train[TARGET].mean()*100:.4f}%")
    print(f"[pd_model] oot   default rate: "
          f"{df_oot[TARGET].mean()*100:.4f}%")

    num_cols  = cfg["features"]["numeric"]
    cat_cols  = cfg["features"]["categorical"]
    feat_cols = num_cols + cat_cols

    # Meta columns carried through for profit analysis (not model features)
    meta_cols = ["loan_amount", "n_installments", "installment"]
    for c in feat_cols + meta_cols:
        if c not in df.columns:
            sys.exit(f"ERROR: required column '{c}' not in ABT")

    X_train    = df_train[feat_cols]
    y_train    = df_train[TARGET].astype(int).values
    meta_oot   = df_oot[meta_cols].reset_index(drop=True)
    X_oot      = df_oot[feat_cols]
    y_oot      = df_oot[TARGET].astype(int).values

    # 3. 80/20 stratified split of TRAIN for Platt calibration ---------
    cal_rng = cfg["calibration"]["random_state"]
    holdout = cfg["calibration"]["holdout_fraction"]
    X_model_train, X_cal, y_model_train, y_cal = train_test_split(
        X_train, y_train,
        test_size=holdout,
        stratify=y_train,
        random_state=cal_rng,
    )
    print(f"[pd_model] model_train: {len(X_model_train):,}  "
          f"cal_holdout: {len(X_cal):,}")

    # 4. Fit preprocessor + LR on model_train --------------------------
    preprocessor = build_preprocessor(num_cols, cat_cols)
    lr_p = cfg["pd_model"]["params"]
    clf  = LogisticRegression(
        max_iter=lr_p["max_iter"],
        class_weight=lr_p["class_weight"],
        random_state=lr_p["random_state"],
        solver="lbfgs",
    )

    X_mtr_t = preprocessor.fit_transform(X_model_train)
    clf.fit(X_mtr_t, y_model_train)
    print(f"[pd_model] LR fitted  "
          f"(expanded features: {X_mtr_t.shape[1]})")

    # 5. Platt calibrator on calibration_holdout -----------------------
    X_cal_t    = preprocessor.transform(X_cal)
    p_cal_raw  = clf.predict_proba(X_cal_t)[:, 1]
    platt      = LogisticRegression(
        solver="lbfgs", max_iter=1000, random_state=rng
    )
    platt.fit(p_cal_raw.reshape(-1, 1), y_cal)
    platt_coef = float(platt.coef_[0][0])
    print(f"[pd_model] Platt calibrator fitted  "
          f"(coef={platt_coef:.4f}  "
          f"intercept={float(platt.intercept_[0]):.4f})")
    if platt_coef < 0:
        print("WARNING: Platt calibrator negative coefficient -- "
              "probability ordering may be inverted.")

    # 6. Predict on OOT -----------------------------------------------
    X_oot_t   = preprocessor.transform(X_oot)
    p_oot_raw = clf.predict_proba(X_oot_t)[:, 1]
    p_oot_cal = platt.predict_proba(p_oot_raw.reshape(-1, 1))[:, 1]

    # 7. Validation checks --------------------------------------------
    warnings_list = []

    g_raw = gini(y_oot, p_oot_raw)
    g_cal = gini(y_oot, p_oot_cal)
    brier = float(brier_score_loss(y_oot, p_oot_cal))
    mean_pred   = float(p_oot_cal.mean())
    mean_actual = float(y_oot.mean())

    print(f"[pd_model] Gini OOT raw       = {g_raw:.4f}")
    print(f"[pd_model] Gini OOT calibrated= {g_cal:.4f}")
    print(f"[pd_model] Mean pred (cal)     = {mean_pred:.6f}")
    print(f"[pd_model] Mean actual (oot)   = {mean_actual:.6f}")
    print(f"[pd_model] Brier score         = {brier:.6f}")

    if abs(g_cal - g_raw) > 0.02:
        msg = (f"WARNING: Gini shift after Platt ({g_raw:.4f} -> "
               f"{g_cal:.4f}) exceeds 0.02 -- ranking may have changed.")
        print(msg);  warnings_list.append(msg)

    cal_dev = abs(mean_pred - mean_actual)
    if cal_dev > 0.005:
        msg = (f"WARNING: calibrated mean {mean_pred:.4f} vs OOT actual "
               f"{mean_actual:.4f} ({cal_dev*100:.2f}pp > 0.5pp). "
               f"Expected when train/OOT base rates differ "
               f"({df_train[TARGET].mean()*100:.2f}% vs "
               f"{mean_actual*100:.2f}%).")
        print(msg);  warnings_list.append(msg)

    # 8. Save artifacts -----------------------------------------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf,          OUT_DIR / "pd_model.pkl")
    joblib.dump(preprocessor, OUT_DIR / "preprocessor.pkl")
    joblib.dump(platt,        OUT_DIR / "platt_calibrator.pkl")
    print("[pd_model] model artifacts saved")

    n_oot = len(y_oot)
    df_raw = pd.DataFrame({
        "row_id":         np.arange(n_oot, dtype=np.int32),
        "y_true":         y_oot.astype(np.int8),
        "prob_raw":       p_oot_raw.astype(np.float32),
        "loan_amount":    meta_oot["loan_amount"].values.astype(np.float32),
        "n_installments": meta_oot["n_installments"].values.astype(np.int16),
        "installment":    meta_oot["installment"].values.astype(np.float32),
    })
    df_cal = df_raw.copy()
    df_cal["prob_calibrated"] = p_oot_cal.astype(np.float32)

    df_raw.to_parquet(OUT_DIR / "predictions_oot_raw.parquet",        index=False)
    df_cal.to_parquet(OUT_DIR / "predictions_oot_calibrated.parquet", index=False)
    print(f"[pd_model] predictions saved ({n_oot:,} OOT rows)")

    validation = {
        "n_oot_rows":              int(n_oot),
        "train_default_rate":      round(float(df_train[TARGET].mean()), 6),
        "oot_default_rate":        round(mean_actual, 6),
        "gini_oot_raw":            round(g_raw, 6),
        "gini_oot_calibrated":     round(g_cal, 6),
        "gini_shift":              round(g_cal - g_raw, 6),
        "mean_predicted_cal":      round(mean_pred, 6),
        "mean_actual_oot":         round(mean_actual, 6),
        "calibration_deviation_pp": round(cal_dev * 100, 4),
        "brier_score":             round(brier, 6),
        "platt_coef":              round(platt_coef, 6),
        "platt_intercept":         round(float(platt.intercept_[0]), 6),
        "warnings":                warnings_list,
    }
    (OUT_DIR / "pd_model_validation.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    print("[pd_model] validation JSON saved")
    print("[pd_model] DONE")


if __name__ == "__main__":
    main()
