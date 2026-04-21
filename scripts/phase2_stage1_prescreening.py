#!/usr/bin/env python3
"""Phase 2 Stage 1 — Feature pre-screening on wide ABT train set.

Steps
-----
1. Missing rate filter  : drop col if null% > 50% on train
2. Near-zero variance   : drop col if top-value share >= 95% of non-null rows
3. Univariate Gini      : 70/30 split (seed=42), keep gini_train > 0.02
4. Stability filter     : drop col if delta_gini > 0.20

Categorical handling
--------------------
7 nominal columns are label-encoded for Gini scoring only.
Note: label encoding is used here for screening purposes only.
Stage 2 will apply one-hot encoding for the final model.

Outputs
-------
<output_dir>/stage1_prescreening_report.txt
<output_dir>/stage1_selected_features.txt  (one feature per line)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve, auc
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TARGET      = "default_flag_12m"
EXCLUDE     = {"aid", "cid", "fin_period", "obs_period",
               "observation_status", "split", TARGET}

CATEGORICALS = [
    "app_nom_branch", "app_nom_gender", "app_nom_job_code",
    "app_nom_marital_status", "app_nom_city",
    "app_nom_home_status", "app_nom_cars",
]

NULL_THRESHOLD     = 0.50   # Step 1: drop if null% > 50%
NZV_THRESHOLD      = 0.95   # Step 2: drop if top-value share >= 95%
GINI_MIN           = 0.02   # Step 3: keep if gini_train > 0.02
STABILITY_MAX      = 0.20   # Step 4: drop if delta_gini > 0.20

VAL_SPLIT          = 0.30
RANDOM_STATE       = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[stage1] {msg}", flush=True)


def sep(title: str = "", width: int = 70) -> None:
    if title:
        print(f"\n{'=' * width}")
        print(f"  {title}")
        print(f"{'=' * width}")
    else:
        print("-" * width)


def compute_gini(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Compute abs Gini = |2*AUC - 1|. Returns 0.0 on degenerate input."""
    try:
        if len(np.unique(y_true)) < 2:
            return 0.0
        fpr, tpr, _ = roc_curve(y_true, scores)
        return abs(2.0 * auc(fpr, tpr) - 1.0)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_train(input_dir: Path) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    csv_path = input_dir / "thesis_wide_abt.csv"
    log(f"Loading {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    log(f"  Full ABT: {df.shape[0]:,} rows x {df.shape[1]} cols")

    train = df[df["split"] == "train"].copy()
    log(f"  Train set: {len(train):,} rows")

    y = train[TARGET].astype(float)
    assert y.isna().sum() == 0, "default_flag_12m has nulls on train -- abort"
    log(f"  Target null count: 0  OK")
    log(f"  Default rate: {y.mean()*100:.4f}%")

    # Candidate features
    features = [c for c in train.columns if c not in EXCLUDE]
    log(f"  Candidate features: {len(features)}")

    # Label-encode categoricals (for screening only)
    encoded = []
    for col in CATEGORICALS:
        if col in train.columns:
            le = LabelEncoder()
            train[col] = le.fit_transform(train[col].astype(str))
            encoded.append(col)
    log(f"  Label-encoded {len(encoded)} categorical cols: {encoded}")

    X = train[features].copy()
    return X, y, features


# ---------------------------------------------------------------------------
# Step 1 — Missing rate filter
# ---------------------------------------------------------------------------

def step1_missing(X: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    sep("Step 1 -- Missing Rate Filter (threshold: null% > 50%)")
    n = len(X)
    dropped, kept = [], []
    report_rows = []

    for col in X.columns:
        null_pct = X[col].isna().mean() * 100
        if null_pct > NULL_THRESHOLD * 100:
            dropped.append(col)
            report_rows.append((col, null_pct, "DROPPED"))
            log(f"  DROP {col}: {null_pct:.1f}% null")
        else:
            kept.append(col)

    if not dropped:
        log(f"  No columns dropped (all {len(kept)} cols pass null filter)")

    X = X[kept]
    log(f"  Features after Step 1: {len(X.columns)}")
    return X, {"dropped": dropped, "report_rows": report_rows}


# ---------------------------------------------------------------------------
# Step 2 — Near-zero variance filter
# ---------------------------------------------------------------------------

def step2_nzv(X: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    sep("Step 2 -- Near-Zero Variance Filter (threshold: top-value >= 95%)")
    dropped, kept = [], []
    report_rows = []

    for col in X.columns:
        s = X[col].dropna()
        if len(s) == 0:
            dropped.append(col)
            report_rows.append((col, 100.0, "NA", "DROPPED"))
            continue
        top_share = s.value_counts().iloc[0] / len(s) * 100
        top_val   = s.value_counts().index[0]
        if top_share >= NZV_THRESHOLD * 100:
            dropped.append(col)
            report_rows.append((col, top_share, top_val, "DROPPED"))
            log(f"  DROP {col}: top value {top_val!r} = {top_share:.1f}%")
        else:
            kept.append(col)

    if not dropped:
        log(f"  No columns dropped (all {len(kept)} cols pass NZV filter)")

    X = X[kept]
    log(f"  Features after Step 2: {len(X.columns)}")
    return X, {"dropped": dropped, "report_rows": report_rows}


# ---------------------------------------------------------------------------
# Step 3 — Univariate Gini filter
# ---------------------------------------------------------------------------

def step3_gini(
    X: pd.DataFrame,
    y: pd.Series,
) -> tuple[pd.DataFrame, dict]:
    sep(f"Step 3 -- Univariate Gini Filter (keep gini_train > {GINI_MIN})")
    log(f"  70/30 train/val split (random_state={RANDOM_STATE})")

    idx = np.arange(len(X))
    idx_tr, idx_val = train_test_split(idx, test_size=VAL_SPLIT,
                                       random_state=RANDOM_STATE)
    y_arr  = y.values
    y_tr   = y_arr[idx_tr]
    y_val  = y_arr[idx_val]

    log(f"  Gini sub-train: {len(idx_tr):,} rows  |  val: {len(idx_val):,} rows")
    log(f"  Computing Gini for {len(X.columns)} features ...")

    t0 = time.time()
    gini_rows = []
    cols = list(X.columns)

    for i, col in enumerate(cols):
        scores = X[col].values
        # Fill NaN with median (for imputed cols with residual NaN)
        if np.isnan(scores).any():
            med = np.nanmedian(scores)
            scores = np.where(np.isnan(scores), med, scores)

        g_tr  = compute_gini(y_tr,  scores[idx_tr])
        g_val = compute_gini(y_val, scores[idx_val])
        delta = abs(g_tr - g_val) / g_tr if g_tr > 0 else float("nan")
        gini_rows.append({
            "feature":     col,
            "gini_train":  round(g_tr,  6),
            "gini_val":    round(g_val, 6),
            "delta_gini":  round(delta, 6) if not np.isnan(delta) else float("nan"),
        })

        if (i + 1) % 25 == 0 or (i + 1) == len(cols):
            elapsed = time.time() - t0
            log(f"    {i+1:3d}/{len(cols)}  ({elapsed:.1f}s)")

    gini_df = pd.DataFrame(gini_rows).sort_values("gini_train", ascending=False)

    # Filter
    kept_mask = gini_df["gini_train"] > GINI_MIN
    dropped_df = gini_df[~kept_mask]
    kept_df    = gini_df[kept_mask]
    dropped    = dropped_df["feature"].tolist()

    log(f"  Dropped {len(dropped)} features with gini_train <= {GINI_MIN}")
    if dropped:
        for _, row in dropped_df.iterrows():
            log(f"    DROP {row['feature']}: gini_train={row['gini_train']:.4f}")
    log(f"  Features after Step 3: {len(kept_df)}")

    log(f"\n  Top 20 features by gini_train:")
    log(f"  {'Feature':<45} {'gini_tr':>8} {'gini_val':>9} {'delta':>8}")
    sep()
    for _, row in kept_df.head(20).iterrows():
        delta_str = f"{row['delta_gini']:.4f}" if not np.isnan(row['delta_gini']) else "  nan "
        log(f"  {row['feature']:<45} {row['gini_train']:>8.4f} {row['gini_val']:>9.4f} {delta_str:>8}")

    X = X[kept_df["feature"].tolist()]
    return X, {"gini_df": gini_df, "kept_df": kept_df, "dropped": dropped}


# ---------------------------------------------------------------------------
# Step 4 — Stability filter
# ---------------------------------------------------------------------------

def step4_stability(
    X: pd.DataFrame,
    gini_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    sep(f"Step 4 -- Stability Filter (drop if delta_gini > {STABILITY_MAX})")

    kept_gini = gini_df[gini_df["feature"].isin(X.columns)].copy()
    dropped, kept = [], []

    for _, row in kept_gini.iterrows():
        delta = row["delta_gini"]
        if np.isnan(delta) or delta > STABILITY_MAX:
            dropped.append(row["feature"])
            log(f"  DROP {row['feature']}: delta_gini={delta:.4f} "
                f"(train={row['gini_train']:.4f}, val={row['gini_val']:.4f})")
        else:
            kept.append(row["feature"])

    if not dropped:
        log(f"  No columns dropped (all {len(kept)} cols pass stability filter)")

    X = X[kept]
    log(f"  Features after Step 4: {len(X.columns)}")
    return X, {"dropped": dropped}


# ---------------------------------------------------------------------------
# Write report
# ---------------------------------------------------------------------------

def write_report(
    output_dir: Path,
    features_initial: list[str],
    step1_info: dict,
    step2_info: dict,
    step3_info: dict,
    step4_info: dict,
    final_features: list[str],
) -> None:
    report_path  = output_dir / "stage1_prescreening_report.txt"
    feature_path = output_dir / "stage1_selected_features.txt"

    gini_df = step3_info["gini_df"]

    lines = [
        "Phase 2 Stage 1 -- Feature Pre-screening Report",
        "=" * 70,
        f"Input ABT    : thesis_wide_abt_12m_500c_clean/thesis_wide_abt.csv",
        f"Train rows   : 577,965",
        f"Target       : default_flag_12m  (default rate 3.27%)",
        f"Initial features: {len(features_initial)}",
        "",
        "Categorical encoding note:",
        "  7 nominal columns were label-encoded for Gini screening only.",
        "  Stage 2 will apply one-hot encoding for the final model.",
        "  Encoded: " + ", ".join(CATEGORICALS),
        "",
        "=" * 70,
        "Step 1 -- Missing Rate Filter  (threshold: null% > 50%)",
        "-" * 70,
        f"  Dropped : {len(step1_info['dropped'])}",
    ]
    if step1_info["dropped"]:
        for col, pct, status in step1_info["report_rows"]:
            lines.append(f"    {col:<45}  {pct:>6.1f}% null")
    else:
        lines.append("  (no columns dropped -- all pass null filter)")
    n_after1 = len(features_initial) - len(step1_info["dropped"])
    lines.append(f"  Features remaining: {n_after1}")

    lines += [
        "",
        "=" * 70,
        "Step 2 -- Near-Zero Variance Filter  (threshold: top-value >= 95%)",
        "-" * 70,
        f"  Dropped : {len(step2_info['dropped'])}",
    ]
    if step2_info["dropped"]:
        for col, share, top_val, status in step2_info["report_rows"]:
            lines.append(f"    {col:<45}  top value={top_val!r}  {share:.1f}%")
    else:
        lines.append("  (no columns dropped -- all pass NZV filter)")
    n_after2 = n_after1 - len(step2_info["dropped"])
    lines.append(f"  Features remaining: {n_after2}")

    lines += [
        "",
        "=" * 70,
        f"Step 3 -- Univariate Gini Filter  (keep gini_train > {GINI_MIN})",
        f"  70/30 train/val split (random_state={RANDOM_STATE})",
        "-" * 70,
        f"  Dropped : {len(step3_info['dropped'])}",
    ]
    if step3_info["dropped"]:
        dropped_gini = gini_df[gini_df["feature"].isin(step3_info["dropped"])]
        for _, row in dropped_gini.iterrows():
            lines.append(f"    {row['feature']:<45}  gini_train={row['gini_train']:.4f}")
    n_after3 = n_after2 - len(step3_info["dropped"])
    lines.append(f"  Features remaining: {n_after3}")

    lines += [
        "",
        "=" * 70,
        f"Step 4 -- Stability Filter  (drop if delta_gini > {STABILITY_MAX})",
        "-" * 70,
        f"  Dropped : {len(step4_info['dropped'])}",
    ]
    if step4_info["dropped"]:
        for col in step4_info["dropped"]:
            row = gini_df[gini_df["feature"] == col].iloc[0]
            lines.append(
                f"    {col:<45}  delta={row['delta_gini']:.4f}  "
                f"(tr={row['gini_train']:.4f}, val={row['gini_val']:.4f})"
            )
    else:
        lines.append("  (no columns dropped -- all pass stability filter)")
    lines.append(f"  Features remaining: {len(final_features)}")

    # Summary table — all screened features
    lines += [
        "",
        "=" * 70,
        "Full Gini table -- features passing Step 3 + 4, sorted by gini_train",
        "-" * 70,
        f"  {'Feature':<45} {'gini_tr':>8} {'gini_val':>9} {'delta':>8}  Status",
        "-" * 70,
    ]
    final_set = set(final_features)
    kept_gini = gini_df[gini_df["feature"].isin(
        step3_info["kept_df"]["feature"].tolist()
    )].copy()
    for _, row in kept_gini.iterrows():
        status = "selected" if row["feature"] in final_set else "stability_drop"
        delta_str = f"{row['delta_gini']:.4f}" if not np.isnan(row["delta_gini"]) else "   nan"
        lines.append(
            f"  {row['feature']:<45} {row['gini_train']:>8.4f} "
            f"{row['gini_val']:>9.4f} {delta_str:>8}  {status}"
        )

    lines += [
        "",
        "=" * 70,
        f"Final selected features: {len(final_features)}",
        "-" * 70,
    ]
    for i, f in enumerate(final_features, 1):
        row = gini_df[gini_df["feature"] == f]
        if len(row):
            r = row.iloc[0]
            delta_str = f"{r['delta_gini']:.4f}" if not np.isnan(r["delta_gini"]) else "   nan"
            lines.append(
                f"  {i:3d}. {f:<45} gini_train={r['gini_train']:.4f}  "
                f"gini_val={r['gini_val']:.4f}  delta={delta_str}"
            )
        else:
            lines.append(f"  {i:3d}. {f}")

    # Write report
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    log(f"Report written  : {report_path}")

    # Write feature list
    with open(feature_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(final_features) + "\n")
    log(f"Feature list    : {feature_path}  ({len(final_features)} features)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 2 Stage 1: feature pre-screening on wide ABT."
    )
    parser.add_argument(
        "--input-dir", type=Path,
        default=Path("artifacts/thesis_wide_abt_12m_500c_clean"),
        help="Directory containing thesis_wide_abt.csv",
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("artifacts/phase2"),
        help="Directory for report and feature list outputs",
    )
    args = parser.parse_args()

    input_dir  = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    t_start = time.time()

    # Load
    X, y, features_initial = load_train(input_dir)

    # Steps
    X, step1_info = step1_missing(X)
    X, step2_info = step2_nzv(X)
    X, step3_info = step3_gini(X, y)
    X, step4_info = step4_stability(X, step3_info["gini_df"])

    final_features = list(X.columns)

    # Print final summary
    sep("Final Summary")
    print(f"  Initial features    : {len(features_initial)}")
    print(f"  After Step 1 (null) : {len(features_initial) - len(step1_info['dropped'])}"
          f"  (dropped {len(step1_info['dropped'])})")
    print(f"  After Step 2 (NZV)  : {len(features_initial) - len(step1_info['dropped']) - len(step2_info['dropped'])}"
          f"  (dropped {len(step2_info['dropped'])})")
    print(f"  After Step 3 (Gini) : {len(step3_info['kept_df'])}"
          f"  (dropped {len(step3_info['dropped'])})")
    print(f"  After Step 4 (stab) : {len(final_features)}"
          f"  (dropped {len(step4_info['dropped'])})")
    print()
    gini_df = step3_info["gini_df"]
    final_gini = gini_df[gini_df["feature"].isin(final_features)].head(20)
    print(f"  Top 20 selected features:")
    print(f"  {'Feature':<45} {'gini_tr':>8} {'gini_val':>9} {'delta':>8}")
    sep()
    for _, row in final_gini.iterrows():
        delta_str = f"{row['delta_gini']:.4f}" if not np.isnan(row["delta_gini"]) else "   nan"
        print(f"  {row['feature']:<45} {row['gini_train']:>8.4f} "
              f"{row['gini_val']:>9.4f} {delta_str:>8}")

    # Write outputs
    write_report(output_dir, features_initial,
                 step1_info, step2_info, step3_info, step4_info,
                 final_features)

    elapsed = time.time() - t_start
    sep("Done")
    log(f"Total time      : {elapsed:.1f}s")
    log(f"Selected features: {len(final_features)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
