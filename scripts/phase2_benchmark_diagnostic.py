"""
Phase 2 -- Benchmark Diagnostic
================================

Purpose
-------
Quantify how much of the predictive signal in the 117-feature Stage-1
baseline comes from delinquency-trajectory leakage vs. genuine
origination-time credit-risk signal.

Three Logistic Regression baselines are fit on increasingly richer
feature sets and the train/OOT Gini gap is used as the litmus test:

  SET A -- origination-only      (no behavioral)
  SET B -- origination + early   (first 3 observable behavioral months)
  SET C -- full Stage-1 set      (proxy upper bound)

This is a DIAGNOSTIC -- no hyperparameter tuning, no CV.  All steps are
deterministic (random_state=42).

Run
---
  python scripts/phase2_benchmark_diagnostic.py
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

REPO_ROOT     = Path(__file__).resolve().parents[1]
ABT_DIR       = REPO_ROOT / "artifacts" / "thesis_wide_abt_12m_500c_clean"
ABT_PARQ      = ABT_DIR  / "thesis_wide_abt.parquet"
ABT_CSV       = ABT_DIR  / "thesis_wide_abt.csv"
STAGE1_FEATS  = REPO_ROOT / "artifacts" / "phase2" / "stage1_selected_features.txt"
OUT_DIR       = REPO_ROOT / "artifacts" / "phase2"
OUT_PATH      = OUT_DIR / "benchmark_diagnostic_report.txt"

TARGET        = "default_flag_12m"
SPLIT_COL     = "split"
RNG           = 42


# ---------------------------------------------------------------------------
# HARD-CODED feature sets
# ---------------------------------------------------------------------------
# SET A -- origination-only
#   Strictly information observable at t=0 (loan booking time):
#     product terms : loan_amount, n_installments, installment
#     applicant     : income, dependents, spendings, age
#     applicant nom : gender, marital, home_status, cars, job_code
#   Excluded on purpose:
#     app_nom_branch, app_nom_city -- primarily geographic, not demographic
#     app_loan_amount, app_n_installments -- exact duplicates of
#       loan_amount, n_installments after the build step

SET_A_NUMERIC = [
    "loan_amount",
    "n_installments",
    "installment",
    "app_income",
    "app_number_of_children",
    "app_spendings",
    "act_age",
]
SET_A_CATEGORICAL = [
    "app_nom_gender",
    "app_nom_marital_status",
    "app_nom_home_status",
    "app_nom_cars",
    "app_nom_job_code",
]

# SET B -- SET A + early-behavioral extras
#
#   Spec requested m1, m2, m3 of {act_due, coll_status, act_dueutl}.
#   Those features are constant-zero at m1 (no installment is yet due
#   at the origination month) and were dropped by Step 8A constant-col
#   filter during ABT build.  We substitute the first three months
#   that DO carry signal: m2, m3, m4.  This preserves the spec's
#   intent (first 3 months of observable behavioral signal).

SET_B_EXTRA = [
    "act_due_m2",     "act_due_m3",     "act_due_m4",
    "coll_status_m2", "coll_status_m3", "coll_status_m4",
    "act_dueutl_m2",  "act_dueutl_m3",  "act_dueutl_m4",
]

# SET C -- full Stage-1 selected feature set, loaded from disk at runtime
#   (artifacts/phase2/stage1_selected_features.txt -- 117 features after
#    Stage-1 collinearity dedup)


# Override: nominal columns are stored as int64 in the cleaned CSV
# (build_wide_abt persisted them as integer codes).  Without this list,
# dtype-based detection would treat them as numeric and StandardScale
# them instead of one-hot encoding -- wrong for unordered nominals
# (notably app_nom_job_code, app_nom_branch, app_nom_city).

KNOWN_CATEGORICAL_COLS = {
    "app_nom_branch",
    "app_nom_gender",
    "app_nom_job_code",
    "app_nom_marital_status",
    "app_nom_city",
    "app_nom_home_status",
    "app_nom_cars",
}


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def load_abt() -> pd.DataFrame:
    if ABT_PARQ.exists():
        print(f"[diag] loading parquet: {ABT_PARQ}")
        df = pd.read_parquet(ABT_PARQ)
    elif ABT_CSV.exists():
        print(f"[diag] loading csv: {ABT_CSV}")
        df = pd.read_csv(ABT_CSV)
    else:
        sys.exit(f"ERROR: ABT not found at {ABT_PARQ} or {ABT_CSV}")
    print(f"[diag]   rows: {len(df):,}  cols: {df.shape[1]}")
    return df


def load_stage1_features() -> list:
    if not STAGE1_FEATS.exists():
        sys.exit(f"ERROR: Stage-1 selected features not found at {STAGE1_FEATS}")
    feats = [ln.strip() for ln in STAGE1_FEATS.read_text().splitlines() if ln.strip()]
    print(f"[diag] Stage-1 features loaded: {len(feats)}")
    return feats


def assert_features_exist(feats, available, set_name):
    missing = [c for c in feats if c not in available]
    if missing:
        print(f"\nERROR: {set_name} requested features missing from ABT:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Modeling
# ---------------------------------------------------------------------------

def split_categorical_numeric(feats, df):
    """Return (numeric_cols, categorical_cols) preserving feats order.

    A column is treated as categorical if EITHER:
      - it is in KNOWN_CATEGORICAL_COLS (override -- nominals are stored
        as int64 in the cleaned CSV), or
      - its dtype is object / pandas categorical.
    """
    num_cols, cat_cols = [], []
    for c in feats:
        dt = df[c].dtype
        if c in KNOWN_CATEGORICAL_COLS \
                or dt == object or str(dt).startswith("category"):
            cat_cols.append(c)
        else:
            num_cols.append(c)
    return num_cols, cat_cols


def make_one_hot_encoder():
    """Build a OneHotEncoder that works on both new and old sklearn."""
    try:
        return OneHotEncoder(
            handle_unknown="ignore",
            min_frequency=0.005,
            sparse_output=False,
        )
    except TypeError:
        # older sklearn (<1.2): no min_frequency / sparse_output kw
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def fit_and_score(df_train, df_oot, feats, set_name):
    num_cols, cat_cols = split_categorical_numeric(feats, df_train)

    # Drop rows with NaN in any selected feature
    n_train_before = len(df_train)
    n_oot_before   = len(df_oot)
    train_used = df_train.dropna(subset=feats).copy()
    oot_used   = df_oot.dropna(subset=feats).copy()
    n_train_dropped = n_train_before - len(train_used)
    n_oot_dropped   = n_oot_before   - len(oot_used)

    X_train = train_used[feats]
    y_train = train_used[TARGET].astype(int).values
    X_oot   = oot_used[feats]
    y_oot   = oot_used[TARGET].astype(int).values

    transformers = []
    if num_cols:
        transformers.append(("num", StandardScaler(), num_cols))
    if cat_cols:
        transformers.append(("cat", make_one_hot_encoder(), cat_cols))
    pre = ColumnTransformer(transformers, remainder="drop")

    clf = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=RNG,
        solver="lbfgs",
    )
    pipe = Pipeline([("pre", pre), ("lr", clf)])
    pipe.fit(X_train, y_train)

    p_train = pipe.predict_proba(X_train)[:, 1]
    p_oot   = pipe.predict_proba(X_oot)[:, 1]

    auc_train = roc_auc_score(y_train, p_train)
    auc_oot   = roc_auc_score(y_oot,   p_oot)
    gini_train = 2.0 * auc_train - 1.0
    gini_oot   = 2.0 * auc_oot   - 1.0

    # Top-5 by |coef| using expanded feature names from the preprocessor
    expanded = list(pipe.named_steps["pre"].get_feature_names_out())
    coefs = pipe.named_steps["lr"].coef_.ravel()
    abs_idx = np.argsort(np.abs(coefs))[::-1][:5]
    top5 = [(expanded[i], float(coefs[i])) for i in abs_idx]

    return dict(
        set_name        = set_name,
        n_features      = len(feats),
        feats           = feats,
        n_train_used    = len(train_used),
        n_oot_used      = len(oot_used),
        n_train_dropped = n_train_dropped,
        n_oot_dropped   = n_oot_dropped,
        gini_train      = gini_train,
        gini_oot        = gini_oot,
        gap             = gini_train - gini_oot,
        top5            = top5,
    )


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------

def verdict_a(g):
    if g > 0.55:
        return ("Simulator HAS origination credit risk signal. "
                "Thesis can use origination-only benchmark.")
    if g >= 0.50:
        return ("Weak origination signal. Consider T=3 early behavioral "
                "as primary benchmark.")
    return ("No origination signal. Must redesign simulator or restrict "
            "thesis claim to behavioral scoring.")


def verdict_b(g_b, g_a):
    if (g_b - g_a) > 0.10:
        return "Early behavioral adds meaningful signal over origination."
    return ("Early behavioral does NOT add meaningful (>0.10) incremental "
            "signal over origination.")


def verdict_c(g):
    if g > 0.90:
        return ("Full trajectory is dominated by target-proxy leakage, "
                "confirmed. Cannot be primary benchmark.")
    return ("Full trajectory not in leakage band (>0.90); inspect "
            "features for proxy contamination.")


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def fmt_block(r):
    lines = [f"--- {r['set_name']} ---"]
    lines.append(f"N features: {r['n_features']}")
    lines.append(f"Features: {', '.join(r['feats'])}")
    lines.append(
        f"Train rows used: {r['n_train_used']:,} "
        f"(dropped {r['n_train_dropped']:,} due to NaN)"
    )
    lines.append(
        f"OOT rows used: {r['n_oot_used']:,} "
        f"(dropped {r['n_oot_dropped']:,} due to NaN)"
    )
    lines.append(f"Gini train: {r['gini_train']:.4f}")
    lines.append(f"Gini OOT:   {r['gini_oot']:.4f}")
    lines.append(f"Gap:        {r['gap']:.4f}")
    lines.append("Top 5 features by |coef|:")
    for i, (name, c) in enumerate(r["top5"], 1):
        lines.append(f"  {i}. {name}: {c:+.4f}")
    return "\n".join(lines)


# ===========================================================================
# TASK 1 -- Duration stratification
# ===========================================================================
#
# Hypothesis: if loan term genuinely predicts credit risk, the
# coefficient sign of the remaining loan-term features (loan_amount,
# installment) should be CONSISTENT across n_installments groups.
# A sign flip or magnitude blow-up between groups indicates that the
# loan-term signal is an artifact of the simulator's deterministic
# write_off rule (due_installments == 12), not genuine credit risk.

def _fit_lr_for_task1(X_train, y_train, X_oot, y_oot, num_cols, cat_cols):
    """Lower-level helper used by Task 1.  Returns (pipeline, gini_train,
    gini_oot)."""
    transformers = []
    if num_cols:
        transformers.append(("num", StandardScaler(), num_cols))
    if cat_cols:
        transformers.append(("cat", make_one_hot_encoder(), cat_cols))
    pre = ColumnTransformer(transformers, remainder="drop")
    clf = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=RNG,
        solver="lbfgs",
    )
    pipe = Pipeline([("pre", pre), ("lr", clf)])
    pipe.fit(X_train, y_train)
    p_train = pipe.predict_proba(X_train)[:, 1]
    p_oot   = pipe.predict_proba(X_oot)[:, 1]
    return (
        pipe,
        2.0 * roc_auc_score(y_train, p_train) - 1.0,
        2.0 * roc_auc_score(y_oot,   p_oot)   - 1.0,
    )


def _extract_numeric_coef(pipe, raw_name):
    """Look up the coefficient of a raw numeric feature in the fitted
    pipeline.  Returns NaN if not found (e.g. it ended up categorical)."""
    expanded = list(pipe.named_steps["pre"].get_feature_names_out())
    coefs    = pipe.named_steps["lr"].coef_.ravel()
    for name, c in zip(expanded, coefs):
        if name == f"num__{raw_name}":
            return float(c)
    return float("nan")


def task1_duration_stratification(df_train, df_oot):
    print("[diag] TASK 1: duration stratification")

    # SET A features minus n_installments (we are stratifying on it)
    num_cols_full = [c for c in SET_A_NUMERIC if c != "n_installments"]
    cat_cols_full = list(SET_A_CATEGORICAL)
    feats         = num_cols_full + cat_cols_full

    # Discover groups in train; sort ascending
    groups = sorted(df_train["n_installments"].dropna().unique().tolist())
    print(f"[diag]   duration groups discovered (train): {groups}")

    per_group = []
    for g in groups:
        tr = df_train[df_train["n_installments"] == g] \
                 .dropna(subset=feats).copy()
        oo = df_oot  [df_oot  ["n_installments"] == g] \
                 .dropna(subset=feats).copy()

        warns = []
        if len(tr) < 1000 or len(oo) < 1000:
            warns.append("  WARNING: group has < 1000 rows "
                         f"(train={len(tr)}, oot={len(oo)})")

        X_tr = tr[feats]
        y_tr = tr[TARGET].astype(int).values
        X_oo = oo[feats]
        y_oo = oo[TARGET].astype(int).values

        n_pos_tr = int(y_tr.sum()) if len(y_tr) else 0
        n_pos_oo = int(y_oo.sum()) if len(y_oo) else 0

        # Structural-zero-default guard: simulator's write_off rule is
        # due_installments == 12, so a loan with n_installments == 12
        # cannot accumulate 12 missed payments before maturing.  Such a
        # group has zero positive class and LR cannot fit.
        if n_pos_tr == 0:
            warns.append("  STRUCTURAL: train has 0 positive labels in "
                         "this group; LR fit skipped (likely a simulator "
                         "duration-bias artifact).")
            per_group.append(dict(
                group        = int(g),
                n_train      = len(tr),
                n_oot        = len(oo),
                train_rate   = 0.0,
                oot_rate     = (float(y_oo.mean()) if len(y_oo) else 0.0),
                gini_train   = float("nan"),
                gini_oot     = float("nan"),
                coef_loan    = float("nan"),
                coef_inst    = float("nan"),
                warn         = "\n".join(warns),
                skipped      = True,
                skip_reason  = "zero_positive_in_train",
            ))
            for w in warns:
                print(f"[diag]  {w.strip()}")
            print(f"[diag]   group {g}: SKIPPED (n_pos_train={n_pos_tr})")
            continue

        n_cols, c_cols = split_categorical_numeric(feats, tr)
        pipe, gini_tr, gini_oo = _fit_lr_for_task1(
            X_tr, y_tr, X_oo, y_oo, n_cols, c_cols
        )

        # OOT can have only one class -- AUC is then undefined
        if n_pos_oo == 0 or n_pos_oo == len(y_oo):
            gini_oo = float("nan")
            warns.append("  WARNING: OOT has degenerate class distribution; "
                         "Gini OOT undefined.")

        coef_loan = _extract_numeric_coef(pipe, "loan_amount")
        coef_inst = _extract_numeric_coef(pipe, "installment")

        per_group.append(dict(
            group        = int(g),
            n_train      = len(tr),
            n_oot        = len(oo),
            train_rate   = float(y_tr.mean()) if len(y_tr) else 0.0,
            oot_rate     = float(y_oo.mean()) if len(y_oo) else 0.0,
            gini_train   = gini_tr,
            gini_oot     = gini_oo,
            coef_loan    = coef_loan,
            coef_inst    = coef_inst,
            warn         = "\n".join(warns),
            skipped      = False,
            skip_reason  = "",
        ))
        print(f"[diag]   group {g}: gini_oot={gini_oo:.4f}  "
              f"coef_loan={coef_loan:+.4f}  coef_inst={coef_inst:+.4f}")

    # Cross-group analysis -------------------------------------------------
    # Skipped groups (NaN coefs) are excluded from sign-flip / magnitude
    # comparisons but COUNTED separately as a structural-artifact signal.
    fit_groups   = [r for r in per_group if not r["skipped"]]
    skip_groups  = [r for r in per_group if r["skipped"]]
    n_skipped    = len(skip_groups)

    sign_of = lambda x: "+" if x >= 0 else "-"
    coef_loans = [r["coef_loan"] for r in fit_groups]
    coef_insts = [r["coef_inst"] for r in fit_groups]

    if len(fit_groups) >= 2:
        sign_flip_loan = len({sign_of(c) for c in coef_loans}) > 1
        sign_flip_inst = len({sign_of(c) for c in coef_insts}) > 1
    else:
        sign_flip_loan = False
        sign_flip_inst = False
    sign_flip = sign_flip_loan or sign_flip_inst

    def magnitude_ratio(vs):
        m = [abs(v) for v in vs if v == v and v != 0.0]
        if len(m) < 2:
            return float("nan"), False
        ratio = max(m) / min(m)
        return ratio, ratio > 3.0

    loan_ratio, loan_big = magnitude_ratio(coef_loans)
    inst_ratio, inst_big = magnitude_ratio(coef_insts)
    mag_var_big = loan_big or inst_big

    # Default-rate ratio across ALL groups (including skipped: rate=0)
    # If a group has 0 default rate while another has > 0, ratio is
    # infinite -- treat as "strong duration-default correlation".
    train_rates_all = [r["train_rate"] for r in per_group]
    has_zero_rate = any(rt == 0.0 for rt in train_rates_all)
    pos_rates     = [rt for rt in train_rates_all if rt > 0]

    if has_zero_rate and pos_rates:
        rate_ratio   = float("inf")
        rate_var_big = True
    elif pos_rates:
        rate_ratio   = max(pos_rates) / min(pos_rates)
        rate_var_big = rate_ratio > 5.0
    else:
        rate_ratio   = 0.0
        rate_var_big = False

    # Structural-zero in any group = automatic duration-artifact verdict.
    # Otherwise apply spec rules on sign/magnitude.
    if n_skipped > 0:
        verdict = (
            f"Loan term coefficients unstable across durations "
            f"({n_skipped} group(s) had structurally zero defaults and "
            f"could not be fit). Confirms simulator duration artifact. "
            f"Loan terms should be flagged as benchmark-contaminated "
            f"features."
        )
    elif sign_flip or mag_var_big:
        verdict = ("Loan term coefficients unstable across durations. "
                   "Confirms simulator duration artifact. Loan terms "
                   "should be flagged as benchmark-contaminated features.")
    else:
        verdict = ("Loan terms have genuine risk signal; high Gini in "
                   "full SET A is not solely due to duration artifact.")

    rate_note = ""
    if rate_var_big:
        rate_note = ("Strong duration-default correlation beyond what "
                     "loan terms can explain. Simulator write-off "
                     "mechanics are duration-biased.")

    return dict(
        groups          = [int(g) for g in groups],
        per_group       = per_group,
        sign_flip       = sign_flip,
        sign_flip_loan  = sign_flip_loan,
        sign_flip_inst  = sign_flip_inst,
        mag_var_big     = mag_var_big,
        loan_ratio      = loan_ratio,
        inst_ratio      = inst_ratio,
        rate_ratio      = rate_ratio,
        rate_var_big    = rate_var_big,
        n_skipped       = n_skipped,
        verdict         = verdict,
        rate_note       = rate_note,
    )


def _fmt_signed(x):
    """Format a value as +x.xxxx or -x.xxxx, or 'N/A' if NaN."""
    if x != x:  # NaN
        return "N/A"
    return f"{x:+.4f}"


def _fmt_gini(x):
    if x != x:
        return "N/A    "
    return f"{x:.4f}"


def _fmt_ratio(x):
    if x != x:
        return "N/A"
    if x == float("inf"):
        return "inf"
    return f"{x:.2f}"


def _sign_str(x):
    if x != x:
        return "N/A"
    return "+" if x >= 0 else "-"


def fmt_task1(t1):
    out = ["=== TASK 1: DURATION STRATIFICATION ===", ""]
    out.append(f"Duration groups found: {t1['groups']}")
    if t1["n_skipped"] > 0:
        out.append(f"Groups skipped (zero positive labels in train): "
                   f"{t1['n_skipped']}")
    out.append("")
    for r in t1["per_group"]:
        out.append(f"--- Group n_installments={r['group']} ---")
        out.append(f"Train rows: {r['n_train']:,}")
        out.append(f"Train default rate: {r['train_rate']*100:.4f}%")
        out.append(f"OOT rows: {r['n_oot']:,}")
        out.append(f"OOT default rate: {r['oot_rate']*100:.4f}%")
        if r.get("skipped"):
            out.append("Gini train: N/A  (LR fit skipped)")
            out.append("Gini OOT:   N/A  (LR fit skipped)")
            out.append("Coef loan_amount: N/A")
            out.append("Coef installment: N/A")
        else:
            out.append(f"Gini train: {_fmt_gini(r['gini_train'])}")
            out.append(f"Gini OOT:   {_fmt_gini(r['gini_oot'])}")
            out.append(f"Coef loan_amount: {_fmt_signed(r['coef_loan'])} "
                       f"(sign: {_sign_str(r['coef_loan'])})")
            out.append(f"Coef installment: {_fmt_signed(r['coef_inst'])} "
                       f"(sign: {_sign_str(r['coef_inst'])})")
        if r.get("warn"):
            out.append(r["warn"])
        out.append("")

    out.append("--- CROSS-GROUP COEFFICIENT COMPARISON ---")
    out.append("| Group | n_installments | loan_amount coef | installment coef |")
    for r in t1["per_group"]:
        loan_s = _fmt_signed(r["coef_loan"])
        inst_s = _fmt_signed(r["coef_inst"])
        out.append(
            f"| {r['group']:<5} | (stratified)   "
            f"| {loan_s:<16} | {inst_s:<16} |"
        )
    out.append("")
    out.append("--- VERDICT TASK 1 ---")
    out.append(f"Structural-zero groups: {t1['n_skipped']} of {len(t1['groups'])}")
    out.append(f"Sign flip detected: {'YES' if t1['sign_flip'] else 'NO'}  "
               f"(loan: {'YES' if t1['sign_flip_loan'] else 'NO'}, "
               f"installment: {'YES' if t1['sign_flip_inst'] else 'NO'})")
    out.append(f"Magnitude variation >3x: {'YES' if t1['mag_var_big'] else 'NO'}  "
               f"(loan ratio={_fmt_ratio(t1['loan_ratio'])}, "
               f"inst ratio={_fmt_ratio(t1['inst_ratio'])})")
    out.append(f"Default-rate variation >5x: "
               f"{'YES' if t1['rate_var_big'] else 'NO'}  "
               f"(ratio={_fmt_ratio(t1['rate_ratio'])})")
    out.append(f"Interpretation: {t1['verdict']}")
    if t1["rate_note"]:
        out.append(f"Additional: {t1['rate_note']}")
    return "\n".join(out)


# ===========================================================================
# TASK 2 -- SET A' demographics-only (no loan terms, no behavioral)
# ===========================================================================

SET_A_PRIME_NUMERIC = [
    "app_income",
    "app_number_of_children",
    "app_spendings",
    "act_age",
]
SET_A_PRIME_CATEGORICAL = [
    "app_nom_gender",
    "app_nom_marital_status",
    "app_nom_home_status",
    "app_nom_cars",
    "app_nom_job_code",
]


def task2_demographics_only(df_train, df_oot, available):
    print("[diag] TASK 2: SET A' demographics-only")
    set_ap = SET_A_PRIME_NUMERIC + SET_A_PRIME_CATEGORICAL
    assert_features_exist(set_ap, available, "SET A'")
    res = fit_and_score(df_train, df_oot, set_ap,
                        "SET A': Demographics-only")
    print(f"[diag]   SET A'  gini_oot = {res['gini_oot']:.4f}")
    return res


def verdict_task2(g):
    if g < 0.55:
        return ("Demographics-only gives realistic signal level. "
                "Thesis CAN use SET A' as primary benchmark "
                "representing real-world-like discrimination.")
    if g <= 0.75:
        return ("Demographics-only still higher than typical real-world "
                "but within acceptable range. Viable benchmark with "
                "limitation note.")
    return ("Demographics alone still produce high discrimination. "
            "Simulator artifact extends beyond loan terms to demographic "
            "encoding. Must use Option 3 (thesis reframe + score "
            "calibration).")


def fmt_task2(res_ap, res_a, res_b, res_c):
    g_ap = res_ap["gini_oot"]
    out = ["=== TASK 2: SET A' -- DEMOGRAPHICS-ONLY (NO LOAN TERMS) ===", ""]
    out.append(f"N features: {res_ap['n_features']}")
    out.append(f"Features: {', '.join(res_ap['feats'])}")
    out.append(f"Train rows used: {res_ap['n_train_used']:,} "
               f"(dropped {res_ap['n_train_dropped']:,} due to NaN)")
    out.append(f"OOT rows used: {res_ap['n_oot_used']:,} "
               f"(dropped {res_ap['n_oot_dropped']:,} due to NaN)")
    out.append(f"Gini train: {res_ap['gini_train']:.4f}")
    out.append(f"Gini OOT:   {res_ap['gini_oot']:.4f}")
    out.append(f"Gap:        {res_ap['gap']:.4f}")
    out.append("Top 5 features by |coef|:")
    for i, (name, c) in enumerate(res_ap["top5"], 1):
        out.append(f"  {i}. {name}: {c:+.4f}")
    out.append("")
    out.append("--- COMPARISON WITH SET A ---")
    out.append("| Set | N features | Gini OOT | Delta vs SET A' |")
    out.append(f"| A'  | {res_ap['n_features']:<10} "
               f"| {g_ap:.4f}   | baseline        |")
    out.append(f"| A   | 12         | {res_a['gini_oot']:.4f}   "
               f"| {res_a['gini_oot']-g_ap:+.4f}         |")
    out.append(f"| B   | 21         | {res_b['gini_oot']:.4f}   "
               f"| {res_b['gini_oot']-g_ap:+.4f}         |")
    out.append(f"| C   | 117        | {res_c['gini_oot']:.4f}   "
               f"| {res_c['gini_oot']-g_ap:+.4f}         |")
    out.append("")
    out.append("--- VERDICT TASK 2 ---")
    out.append(f"Gini OOT of A':  {g_ap:.4f}")
    out.append(f"Interpretation: {verdict_task2(g_ap)}")
    return "\n".join(out)


# ===========================================================================
# TASK 3 -- Final diagnostic summary / recommended scenario
# ===========================================================================

def fmt_task3(t1, res_ap):
    g_ap = res_ap["gini_oot"]
    duration_artifact = (
        t1["sign_flip"] or t1["mag_var_big"] or t1["rate_var_big"]
    )

    if g_ap < 0.75:
        scenario = 1
        reasoning = (
            f"SET A' OOT Gini = {g_ap:.4f} < 0.75 -- demographics-only "
            f"benchmark is viable. Drop loan term features and proceed "
            f"with APR cut-off framework on SET A'."
        )
    elif g_ap >= 0.75 and duration_artifact:
        scenario = 2
        reasoning = (
            f"SET A' OOT Gini = {g_ap:.4f} >= 0.75 AND Task 1 confirmed "
            f"duration artifact -- demographic encoding itself is "
            f"contributing to the inflated signal. Thesis must reframe "
            f"with score calibration to realistic Gini levels."
        )
    else:
        scenario = 3
        reasoning = (
            f"SET A' OOT Gini = {g_ap:.4f} and Task 1 verdict do not "
            f"jointly point to a single fix. Escalate to supervisor for "
            f"simulator-redesign vs. public-dataset decision."
        )

    out = [
        "=== FINAL DIAGNOSTIC SUMMARY ===",
        "",
        "Benchmark candidates ranked by thesis viability:",
        "",
        "Scenario 1 -- SET A' (demographics-only) if Gini OOT < 0.75:",
        "  Primary benchmark for thesis",
        "  Ban loan term features explicitly in thesis spec",
        "  APR cut-off framework applied on this benchmark",
        "",
        "Scenario 2 -- SET A' Gini > 0.75 AND duration artifact confirmed:",
        "  Thesis must reframe to methodology contribution",
        "  Add score calibration experiment (noise injection to degrade",
        "    Gini to realistic level)",
        "  Run cut-off analysis at multiple calibrated Gini levels",
        "",
        "Scenario 3 -- Both Task 1 and Task 2 verdicts negative:",
        "  Must escalate to supervisor",
        "  Options: (a) redesign simulator noise layer (large scope),",
        "           (b) switch to public benchmark dataset (HMEQ, Give Me",
        "               Some Credit) for empirical portion",
        "",
        f"Recommended scenario based on current results: SCENARIO {scenario}",
        f"Reasoning: {reasoning}",
    ]
    return "\n".join(out)


# ===========================================================================
# TASK 4 -- Re-run SET A and SET A' after excluding n_installments=12
# ===========================================================================
#
# n_installments=12 group has structurally-zero defaults: the simulator's
# write-off rule (due_installments == 12) is impossible to trigger on a
# 12-installment loan that matures at month 12 -- no loan can accumulate
# 12 *missed* payments in its own 12-period lifespan.  Including this group
# contaminates training with a deterministic label artifact.
#
# This task measures whether Gini drops to a defensible range once the
# structurally-invalid cohort is removed.

def task4_filtered_rerun(df_train, df_oot, available, res_a_orig, res_ap_orig):
    print("[diag] TASK 4: re-run after dropping n_installments=12")

    # --- Filter -----------------------------------------------------------
    tr_orig_n  = len(df_train)
    oo_orig_n  = len(df_oot)
    tr_orig_dr = float(df_train[TARGET].mean())
    oo_orig_dr = float(df_oot[TARGET].mean())

    tr_f = df_train[df_train["n_installments"] != 12].copy()
    oo_f = df_oot  [df_oot  ["n_installments"] != 12].copy()

    tr_filt_n  = len(tr_f)
    oo_filt_n  = len(oo_f)
    tr_filt_dr = float(tr_f[TARGET].mean())
    oo_filt_dr = float(oo_f[TARGET].mean())

    tr_drop_pct = (tr_orig_n - tr_filt_n) / tr_orig_n * 100
    oo_drop_pct = (oo_orig_n - oo_filt_n) / oo_orig_n * 100

    print(f"[diag]   train: {tr_orig_n:,} -> {tr_filt_n:,} "
          f"(-{tr_drop_pct:.1f}%)  "
          f"default rate: {tr_orig_dr*100:.4f}% -> {tr_filt_dr*100:.4f}%")
    print(f"[diag]   oot  : {oo_orig_n:,} -> {oo_filt_n:,} "
          f"(-{oo_drop_pct:.1f}%)  "
          f"default rate: {oo_orig_dr*100:.4f}% -> {oo_filt_dr*100:.4f}%")

    # --- SET A filtered (12 features, include loan terms) -----------------
    set_a = SET_A_NUMERIC + SET_A_CATEGORICAL
    assert_features_exist(set_a, available, "SET A (Task 4)")
    print("[diag]   fitting SET A (filtered) ...")
    res_af = fit_and_score(tr_f, oo_f, set_a, "SET A (filtered)")
    print(f"[diag]   SET A (filtered) gini_oot = {res_af['gini_oot']:.4f}")

    # --- SET A' filtered (9 features, demographics only) -----------------
    set_ap = SET_A_PRIME_NUMERIC + SET_A_PRIME_CATEGORICAL
    assert_features_exist(set_ap, available, "SET A' (Task 4)")
    print("[diag]   fitting SET A' (filtered) ...")
    res_apf = fit_and_score(tr_f, oo_f, set_ap, "SET A' (filtered)")
    print(f"[diag]   SET A' (filtered) gini_oot = {res_apf['gini_oot']:.4f}")

    return dict(
        tr_orig_n   = tr_orig_n,
        oo_orig_n   = oo_orig_n,
        tr_orig_dr  = tr_orig_dr,
        oo_orig_dr  = oo_orig_dr,
        tr_filt_n   = tr_filt_n,
        oo_filt_n   = oo_filt_n,
        tr_filt_dr  = tr_filt_dr,
        oo_filt_dr  = oo_filt_dr,
        tr_drop_pct = tr_drop_pct,
        oo_drop_pct = oo_drop_pct,
        res_af      = res_af,
        res_apf     = res_apf,
        # originals for comparison table
        g_a_orig    = res_a_orig["gini_oot"],
        g_ap_orig   = res_ap_orig["gini_oot"],
    )


def verdict_task4(g_apf):
    """Hardcoded scenario rules based on SET A' filtered OOT Gini."""
    if g_apf < 0.60:
        return (1, "Clean benchmark achieved. SET A' (filtered) viable as "
                   "primary benchmark. Score calibration optional robustness "
                   "check.")
    if g_apf < 0.70:
        return (2, "Benchmark acceptable but elevated. Use SET A' (filtered) "
                   "as primary. Add score calibration experiment as thesis "
                   "robustness contribution.")
    if g_apf < 0.85:
        return (3, "Benchmark borderline. Use SET A' (filtered) but score "
                   "calibration experiment is mandatory. Thesis framing must "
                   "emphasize methodology contribution over empirical realism.")
    return (4, "Artifact persists beyond duration. Escalate to supervisor. "
               "Options: (a) redesign simulator noise layer (large scope), "
               "(b) switch to public benchmark dataset (HMEQ, Give Me Some "
               "Credit) for empirical portion.")


