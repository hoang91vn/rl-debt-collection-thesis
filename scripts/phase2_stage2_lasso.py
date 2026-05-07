#!/usr/bin/env python3
"""Phase 2 Stage 2 -- Lasso Logistic Regression feature selection.

Reads 173 pre-screened features from Stage 1.
OHE-encodes 6 nominal columns (drop_first=True): 173 - 6 + 14 = 181 input cols.
Fits LogisticRegressionCV with L1 penalty (SAGA, 5-fold CV, Cs=10).
Selects features with abs(coef) > 0 after Lasso fit.

Nominal columns (already stored as integers, treated as categorical):
  app_nom_gender, app_nom_job_code, app_nom_marital_status,
  app_nom_home_status, app_nom_cars, app_nom_city

All 181 columns are StandardScaled before fitting.

Outputs
-------
<output_dir>/stage2_lasso_report.txt
<output_dir>/stage2_selected_features.txt  (sorted by abs(coef) desc)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegressionCV
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TARGET = "default_flag_12m"

# Nominal columns to OHE (stored as integers, not ordinal)
OHE_COLS = [
    "app_nom_gender",
    "app_nom_job_code",
    "app_nom_marital_status",
    "app_nom_home_status",
    "app_nom_cars",
    "app_nom_city",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[stage2] {msg}", flush=True)


def sep(title: str = "", width: int = 70) -> None:
    if title:
        print(f"\n{'=' * width}")
        print(f"  {title}")
        print(f"{'=' * width}")
    else:
        print("-" * width)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_data(
    input_dir: Path,
    feature_file: Path,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load train set, apply OHE + StandardScaler.
    Returns X (ndarray), y (ndarray), feature_names (list).
    """
    # Feature list
    features_173 = feature_file.read_text(encoding="utf-8").splitlines()
    features_173 = [f.strip() for f in features_173 if f.strip()]
    log(f"Stage 1 features loaded : {len(features_173)}")

    # Load CSV — only train split
    csv_path = input_dir / "thesis_wide_abt.csv"
    log(f"Loading {csv_path} ...")
    df = pd.read_csv(csv_path, low_memory=False)
    log(f"  Full ABT shape  : {df.shape[0]:,} rows x {df.shape[1]} cols")
    train = df[df["split"] == "train"].copy()
    log(f"  Train rows      : {len(train):,}")

    y = train[TARGET].astype(float).values
    assert np.isnan(y).sum() == 0, "default_flag_12m has nulls on train"
    log(f"  Target null count: 0  OK  |  default rate: {y.mean()*100:.4f}%")

    # Subset to 173 features
    missing = [f for f in features_173 if f not in train.columns]
    if missing:
        log(f"  WARNING: {len(missing)} features not found in ABT: {missing}")
    feats = [f for f in features_173 if f in train.columns]
    X_df = train[feats].copy()

    # --- OHE ---
    ohe_present = [c for c in OHE_COLS if c in X_df.columns]
    numeric_cols = [c for c in X_df.columns if c not in ohe_present]

    log(f"  Numeric cols    : {len(numeric_cols)}")
    log(f"  OHE cols        : {len(ohe_present)}  -> {ohe_present}")

    # Cast OHE columns to string so get_dummies creates category labels
    ohe_frames = []
    ohe_generated: list[str] = []
    for col in ohe_present:
        dummies = pd.get_dummies(
            X_df[col].astype(str), prefix=col, drop_first=True
        ).astype(float)
        ohe_frames.append(dummies)
        ohe_generated.extend(dummies.columns.tolist())
        log(f"    {col}: {X_df[col].nunique()} categories "
            f"-> {dummies.shape[1]} dummies  {list(dummies.columns)}")

    X_numeric = X_df[numeric_cols].astype(float)
    X_ohe     = pd.concat(ohe_frames, axis=1) if ohe_frames else pd.DataFrame(index=X_df.index)
    X_all     = pd.concat([X_numeric, X_ohe], axis=1)

    feature_names = list(X_all.columns)
    log(f"  Input cols after OHE : {len(feature_names)} "
        f"(= {len(numeric_cols)} numeric + {len(ohe_generated)} dummies)")

    # --- StandardScaler ---
    log("  Applying StandardScaler ...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_all.values)
    log(f"  Scaling complete. Shape: {X_scaled.shape[0]:,} x {X_scaled.shape[1]}")

    return X_scaled, y, feature_names


# ---------------------------------------------------------------------------
# Fit
# ---------------------------------------------------------------------------

def fit_lasso(
    X: np.ndarray,
    y: np.ndarray,
) -> LogisticRegressionCV:
    log("Fitting LogisticRegressionCV (L1, SAGA, Cs=10, cv=5) ...")
    log("  This may take 5-15 minutes on 577K rows ...")
    t0 = time.time()

    model = LogisticRegressionCV(
        Cs=10,
        cv=5,
        penalty="l1",
        solver="saga",
        max_iter=1000,
        scoring="roc_auc",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)

    elapsed = time.time() - t0
    log(f"  Fit complete in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    return model


# ---------------------------------------------------------------------------
# Extract results
# ---------------------------------------------------------------------------

def extract_results(
    model: LogisticRegressionCV,
    feature_names: list[str],
) -> tuple[list[tuple[str, float]], float, float, float]:
    """Return (selected_features_with_coef, best_C, cv_auc_mean, cv_auc_std)."""
    best_C = float(model.C_[0])

    # CV scores: model.scores_ is {class_label: ndarray(n_folds, n_Cs)}
    scores_arr = next(iter(model.scores_.values()))  # shape (n_folds, n_Cs)
    Cs_arr     = np.array(model.Cs_)
    best_C_idx = int(np.argmin(np.abs(Cs_arr - best_C)))
    fold_aucs  = scores_arr[:, best_C_idx]
    cv_mean    = float(fold_aucs.mean())
    cv_std     = float(fold_aucs.std())

    coefs = model.coef_[0]  # shape (n_features,)
    selected = [
        (name, float(coef))
        for name, coef in zip(feature_names, coefs)
        if abs(coef) > 0
    ]
    selected.sort(key=lambda x: abs(x[1]), reverse=True)

    return selected, best_C, cv_mean, cv_std


# ---------------------------------------------------------------------------
# Write report
# ---------------------------------------------------------------------------

def write_outputs(
    output_dir: Path,
    feature_names_in: list[str],
    selected: list[tuple[str, float]],
    best_C: float,
    cv_mean: float,
    cv_std: float,
    model: LogisticRegressionCV,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path  = output_dir / "stage2_lasso_report.txt"
    feature_path = output_dir / "stage2_selected_features.txt"

    n_in  = len(feature_names_in)
    n_out = len(selected)

    # --- Build report lines ---
    lines = [
        "Phase 2 Stage 2 -- Lasso Logistic Regression Report",
        "=" * 70,
        f"Input features (after OHE)  : {n_in}",
        f"  (= 167 numeric + 14 OHE dummies from 6 nominal cols)",
        f"Target                      : default_flag_12m  (3.27% default rate)",
        f"Train rows                  : 577,965",
        "",
        "Model configuration:",
        "  LogisticRegressionCV(Cs=10, cv=5, penalty='l1',",
        "                       solver='saga', max_iter=1000,",
        "                       scoring='roc_auc', random_state=42, n_jobs=-1)",
        "  Preprocessing: StandardScaler on all 181 input columns",
        "",
        "=" * 70,
        "Results",
        "-" * 70,
        f"  Best C (selected by CV)     : {best_C:.6g}",
        f"  CV AUC (mean +/- std)       : {cv_mean:.6f} +/- {cv_std:.6f}",
        "",
        f"  Features in (after OHE)     : {n_in}",
        f"  Features out (abs coef > 0) : {n_out}",
        f"  Features zeroed out         : {n_in - n_out}",
        "",
        "  CV AUC per fold at best C:",
    ]

    scores_arr = next(iter(model.scores_.values()))
    Cs_arr     = np.array(model.Cs_)
    best_C_idx = int(np.argmin(np.abs(Cs_arr - best_C)))
    fold_aucs  = scores_arr[:, best_C_idx]
    for i, auc_val in enumerate(fold_aucs, 1):
        lines.append(f"    Fold {i}: {auc_val:.6f}")

    # Top 20
    lines += [
        "",
        "=" * 70,
        "Top 20 features by abs(coef)",
        "-" * 70,
        f"  {'Rank':<5} {'Feature':<45} {'Coef':>10} {'AbsCoef':>10}",
        "-" * 70,
    ]
    for i, (name, coef) in enumerate(selected[:20], 1):
        lines.append(f"  {i:<5} {name:<45} {coef:>10.6f} {abs(coef):>10.6f}")

    # Full list
    lines += [
        "",
        "=" * 70,
        f"Full selected feature list ({n_out} features, sorted by abs(coef) desc)",
        "-" * 70,
        f"  {'Rank':<5} {'Feature':<45} {'Coef':>10} {'AbsCoef':>10}",
        "-" * 70,
    ]
    for i, (name, coef) in enumerate(selected, 1):
        lines.append(f"  {i:<5} {name:<45} {coef:>10.6f} {abs(coef):>10.6f}")

    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log(f"Report written  : {report_path}")

    # Feature list (names only, sorted by abs coef desc)
    with open(feature_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(name for name, _ in selected) + "\n")
    log(f"Feature list    : {feature_path}  ({n_out} features)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 2 Stage 2: Lasso LR feature selection."
    )
    parser.add_argument(
        "--input-dir", type=Path,
        default=Path("artifacts/thesis_wide_abt_12m_500c_clean"),
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("artifacts/phase2"),
    )
    args = parser.parse_args()

    input_dir  = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    feature_file = output_dir / "stage1_selected_features.txt"

    if not feature_file.exists():
        log(f"ERROR: {feature_file} not found -- run Stage 1 first")
        return 1

    t_total = time.time()

    sep("Load + Preprocess")
    X, y, feature_names = load_data(input_dir, feature_file)

    sep("Fit")
    model = fit_lasso(X, y)

    sep("Extract Results")
    selected, best_C, cv_mean, cv_std = extract_results(model, feature_names)

    sep("Summary")
    print(f"  Best C            : {best_C:.6g}")
    print(f"  CV AUC            : {cv_mean:.6f} +/- {cv_std:.6f}")
    print(f"  Features in       : {len(feature_names)}")
    print(f"  Features selected : {len(selected)}  (abs coef > 0)")
    print(f"  Features zeroed   : {len(feature_names) - len(selected)}")
    print()
    print(f"  Top 20 features by abs(coef):")
    print(f"  {'Feature':<45} {'Coef':>10} {'AbsCoef':>10}")
    sep()
    for name, coef in selected[:20]:
        print(f"  {name:<45} {coef:>10.6f} {abs(coef):>10.6f}")

    sep("Write Outputs")
    write_outputs(output_dir, feature_names, selected, best_C, cv_mean, cv_std, model)

    elapsed = time.time() - t_total
    sep("Done")
    log(f"Total runtime : {elapsed:.1f}s  ({elapsed/60:.1f} min)")
    log(f"Selected features: {len(selected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