def fmt_task4(t4):
    res_af  = t4["res_af"]
    res_apf = t4["res_apf"]
    g_apf   = res_apf["gini_oot"]
    scenario, verdict_text = verdict_task4(g_apf)

    def pct(n, orig):
        return (orig - n) / orig * 100

    out = ["=== TASK 4: RE-RUN AFTER DROPPING n_installments=12 ===", ""]
    out.append("--- DATA FILTERING ---")
    out.append(f"Original train rows: {t4['tr_orig_n']:,}")
    out.append(f"Original OOT rows: {t4['oo_orig_n']:,}")
    out.append(f"Original train default rate: {t4['tr_orig_dr']*100:.4f}%")
    out.append(f"Original OOT default rate: {t4['oo_orig_dr']*100:.4f}%")
    out.append("")
    out.append(f"Filtered train rows (n_installments != 12): "
               f"{t4['tr_filt_n']:,} (-{t4['tr_drop_pct']:.1f}%)")
    out.append(f"Filtered OOT rows (n_installments != 12): "
               f"{t4['oo_filt_n']:,} (-{t4['oo_drop_pct']:.1f}%)")
    out.append(f"Filtered train default rate: {t4['tr_filt_dr']*100:.4f}%")
    out.append(f"Filtered OOT default rate: {t4['oo_filt_dr']*100:.4f}%")
    out.append("")
    out.append("--- SET A (FILTERED) ---")
    out.append(f"N features: {res_af['n_features']}")
    out.append(f"Train rows: {res_af['n_train_used']:,}")
    out.append(f"OOT rows: {res_af['n_oot_used']:,}")
    out.append(f"Gini train: {res_af['gini_train']:.4f}")
    out.append(f"Gini OOT:   {res_af['gini_oot']:.4f}")
    out.append(f"Gap:        {res_af['gap']:.4f}")
    out.append("Top 5 features by |coef|:")
    for i, (name, c) in enumerate(res_af["top5"], 1):
        out.append(f"  {i}. {name}: {c:+.4f}")
    out.append("")
    out.append("--- SET A' (FILTERED) ---")
    out.append(f"N features: {res_apf['n_features']}")
    out.append(f"Train rows: {res_apf['n_train_used']:,}")
    out.append(f"OOT rows: {res_apf['n_oot_used']:,}")
    out.append(f"Gini train: {res_apf['gini_train']:.4f}")
    out.append(f"Gini OOT:   {res_apf['gini_oot']:.4f}")
    out.append(f"Gap:        {res_apf['gap']:.4f}")
    out.append("Top 5 features by |coef|:")
    for i, (name, c) in enumerate(res_apf["top5"], 1):
        out.append(f"  {i}. {name}: {c:+.4f}")
    out.append("")
    out.append("--- COMPARISON: ORIGINAL vs FILTERED ---")
    out.append("| Set | Original Gini OOT | Filtered Gini OOT | Delta  |")
    out.append(f"| A   | {t4['g_a_orig']:.4f}            "
               f"| {res_af['gini_oot']:.4f}             "
               f"| {res_af['gini_oot'] - t4['g_a_orig']:+.4f} |")
    out.append(f"| A'  | {t4['g_ap_orig']:.4f}            "
               f"| {res_apf['gini_oot']:.4f}             "
               f"| {res_apf['gini_oot'] - t4['g_ap_orig']:+.4f} |")
    out.append("")
    out.append("--- VERDICT TASK 4 ---")
    out.append(f"Primary benchmark Gini OOT (SET A' filtered): {g_apf:.4f}")
    out.append(f"Scenario triggered: {scenario}")
    out.append(f"Interpretation: {verdict_text}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    np.random.seed(RNG)

    abt = load_abt()

    if SPLIT_COL not in abt.columns:
        sys.exit(f"ERROR: split column '{SPLIT_COL}' not in ABT")
    if TARGET not in abt.columns:
        sys.exit(f"ERROR: target column '{TARGET}' not in ABT")

    df_train = abt[abt[SPLIT_COL] == "train"].copy()
    df_oot   = abt[abt[SPLIT_COL] == "oot"].copy()
    print(f"[diag] train rows: {len(df_train):,}  oot rows: {len(df_oot):,}")

    available = set(abt.columns)

    set_a = SET_A_NUMERIC + SET_A_CATEGORICAL
    assert_features_exist(set_a, available, "SET A")

    set_b = set_a + SET_B_EXTRA
    assert_features_exist(set_b, available, "SET B")

    stage1 = load_stage1_features()
    set_c = stage1
    assert_features_exist(set_c, available, "SET C")

    print("[diag] fitting SET A ...")
    res_a = fit_and_score(df_train, df_oot, set_a, "SET A: Origination-only")
    print(f"[diag]   SET A  gini_oot = {res_a['gini_oot']:.4f}")

    print("[diag] fitting SET B ...")
    res_b = fit_and_score(df_train, df_oot, set_b,
                          "SET B: Origination + Early behavioral")
    print(f"[diag]   SET B  gini_oot = {res_b['gini_oot']:.4f}")

    print("[diag] fitting SET C ...")
    res_c = fit_and_score(df_train, df_oot, set_c, "SET C: Full trajectory")
    print(f"[diag]   SET C  gini_oot = {res_c['gini_oot']:.4f}")

    # ----- TASK 1: duration stratification ----------------------------
    t1 = task1_duration_stratification(df_train, df_oot)

    # ----- TASK 2: SET A' demographics-only ---------------------------
    res_ap = task2_demographics_only(df_train, df_oot, available)

    # ----- TASK 4: re-run SET A + A' on filtered data -----------------
    t4 = task4_filtered_rerun(df_train, df_oot, available, res_a, res_ap)

    train_rate = float(df_train[TARGET].mean())
    oot_rate   = float(df_oot[TARGET].mean())

    lines = [
        "=== BENCHMARK DIAGNOSTIC REPORT ===",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"ABT: {ABT_CSV.relative_to(REPO_ROOT)}",
        f"Train rows: {len(df_train):,}",
        f"OOT rows: {len(df_oot):,}",
        f"Train default rate: {train_rate*100:.4f}%",
        f"OOT default rate: {oot_rate*100:.4f}%",
        "",
        "Note on SET B feature substitution:",
        "  Spec requested m1 versions of act_due, coll_status, act_dueutl.",
        "  Those columns are constant-zero at the origination month",
        "  (no installment is yet due) and were dropped by Step 8A of",
        "  the ABT build (constant-column filter).  We substitute the",
        "  first three months that DO carry signal: m2, m3, m4.",
        "",
        fmt_block(res_a),
        "",
        fmt_block(res_b),
        "",
        fmt_block(res_c),
        "",
        "--- INTERPRETATION TABLE ---",
        "| Set | Gini OOT | Verdict |",
        f"| A   | {res_a['gini_oot']:.4f}   | {verdict_a(res_a['gini_oot'])} |",
        f"| B   | {res_b['gini_oot']:.4f}   | {verdict_b(res_b['gini_oot'], res_a['gini_oot'])} |",
        f"| C   | {res_c['gini_oot']:.4f}   | {verdict_c(res_c['gini_oot'])} |",
        "",
        # ----- TASK 1/2/3 sections (appended, do not overwrite SET A/B/C)
        fmt_task1(t1),
        "",
        fmt_task2(res_ap, res_a, res_b, res_c),
        "",
        fmt_task3(t1, res_ap),
        "",
        fmt_task4(t4),
        "",
    ]
    report = "\n".join(lines)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(report, encoding="utf-8")
    print(f"\n[diag] report saved: {OUT_PATH}")
    print()
    print(report)


if __name__ == "__main__":
    main()
