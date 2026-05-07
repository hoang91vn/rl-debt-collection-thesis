"""
phase1_5_feature_factory.py
============================

Expand the cleaned wide ABT raw-variable universe to 2000+ features with
governance metadata, supporting Phase 2 prescreening via catalog filters.

Inputs (read-only):
  artifacts/thesis_wide_abt_12m_500c_clean/thesis_wide_abt.csv
  artifacts/thesis_wide_abt_12m_500c_clean/thesis_wide_abt_report.txt

Outputs (artifacts/phase1_5_feature_factory/):
  thesis_wide_abt_expanded.parquet  (or .csv.gz fallback)
  feature_catalog.csv               (14-field governance for every column)
  feature_family_summary.txt
  phase1_5_report.md
  run_config.json

Usage:
  uv run python scripts/phase1_5_feature_factory.py

Design principles
-----------------
1. Feature factory is RAW universe expansion only. Nothing here is auto-
   eligible for PD modeling -- catalog flags drive Phase 2 selection.
2. Every feature has 14-field governance metadata.
3. Behavioral m4-m12 trajectory features are flagged high risk (level C)
   and excluded from origination PD by default.
4. NO target encoding. NO group default-rate features.
5. Source-based restrictions OVERRIDE family-based defaults via
   Rule Precedence (most restrictive wins).
6. Family 5A train-only group statistics with global-train fallback for
   unseen OOT groups.
7. F6E synthetic-bureau features generated ONLY from safe app vars +
   seeded noise -- never from loan terms, behavioral, or target.

Rule precedence (most restrictive first):
  A. Target involvement                     -> not allowed for any modeling
  B. ID/split/metadata                      -> not allowed for modeling
  C. Late behavioral m4-m12 / agr6/agr12    -> high risk, no orig PD
  D. Aggregate behavioral target-proxy      -> high risk, no orig PD
  E. Loan-term / duration / zero-int        -> no orig PD (profit input)
  F. Early behavioral m1-m3                 -> medium risk, behavioral-only
  G. Safe application/origination           -> allowed for PD, low risk
  H. Pure random negative controls          -> low risk, allowed for PD
"""

from __future__ import annotations

import gc
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# =============================================================================
# Constants
# =============================================================================

SEED = 42
INPUT_CSV = Path("artifacts/thesis_wide_abt_800d_60m_p00/thesis_wide_abt.csv")
OUTPUT_DIR = Path("artifacts/phase1_5_feature_factory")

# Governance metadata fields (14)
GOV_FIELDS = [
    "feature_name", "feature_family", "source_columns", "formula",
    "description", "availability_time", "source_window",
    "uses_target", "uses_future_behavior",
    "allowed_for_origination_pd", "allowed_for_behavioral_pd",
    "allowed_for_profit", "leakage_risk", "reason_if_not_allowed_for_pd",
]

# Original-column classification patterns
TARGET_PATTERNS = [r"^default", r"^writeoff", r"^write_off",
                   r"^bad_flag", r"^target", r"^y_true$", r"^y$", r"^label$"]
ID_COLS = {"aid", "cid", "fin_period", "obs_period",
           "observation_id", "client_id", "account_id", "application_id",
           "snapshot_date", "date", "scenario", "seed"}
SPLIT_COLS = {"split", "sample", "dataset_split", "partition"}
META_COLS = {"observation_status"}

# Behavioral pattern: REQUIRES month suffix _m<digit>+
BEHAVIORAL_RE = re.compile(r"^(act|coll|due|paid)_.*_m(\d+)$")

# Aggregate behavioral target-proxy (level D)
AGGREGATE_BEHAVIORAL = {
    "max_due", "max_coll_status", "trend_due",
    "months_ever_due", "months_coll_2plus", "paid_fraction_at_obs",
}
AGGREGATE_PREFIXES = ("agr6_", "agr12_", "ags6_", "ags12_")  # level C high risk

# Loan-term columns (level E)
LOAN_TERM_COLS = {
    "loan_amount", "app_loan_amount",
    "n_installments", "app_n_installments",
    "installment", "principal", "term", "tenor",
}

# Safe app columns (level G) - applied as set membership after loan-term/behav check
SAFE_APP_COLS_KNOWN = {
    "act_age", "app_age",
    "app_income", "app_spendings",
    "app_number_of_children",
    "app_nom_marital_status", "app_nom_job_code", "app_nom_home_status",
    "app_nom_branch", "app_nom_city", "app_nom_education",
    "app_nom_gender", "app_nom_cars",
}

# Categorical safe columns (used as group keys, NOT for rank transforms)
CATEGORICAL_SAFE = {
    "app_nom_branch", "app_nom_gender", "app_nom_job_code",
    "app_nom_marital_status", "app_nom_city", "app_nom_home_status",
    "app_nom_education",
}

# =============================================================================
# Logging
# =============================================================================

_log_lines: list[str] = []
_t0 = time.time()


def log(msg: str = "") -> None:
    elapsed = time.time() - _t0
    line = f"[{elapsed:7.1f}s] {msg}"
    print(line, flush=True)
    _log_lines.append(line)


def hr() -> None:
    log("-" * 70)


def rule() -> None:
    log("=" * 70)


# =============================================================================
# Step A: load + classify originals
# =============================================================================

def load_abt(path: Path) -> pd.DataFrame:
    log(f"Loading ABT: {path}")
    if not path.exists():
        log(f"ERROR: input ABT not found at {path}")
        log("       The cleaned wide ABT must exist before running feature factory.")
        log("       Regenerate via: uv run python scripts/build_wide_abt.py")
        sys.exit(1)
    df = pd.read_csv(path)
    log(f"  loaded {len(df):,} rows x {len(df.columns)} cols  "
        f"(memory: {df.memory_usage(deep=True).sum() / 1024**2:.0f} MB)")
    return df


def detect_aliases(cols: set[str]) -> dict:
    """Detect actual column names for canonical aliases."""
    found = {}
    # age
    for c in ("act_age", "app_age", "age"):
        if c in cols:
            found["age"] = c
            break
    # loan amount: prefer app_*, else booked
    for c in ("app_loan_amount", "loan_amount", "principal"):
        if c in cols:
            found["loan_amount"] = c
            break
    # tenor
    for c in ("app_n_installments", "n_installments", "term", "tenor"):
        if c in cols:
            found["n_installments"] = c
            break
    # installment
    for c in ("installment", "app_installment", "monthly_payment"):
        if c in cols:
            found["installment"] = c
            break
    # split
    for c in ("split", "sample", "dataset_split", "partition"):
        if c in cols:
            found["split"] = c
            break
    return found


def check_duplicate_columns(df: pd.DataFrame) -> tuple[list[str], dict]:
    """Detect identical app_* vs booked columns; return (cols_to_drop, info)."""
    pairs = [
        ("app_loan_amount",   "loan_amount"),
        ("app_n_installments", "n_installments"),
    ]
    drop: list[str] = []
    info: dict = {}
    for app_col, acct_col in pairs:
        if app_col not in df.columns or acct_col not in df.columns:
            info[f"{app_col}_vs_{acct_col}"] = "one_or_both_missing"
            continue
        # exact equality test (faster than corr)
        same_mask = (df[app_col] == df[acct_col])
        n_same = int(same_mask.sum())
        n_total = len(df)
        if n_same == n_total:
            log(f"  DUPLICATE: {app_col} == {acct_col} (perfect equality, "
                f"dropping {app_col})")
            drop.append(app_col)
            info[f"{app_col}_vs_{acct_col}"] = "perfect_equality"
        else:
            # check correlation for near-duplicates
            try:
                corr = df[app_col].corr(df[acct_col])
            except Exception:
                corr = float("nan")
            if pd.notna(corr) and corr > 0.9999:
                log(f"  NEAR-DUPLICATE: {app_col} vs {acct_col} corr={corr:.6f} "
                    f"(dropping {app_col})")
                drop.append(app_col)
                info[f"{app_col}_vs_{acct_col}"] = f"near_duplicate_corr_{corr:.6f}"
            else:
                log(f"  DISTINCT: {app_col} vs {acct_col} corr={corr:.4f} "
                    f"({n_same}/{n_total} rows match) -> keeping both")
                info[f"{app_col}_vs_{acct_col}"] = (
                    f"distinct_corr_{corr:.4f}_match_{n_same}_of_{n_total}")
    return drop, info


def classify_original(col: str) -> tuple[str, str, str, dict]:
    """Return (family, level, source_window, governance_overrides) for a column."""
    # Level A: target
    for pat in TARGET_PATTERNS:
        if re.match(pat, col):
            return ("ORIGINAL_TARGET", "A", "metadata", {
                "uses_target": True,
                "allowed_for_origination_pd": False,
                "allowed_for_behavioral_pd": False,
                "allowed_for_profit": False,
                "leakage_risk": "high",
                "reason_if_not_allowed_for_pd": "target / outcome variable",
            })
    # Level B: ID / split / meta
    if col in ID_COLS:
        return ("ORIGINAL_ID", "B", "metadata", {
            "allowed_for_origination_pd": False,
            "allowed_for_behavioral_pd": False,
            "allowed_for_profit": False,
            "leakage_risk": "low",
            "reason_if_not_allowed_for_pd": "ID/metadata column, not a predictor",
        })
    if col in SPLIT_COLS:
        return ("ORIGINAL_SPLIT", "B", "metadata", {
            "allowed_for_origination_pd": False,
            "allowed_for_behavioral_pd": False,
            "allowed_for_profit": False,
            "leakage_risk": "low",
            "reason_if_not_allowed_for_pd": "train/OOT split column",
        })
    if col in META_COLS:
        return ("ORIGINAL_OTHER", "B", "metadata", {
            "allowed_for_origination_pd": False,
            "allowed_for_behavioral_pd": False,
            "allowed_for_profit": False,
            "leakage_risk": "low",
            "reason_if_not_allowed_for_pd": "observation metadata",
        })
    # Level D: aggregate behavioral target-proxy
    if col in AGGREGATE_BEHAVIORAL:
        return ("ORIGINAL_BEHAVIORAL", "D", "m1-m12", {
            "uses_future_behavior": True,
            "allowed_for_origination_pd": False,
            "allowed_for_behavioral_pd": False,
            "allowed_for_profit": False,
            "leakage_risk": "high",
            "reason_if_not_allowed_for_pd":
                "aggregate behavioral target-proxy (post-origination)",
        })
    if col.startswith(AGGREGATE_PREFIXES):
        # agr6_*, agr12_*: behavioral summary stats (level C)
        win = "m1-m6" if col.startswith(("agr6_", "ags6_")) else "m1-m12"
        return ("ORIGINAL_BEHAVIORAL", "C", win, {
            "uses_future_behavior": True,
            "allowed_for_origination_pd": False,
            "allowed_for_behavioral_pd": False,  # high risk -> exclude
            "allowed_for_profit": False,
            "leakage_risk": "high",
            "reason_if_not_allowed_for_pd":
                "behavioral summary aggregate (post-origination)",
        })
    # Behavioral with month suffix
    m = BEHAVIORAL_RE.match(col)
    if m:
        month = int(m.group(2))
        if month <= 3:
            # Level F: early behavioral
            return ("ORIGINAL_BEHAVIORAL", "F", f"m{month}", {
                "uses_future_behavior": True,
                "allowed_for_origination_pd": False,
                "allowed_for_behavioral_pd": True,
                "allowed_for_profit": False,
                "leakage_risk": "medium",
                "reason_if_not_allowed_for_pd":
                    "early behavioral (m1-m3), post-origination",
            })
        else:
            # Level C: late behavioral m4-m12
            return ("ORIGINAL_BEHAVIORAL", "C", f"m{month}", {
                "uses_future_behavior": True,
                "allowed_for_origination_pd": False,
                "allowed_for_behavioral_pd": False,
                "allowed_for_profit": False,
                "leakage_risk": "high",
                "reason_if_not_allowed_for_pd":
                    "late behavioral (m4-m12), post-origination",
            })
    # Level E: loan-term
    if col in LOAN_TERM_COLS:
        return ("ORIGINAL_LOAN", "E", "static", {
            "allowed_for_origination_pd": False,
            "allowed_for_behavioral_pd": False,
            "allowed_for_profit": True,  # loan terms ARE profit inputs
            "leakage_risk": "medium",
            "reason_if_not_allowed_for_pd":
                "duration/zero-interest artifact; profit input not PD predictor",
        })
    # Level G: safe application
    if col in SAFE_APP_COLS_KNOWN or col.startswith("app_"):
        return ("ORIGINAL_APP", "G", "static", {
            "allowed_for_origination_pd": True,
            "allowed_for_behavioral_pd": True,
            "allowed_for_profit": False,
            "leakage_risk": "low",
            "reason_if_not_allowed_for_pd": "",
        })
    # Default: OTHER
    return ("ORIGINAL_OTHER", "B", "metadata", {
        "allowed_for_origination_pd": False,
        "allowed_for_behavioral_pd": False,
        "allowed_for_profit": False,
        "leakage_risk": "low",
        "reason_if_not_allowed_for_pd": "unclassified column",
    })


def make_catalog_row(
    name: str, feature_family: str, source_columns: str, formula: str,
    description: str, availability_time: str, source_window: str,
    uses_target: bool = False, uses_future_behavior: bool = False,
    allowed_for_origination_pd: bool = False,
    allowed_for_behavioral_pd: bool = False,
    allowed_for_profit: bool = False,
    leakage_risk: str = "medium",
    reason_if_not_allowed_for_pd: str = "",
) -> dict:
    return {
        "feature_name": name,
        "feature_family": feature_family,
        "source_columns": source_columns,
        "formula": formula,
        "description": description,
        "availability_time": availability_time,
        "source_window": source_window,
        "uses_target": uses_target,
        "uses_future_behavior": uses_future_behavior,
        "allowed_for_origination_pd": allowed_for_origination_pd,
        "allowed_for_behavioral_pd": allowed_for_behavioral_pd,
        "allowed_for_profit": allowed_for_profit,
        "leakage_risk": leakage_risk,
        "reason_if_not_allowed_for_pd": reason_if_not_allowed_for_pd,
    }


def classify_all_originals(df: pd.DataFrame) -> list[dict]:
    """Build catalog rows for ALL original ABT columns."""
    log("Classifying ALL original columns...")
    rows = []
    for col in df.columns:
        family, level, src_win, gov = classify_original(col)
        defaults = {
            "uses_target": False, "uses_future_behavior": False,
            "allowed_for_origination_pd": False,
            "allowed_for_behavioral_pd": False,
            "allowed_for_profit": False,
            "leakage_risk": "low",
            "reason_if_not_allowed_for_pd": "",
        }
        defaults.update(gov)
        avail = "metadata" if family in ("ORIGINAL_ID", "ORIGINAL_SPLIT", "ORIGINAL_OTHER") else (
            "post-origination" if family == "ORIGINAL_BEHAVIORAL" else "origination")
        rows.append(make_catalog_row(
            name=col, feature_family=family, source_columns=col,
            formula="raw column from cleaned ABT",
            description=f"original ABT column ({family})",
            availability_time=avail, source_window=src_win,
            **defaults,
        ))
    # quick summary
    fam_counts = pd.Series([r["feature_family"] for r in rows]).value_counts()
    for fam, n in fam_counts.items():
        log(f"  {fam:<30} {n}")
    return rows


def detect_behavioral_series(df: pd.DataFrame) -> dict[str, list[int]]:
    """Return {series_prefix: sorted_list_of_months}."""
    series: dict[str, list[int]] = {}
    for col in df.columns:
        m = BEHAVIORAL_RE.match(col)
        if not m:
            continue
        # Extract series prefix (everything before final "_m\d+")
        prefix = re.sub(r"_m\d+$", "", col)
        month = int(m.group(2))
        series.setdefault(prefix, []).append(month)
    for k in series:
        series[k] = sorted(series[k])
    return series


# =============================================================================
# Step C: feature generation
# =============================================================================

def f1_rolling(df: pd.DataFrame, series: dict[str, list[int]]) -> tuple[dict, list[dict]]:
    """Rolling window aggregations: mean/std/min/max/median/last per window."""
    log("Family F1: rolling window stats")
    out: dict[str, np.ndarray] = {}
    catalog: list[dict] = []

    stats_funcs = [
        ("mean",   np.nanmean),
        ("std",    lambda a, axis: np.nanstd(a, axis=axis, ddof=1)),
        ("min",    np.nanmin),
        ("max",    np.nanmax),
        ("median", np.nanmedian),
        ("last",   None),  # special: use last available column in window
    ]
    windows = [("3m", 3), ("6m", 6), ("9m", 9), ("12m", 12)]

    for prefix, months in series.items():
        # Determine source columns per window: months <= window_size and present
        cols_full = [f"{prefix}_m{m}" for m in months]
        # Cast to float32 for speed/memory
        arr_all = df[cols_full].to_numpy(dtype=np.float32)
        # Mapping month -> idx in cols_full
        month_to_idx = {m: i for i, m in enumerate(months)}

        for win_name, win_size in windows:
            in_window = [m for m in months if m <= win_size]
            if not in_window:
                continue
            idxs = [month_to_idx[m] for m in in_window]
            sub = arr_all[:, idxs]

            for stat_name, fn in stats_funcs:
                fname = f"{prefix}_{stat_name}_{win_name}"
                if stat_name == "last":
                    # last available month in window
                    arr = sub[:, -1]
                else:
                    with np.errstate(all="ignore"):
                        if stat_name == "std" and sub.shape[1] < 2:
                            arr = np.full(sub.shape[0], np.nan, dtype=np.float32)
                        else:
                            arr = fn(sub, axis=1)
                out[fname] = arr.astype(np.float32, copy=False)

                # Governance: 3m -> level F (medium risk, not orig PD);
                #             6/9/12m -> level C (high risk)
                if win_size <= 3:
                    cat = make_catalog_row(
                        name=fname, feature_family="F1",
                        source_columns=",".join(f"{prefix}_m{m}" for m in in_window),
                        formula=f"{stat_name}({prefix} over m{in_window[0]}-m{in_window[-1]})",
                        description=f"rolling {stat_name} of {prefix} over {win_name} window",
                        availability_time="post-origination",
                        source_window=f"m{in_window[0]}-m{in_window[-1]}",
                        uses_future_behavior=True,
                        allowed_for_origination_pd=False,
                        allowed_for_behavioral_pd=True,
                        allowed_for_profit=False,
                        leakage_risk="medium",
                        reason_if_not_allowed_for_pd=
                            "early behavioral aggregate (m1-m3)",
                    )
                else:
                    cat = make_catalog_row(
                        name=fname, feature_family="F1",
                        source_columns=",".join(f"{prefix}_m{m}" for m in in_window),
                        formula=f"{stat_name}({prefix} over m{in_window[0]}-m{in_window[-1]})",
                        description=f"rolling {stat_name} of {prefix} over {win_name} window",
                        availability_time="post-origination",
                        source_window=f"m{in_window[0]}-m{in_window[-1]}",
                        uses_future_behavior=True,
                        allowed_for_origination_pd=False,
                        allowed_for_behavioral_pd=False,
                        allowed_for_profit=False,
                        leakage_risk="high",
                        reason_if_not_allowed_for_pd=
                            f"late behavioral aggregate ({win_name})",
                    )
                catalog.append(cat)

        # endpoint features: first_value (m1 or earliest) + last_value (m12 or latest)
        first_m = months[0]
        last_m  = months[-1]
        first_name = f"{prefix}_first_value"
        last_name  = f"{prefix}_last_value"
        out[first_name] = arr_all[:, 0].astype(np.float32, copy=False)
        out[last_name]  = arr_all[:, -1].astype(np.float32, copy=False)
        # Governance: first_value uses earliest month -> if m<=3 level F, else C
        for endpoint_name, m_used in ((first_name, first_m), (last_name, last_m)):
            if m_used <= 3:
                catalog.append(make_catalog_row(
                    name=endpoint_name, feature_family="F1",
                    source_columns=f"{prefix}_m{m_used}",
                    formula=f"value of {prefix} at m{m_used}",
                    description=f"endpoint value of {prefix} at m{m_used}",
                    availability_time="post-origination",
                    source_window=f"m{m_used}",
                    uses_future_behavior=True,
                    allowed_for_origination_pd=False,
                    allowed_for_behavioral_pd=True,
                    allowed_for_profit=False,
                    leakage_risk="medium",
                    reason_if_not_allowed_for_pd="early behavioral endpoint",
                ))
            else:
                catalog.append(make_catalog_row(
                    name=endpoint_name, feature_family="F1",
                    source_columns=f"{prefix}_m{m_used}",
                    formula=f"value of {prefix} at m{m_used}",
                    description=f"endpoint value of {prefix} at m{m_used}",
                    availability_time="post-origination",
                    source_window=f"m{m_used}",
                    uses_future_behavior=True,
                    allowed_for_origination_pd=False,
                    allowed_for_behavioral_pd=False,
                    allowed_for_profit=False,
                    leakage_risk="high",
                    reason_if_not_allowed_for_pd="late behavioral endpoint",
                ))

    log(f"  F1 generated: {len(out)} features")
    return out, catalog


def f2_trends(df: pd.DataFrame, series: dict[str, list[int]]) -> tuple[dict, list[dict]]:
    """Linear trend slope/intercept/r2 per series per window."""
    log("Family F2: trend slope/intercept/r2")
    out: dict[str, np.ndarray] = {}
    catalog: list[dict] = []
    windows = [("3m", 3), ("6m", 6), ("12m", 12)]

    for prefix, months in series.items():
        cols_full = [f"{prefix}_m{m}" for m in months]
        arr_all = df[cols_full].to_numpy(dtype=np.float32)

        for win_name, win_size in windows:
            in_window = [m for m in months if m <= win_size]
            if len(in_window) < 2:
                continue
            idxs = [months.index(m) for m in in_window]
            sub = arr_all[:, idxs]
            x = np.array(in_window, dtype=np.float32)
            x_mean = x.mean()
            xc = x - x_mean

            # vectorized least-squares slope: cov(x,y)/var(x) per row
            with np.errstate(all="ignore"):
                y = sub
                y_mean = np.nanmean(y, axis=1)
                yc = y - y_mean[:, None]
                # Replace nan in xc product with 0 (treat NaN points as missing)
                num = np.nansum(xc[None, :] * yc, axis=1)
                den_x = np.nansum(xc * xc)
                den_x = den_x if den_x > 0 else np.nan
                slope = num / den_x
                intercept = y_mean - slope * x_mean
                # R^2: 1 - SS_res/SS_tot
                y_pred = intercept[:, None] + slope[:, None] * x[None, :]
                ss_res = np.nansum((y - y_pred) ** 2, axis=1)
                ss_tot = np.nansum(yc ** 2, axis=1)
                r2 = 1.0 - np.where(ss_tot > 0, ss_res / ss_tot, np.nan)

            slope_name     = f"{prefix}_slope_{win_name}"
            intercept_name = f"{prefix}_intercept_{win_name}"
            r2_name        = f"{prefix}_r2_{win_name}"
            out[slope_name]     = slope.astype(np.float32, copy=False)
            out[intercept_name] = intercept.astype(np.float32, copy=False)
            out[r2_name]        = r2.astype(np.float32, copy=False)

            # Governance
            if win_size <= 3:
                risk = "medium"
                allow_beh = True
                reason = "early-window trend (m1-m3)"
            else:
                risk = "high"
                allow_beh = False
                reason = f"late-window trend ({win_name})"
            for fname, metric in ((slope_name, "slope"),
                                  (intercept_name, "intercept"),
                                  (r2_name, "r2")):
                catalog.append(make_catalog_row(
                    name=fname, feature_family="F2",
                    source_columns=",".join(f"{prefix}_m{m}" for m in in_window),
                    formula=f"{metric}(linfit({prefix}, m{in_window[0]}-m{in_window[-1]}))",
                    description=f"linear trend {metric} of {prefix} over {win_name}",
                    availability_time="post-origination",
                    source_window=f"m{in_window[0]}-m{in_window[-1]}",
                    uses_future_behavior=True,
                    allowed_for_origination_pd=False,
                    allowed_for_behavioral_pd=allow_beh,
                    allowed_for_profit=False,
                    leakage_risk=risk,
                    reason_if_not_allowed_for_pd=reason,
                ))

    log(f"  F2 generated: {len(out)} features")
    return out, catalog


def _safe_div(num, den):
    """Element-wise division with NaN on div-by-zero."""
    den_safe = np.where(den == 0, np.nan, den)
    return (num / den_safe).astype(np.float32)


def f3_ratios(df: pd.DataFrame, aliases: dict) -> tuple[dict, list[dict]]:
    """Domain-meaningful ratios with source-inherit governance."""
    log("Family F3: ratios")
    out: dict[str, np.ndarray] = {}
    catalog: list[dict] = []
    age = aliases.get("age")
    loan = aliases.get("loan_amount")
    tenor = aliases.get("n_installments")
    inst = aliases.get("installment")

    def add(name, formula, source_cols, arr, level, family="F3",
            availability="origination", source_window="static",
            uses_future_behavior=False):
        out[name] = arr.astype(np.float32, copy=False)
        if level == "G":
            cat = dict(allowed_for_origination_pd=True, allowed_for_behavioral_pd=True,
                       allowed_for_profit=False, leakage_risk="low",
                       reason_if_not_allowed_for_pd="")
        elif level == "E":
            cat = dict(allowed_for_origination_pd=False, allowed_for_behavioral_pd=False,
                       allowed_for_profit=True, leakage_risk="medium",
                       reason_if_not_allowed_for_pd="loan-term/duration component")
        elif level == "F":
            cat = dict(allowed_for_origination_pd=False, allowed_for_behavioral_pd=True,
                       allowed_for_profit=False, leakage_risk="medium",
                       reason_if_not_allowed_for_pd="early behavioral component")
        elif level == "D":
            cat = dict(allowed_for_origination_pd=False, allowed_for_behavioral_pd=False,
                       allowed_for_profit=False, leakage_risk="high",
                       reason_if_not_allowed_for_pd="aggregate behavioral target-proxy")
        else:  # C
            cat = dict(allowed_for_origination_pd=False, allowed_for_behavioral_pd=False,
                       allowed_for_profit=False, leakage_risk="high",
                       reason_if_not_allowed_for_pd="late behavioral component")
        catalog.append(make_catalog_row(
            name=name, feature_family=family, source_columns=source_cols,
            formula=formula, description=formula,
            availability_time=availability, source_window=source_window,
            uses_target=False,
            uses_future_behavior=uses_future_behavior,
            **cat,
        ))

    # App-only (level G)
    if "app_income" in df.columns and "app_spendings" in df.columns:
        add("app_spendings_to_app_income",
            "app_spendings / app_income",
            "app_spendings,app_income",
            _safe_div(df["app_spendings"].to_numpy(np.float32),
                      df["app_income"].to_numpy(np.float32)),
            level="G")
    if age and "app_number_of_children" in df.columns:
        add("app_number_of_children_to_age",
            f"app_number_of_children / {age}",
            f"app_number_of_children,{age}",
            _safe_div(df["app_number_of_children"].to_numpy(np.float32),
                      df[age].to_numpy(np.float32)),
            level="G")
    if "app_income" in df.columns:
        v = df["app_income"].to_numpy(np.float32)
        add("log_app_income", "log1p(app_income)", "app_income",
            np.log1p(np.where(v > 0, v, 0)), level="G")
    if age:
        v = df[age].to_numpy(np.float32)
        add("log_age", f"log1p({age})", age,
            np.log1p(np.where(v > 0, v, 0)), level="G")

    # App + loan-term (level E)
    if loan and "app_income" in df.columns:
        add("loan_amount_to_income",
            f"{loan} / app_income",
            f"{loan},app_income",
            _safe_div(df[loan].to_numpy(np.float32),
                      df["app_income"].to_numpy(np.float32)),
            level="E")
    if inst and "app_income" in df.columns:
        add("installment_to_income",
            f"{inst} / app_income",
            f"{inst},app_income",
            _safe_div(df[inst].to_numpy(np.float32),
                      df["app_income"].to_numpy(np.float32)),
            level="E")
    if loan and age:
        add("loan_amount_to_age",
            f"{loan} / {age}",
            f"{loan},{age}",
            _safe_div(df[loan].to_numpy(np.float32),
                      df[age].to_numpy(np.float32)),
            level="E")
    if tenor:
        add("tenor_in_years",
            f"{tenor} / 12",
            tenor,
            (df[tenor].to_numpy(np.float32) / 12.0),
            level="E")

    # Behavioral early + loan-term (level E by inheritance)
    if "act_due_m2" in df.columns and loan:
        add("act_due_m2_to_loan_amount",
            f"act_due_m2 / {loan}",
            f"act_due_m2,{loan}",
            _safe_div(df["act_due_m2"].to_numpy(np.float32),
                      df[loan].to_numpy(np.float32)),
            level="E", availability="post-origination",
            source_window="m2", uses_future_behavior=True)
    if "act_due_m2" in df.columns and inst:
        add("act_due_m2_to_installment",
            f"act_due_m2 / {inst}",
            f"act_due_m2,{inst}",
            _safe_div(df["act_due_m2"].to_numpy(np.float32),
                      df[inst].to_numpy(np.float32)),
            level="E", availability="post-origination",
            source_window="m2", uses_future_behavior=True)

    # Aggregate ratios (level D)
    if "max_due" in df.columns and loan:
        add("max_due_to_loan_amount",
            f"max_due / {loan}",
            f"max_due,{loan}",
            _safe_div(df["max_due"].to_numpy(np.float32),
                      df[loan].to_numpy(np.float32)),
            level="D", availability="post-origination",
            source_window="m1-m12", uses_future_behavior=True)
    if "months_ever_due" in df.columns:
        add("months_ever_due_div_12",
            "months_ever_due / 12",
            "months_ever_due",
            (df["months_ever_due"].to_numpy(np.float32) / 12.0),
            level="D", availability="post-origination",
            source_window="m1-m12", uses_future_behavior=True)

    # Apply percentile clipping to all ratio features
    for name, arr in out.items():
        finite = arr[np.isfinite(arr)]
        if finite.size > 100:
            lo, hi = np.percentile(finite, [1, 99])
            out[name] = np.clip(arr, lo, hi).astype(np.float32, copy=False)

    log(f"  F3 generated: {len(out)} features")
    return out, catalog


def f4_interactions(df: pd.DataFrame, aliases: dict) -> tuple[dict, list[dict]]:
    """Interaction features (products, polynomials)."""
    log("Family F4: interactions")
    out: dict[str, np.ndarray] = {}
    catalog: list[dict] = []
    age = aliases.get("age")
    loan = aliases.get("loan_amount")
    tenor = aliases.get("n_installments")

    def add_inter(name, formula, source_cols, arr, level):
        out[name] = arr.astype(np.float32, copy=False)
        if level == "G":
            cat = dict(allowed_for_origination_pd=True, allowed_for_behavioral_pd=True,
                       allowed_for_profit=False, leakage_risk="low",
                       reason_if_not_allowed_for_pd="")
        else:  # E
            cat = dict(allowed_for_origination_pd=False, allowed_for_behavioral_pd=False,
                       allowed_for_profit=True, leakage_risk="medium",
                       reason_if_not_allowed_for_pd="loan-term/duration component")
        catalog.append(make_catalog_row(
            name=name, feature_family="F4", source_columns=source_cols,
            formula=formula, description=formula,
            availability_time="origination", source_window="static",
            uses_target=False, uses_future_behavior=False, **cat,
        ))

    # App-only (level G)
    if age and "app_income" in df.columns:
        add_inter("age_x_income", f"{age} * app_income",
                  f"{age},app_income",
                  df[age].to_numpy(np.float32) * df["app_income"].to_numpy(np.float32),
                  level="G")
    if age:
        v = df[age].to_numpy(np.float32)
        add_inter("age_squared", f"{age}^2", age, v * v, level="G")
    if "app_income" in df.columns:
        v = df["app_income"].to_numpy(np.float32)
        add_inter("app_income_squared", "app_income^2", "app_income",
                  v * v, level="G")
    if age and "app_number_of_children" in df.columns:
        add_inter("age_x_n_children",
                  f"{age} * app_number_of_children",
                  f"{age},app_number_of_children",
                  df[age].to_numpy(np.float32) *
                  df["app_number_of_children"].to_numpy(np.float32),
                  level="G")
    if "app_nom_marital_status" in df.columns and "app_number_of_children" in df.columns:
        # label-encode marital status, multiply
        enc = pd.Categorical(df["app_nom_marital_status"]).codes.astype(np.float32)
        add_inter("marital_x_n_children",
                  "label_encode(app_nom_marital_status) * app_number_of_children",
                  "app_nom_marital_status,app_number_of_children",
                  enc * df["app_number_of_children"].to_numpy(np.float32),
                  level="G")
    if "app_nom_job_code" in df.columns and "app_income" in df.columns:
        enc = pd.Categorical(df["app_nom_job_code"]).codes.astype(np.float32)
        add_inter("job_code_x_income",
                  "label_encode(app_nom_job_code) * app_income",
                  "app_nom_job_code,app_income",
                  enc * df["app_income"].to_numpy(np.float32),
                  level="G")

    # App + loan-term (level E)
    if loan and tenor:
        add_inter("loan_amount_x_tenor",
                  f"{loan} * {tenor}",
                  f"{loan},{tenor}",
                  df[loan].to_numpy(np.float32) * df[tenor].to_numpy(np.float32),
                  level="E")
    if age and loan:
        add_inter("age_x_loan_amount",
                  f"{age} * {loan}",
                  f"{age},{loan}",
                  df[age].to_numpy(np.float32) * df[loan].to_numpy(np.float32),
                  level="E")
    if loan and "app_income" in df.columns:
        v_loan = df[loan].to_numpy(np.float32)
        v_inc  = df["app_income"].to_numpy(np.float32)
        add_inter("loan_amount_x_income",
                  f"{loan} * app_income",
                  f"{loan},app_income",
                  v_loan * v_inc,
                  level="E")

    log(f"  F4 generated: {len(out)} features")
    return out, catalog


def f5a_app_group_stats(df: pd.DataFrame, split_col: Optional[str]) -> tuple[dict, list[dict], dict]:
    """App-only train-only group statistics with global-train fallback."""
    log("Family F5A: app-only group stats (train-only mappings)")
    out: dict[str, np.ndarray] = {}
    catalog: list[dict] = []
    fb: dict = {}
    if split_col is None or split_col not in df.columns:
        log("  WARN: no split column; SKIPPING F5A entirely")
        return out, catalog, fb

    train_mask = df[split_col] == "train"
    train = df.loc[train_mask]
    log(f"  train rows: {train_mask.sum():,}, oot rows: {(~train_mask).sum():,}")

    # Specs: (group_col, value_col, agg, name)
    specs = [
        # core mean income/age/spendings by various keys
        ("app_nom_job_code",        "app_income",   "mean",  "mean_income_by_job_code"),
        ("app_nom_branch",          "app_income",   "mean",  "mean_income_by_branch"),
        ("app_nom_city",            "app_income",   "mean",  "mean_income_by_city"),
        ("app_nom_marital_status",  "app_income",   "mean",  "mean_income_by_marital_status"),
        ("app_nom_home_status",     "app_income",   "mean",  "mean_income_by_home_status"),
        ("app_nom_gender",          "app_income",   "mean",  "mean_income_by_gender"),
        ("app_nom_marital_status",  "act_age",      "mean",  "mean_age_by_marital_status"),
        ("app_nom_city",            "act_age",      "mean",  "mean_age_by_city"),
        ("app_nom_job_code",        "act_age",      "mean",  "mean_age_by_job_code"),
        ("app_nom_home_status",     "act_age",      "mean",  "mean_age_by_home_status"),
        ("app_nom_gender",          "act_age",      "mean",  "mean_age_by_gender"),
        ("app_nom_branch",          "act_age",      "mean",  "mean_age_by_branch"),
        ("app_nom_home_status",     "app_spendings", "mean", "mean_spendings_by_home_status"),
        ("app_nom_branch",          "app_spendings", "mean", "mean_spendings_by_branch"),
        ("app_nom_city",            "app_spendings", "mean", "mean_spendings_by_city"),
        ("app_nom_job_code",        "app_spendings", "mean", "mean_spendings_by_job_code"),
        # std (dispersion)
        ("app_nom_job_code",        "app_income",   "std",   "std_income_by_job_code"),
        ("app_nom_branch",          "app_income",   "std",   "std_income_by_branch"),
        ("app_nom_city",            "app_income",   "std",   "std_income_by_city"),
        ("app_nom_marital_status",  "app_income",   "std",   "std_income_by_marital_status"),
        ("app_nom_branch",          "act_age",      "std",   "std_age_by_branch"),
        ("app_nom_job_code",        "act_age",      "std",   "std_age_by_job_code"),
        # median
        ("app_nom_job_code",        "app_income",   "median","median_income_by_job_code"),
        ("app_nom_branch",          "app_income",   "median","median_income_by_branch"),
        ("app_nom_city",            "app_income",   "median","median_income_by_city"),
        ("app_nom_branch",          "act_age",      "median","median_age_by_branch"),
        # counts (segment size)
        ("app_nom_job_code",        None,           "count", "count_by_job_code"),
        ("app_nom_branch",          None,           "count", "count_by_branch"),
        ("app_nom_city",            None,           "count", "count_by_city"),
        ("app_nom_marital_status",  None,           "count", "count_by_marital_status"),
        ("app_nom_home_status",     None,           "count", "count_by_home_status"),
        ("app_nom_gender",          None,           "count", "count_by_gender"),
        # children-by-segment (mean)
        ("app_nom_marital_status",  "app_number_of_children", "mean",
         "mean_n_children_by_marital_status"),
        ("app_nom_home_status",     "app_number_of_children", "mean",
         "mean_n_children_by_home_status"),
        ("app_nom_job_code",        "app_number_of_children", "mean",
         "mean_n_children_by_job_code"),
        # cars by segment
        ("app_nom_job_code",        "app_nom_cars", "mean", "mean_cars_by_job_code"),
        ("app_nom_branch",          "app_nom_cars", "mean", "mean_cars_by_branch"),
    ]

    for group_col, value_col, agg, fname in specs:
        if group_col not in df.columns:
            continue
        if value_col is not None and value_col not in df.columns:
            continue
        # Compute mapping on train
        if agg == "count":
            mapping = train.groupby(group_col, dropna=False).size()
            global_stat = float(len(train))  # fallback: total train rows
        else:
            grp = train.groupby(group_col, dropna=False)[value_col]
            mapping = getattr(grp, agg)()
            global_stat = float(getattr(train[value_col], agg)())
        # Apply: map all rows, fill unseen groups with global train statistic
        mapped = df[group_col].map(mapping).astype(np.float32)
        # Track fallback rate on OOT subset
        oot_unseen = mapped[~train_mask].isna().sum()
        oot_total  = (~train_mask).sum()
        fb[fname] = {
            "oot_unseen_groups": int(oot_unseen),
            "oot_total":         int(oot_total),
            "fallback_rate":     float(oot_unseen / max(oot_total, 1)),
        }
        mapped = mapped.fillna(global_stat).to_numpy(dtype=np.float32)
        out[fname] = mapped
        # catalog
        src_cols = group_col if value_col is None else f"{group_col},{value_col}"
        catalog.append(make_catalog_row(
            name=fname, feature_family="F5A", source_columns=src_cols,
            formula=f"{agg}({value_col or '1'} grouped by {group_col}) "
                    f"[train-only mapping; OOT unseen -> global train {agg}]",
            description=f"train-only group stat: {agg} of "
                        f"{value_col or 'count'} by {group_col}",
            availability_time="origination", source_window="static",
            uses_target=False, uses_future_behavior=False,
            allowed_for_origination_pd=True,
            allowed_for_behavioral_pd=True,
            allowed_for_profit=False,
            leakage_risk="low",
            reason_if_not_allowed_for_pd="",
        ))

    log(f"  F5A generated: {len(out)} features")
    return out, catalog, fb


def f5b_loanterm_group_stats(df: pd.DataFrame, split_col: Optional[str], aliases: dict) -> tuple[dict, list[dict]]:
    """Loan-term group statistics; level E inheritance -> not for PD."""
    log("Family F5B: loan-term group stats")
    out: dict[str, np.ndarray] = {}
    catalog: list[dict] = []
    if split_col is None or split_col not in df.columns:
        return out, catalog
    train_mask = df[split_col] == "train"
    train = df.loc[train_mask]
    loan = aliases.get("loan_amount")
    tenor = aliases.get("n_installments")
    inst = aliases.get("installment")

    specs: list[tuple[str, str, str, str]] = []
    for grp_col in ("app_nom_branch", "app_nom_job_code", "app_nom_city"):
        if grp_col in df.columns:
            if loan:
                specs += [
                    (grp_col, loan, "mean",   f"mean_{loan}_by_{grp_col}"),
                    (grp_col, loan, "median", f"median_{loan}_by_{grp_col}"),
                    (grp_col, loan, "std",    f"std_{loan}_by_{grp_col}"),
                ]
            if tenor:
                specs += [
                    (grp_col, tenor, "mean", f"mean_{tenor}_by_{grp_col}"),
                ]
            if inst:
                specs += [
                    (grp_col, inst, "median", f"median_{inst}_by_{grp_col}"),
                ]

    for group_col, value_col, agg, fname in specs:
        if value_col not in df.columns:
            continue
        grp = train.groupby(group_col, dropna=False)[value_col]
        mapping = getattr(grp, agg)()
        global_stat = float(getattr(train[value_col], agg)())
        mapped = df[group_col].map(mapping).astype(np.float32)
        mapped = mapped.fillna(global_stat).to_numpy(dtype=np.float32)
        out[fname] = mapped
        catalog.append(make_catalog_row(
            name=fname, feature_family="F5B",
            source_columns=f"{group_col},{value_col}",
            formula=f"{agg}({value_col} grouped by {group_col}) [train-only]",
            description=f"loan-term group stat (level E inheritance)",
            availability_time="origination", source_window="static",
            uses_target=False, uses_future_behavior=False,
            allowed_for_origination_pd=False,
            allowed_for_behavioral_pd=False,
            allowed_for_profit=True,
            leakage_risk="medium",
            reason_if_not_allowed_for_pd=
                "loan-term/duration artifact aggregated at segment level",
        ))

    log(f"  F5B generated: {len(out)} features")
    return out, catalog


def _level_for_source(col: str) -> str:
    """Return level letter for a single source column."""
    fam, lvl, _, _ = classify_original(col)
    return lvl


def f6a_rank_pct(df: pd.DataFrame, numeric_orig: list[str]) -> tuple[dict, list[dict]]:
    """Rank/percentile/zscore/log1p/sqrt transforms for every numeric original."""
    log(f"Family F6A: rank/pct/zscore/log/sqrt transforms over {len(numeric_orig)} numeric originals")
    out: dict[str, np.ndarray] = {}
    catalog: list[dict] = []
    n = len(df)

    for col in numeric_orig:
        v = df[col].to_numpy(np.float64)  # use float64 for rank precision
        lvl = _level_for_source(col)
        # 1) rank (0..N-1)
        rank = pd.Series(v).rank(method="average", na_option="keep").to_numpy(np.float32)
        # 2) percentile (0..1)
        pct = (rank - 1.0) / max(n - 1, 1)
        pct = pct.astype(np.float32)
        # 3) zscore
        with np.errstate(all="ignore"):
            mu = np.nanmean(v)
            sd = np.nanstd(v, ddof=1)
            z = ((v - mu) / sd).astype(np.float32) if sd > 0 else np.full(n, 0.0, dtype=np.float32)
        # 4) log1p (only for non-negative values; clip negatives to 0)
        log1p_v = np.log1p(np.where(v >= 0, v, 0)).astype(np.float32)
        # 5) sqrt (only for non-negative values)
        sqrt_v = np.sqrt(np.where(v >= 0, v, 0)).astype(np.float32)

        transforms = [
            ("rank",  rank,    "rank"),
            ("pct",   pct,     "percentile"),
            ("z",     z,       "zscore"),
            ("log1p", log1p_v, "log1p"),
            ("sqrt",  sqrt_v,  "sqrt"),
        ]
        for suffix, arr, formula_name in transforms:
            fname = f"{col}_{suffix}"
            out[fname] = arr
            cat_kwargs = _gov_for_level(lvl, col, "F6A", formula_name)
            catalog.append(make_catalog_row(
                name=fname, feature_family="F6A",
                source_columns=col,
                formula=f"{formula_name}({col})",
                description=f"{formula_name} transform of {col} (level {lvl})",
                **cat_kwargs,
            ))

    log(f"  F6A generated: {len(out)} features")
    return out, catalog


def _gov_for_level(level: str, source_col: str, family: str, op: str) -> dict:
    """Build governance dict from inherited level."""
    # Determine availability + source_window from source classification
    fam, lvl, src_win, gov = classify_original(source_col)
    avail = "metadata" if fam in ("ORIGINAL_ID", "ORIGINAL_SPLIT", "ORIGINAL_OTHER") else (
        "post-origination" if fam == "ORIGINAL_BEHAVIORAL" else "origination")
    uft = bool(gov.get("uses_future_behavior", False))
    uses_target = bool(gov.get("uses_target", False))

    if level == "A":
        return dict(availability_time=avail, source_window=src_win,
                    uses_target=True, uses_future_behavior=uft,
                    allowed_for_origination_pd=False, allowed_for_behavioral_pd=False,
                    allowed_for_profit=False, leakage_risk="high",
                    reason_if_not_allowed_for_pd="target/outcome derivative")
    if level == "B":
        return dict(availability_time="metadata", source_window="metadata",
                    uses_target=uses_target, uses_future_behavior=uft,
                    allowed_for_origination_pd=False, allowed_for_behavioral_pd=False,
                    allowed_for_profit=False, leakage_risk="low",
                    reason_if_not_allowed_for_pd="ID/metadata source")
    if level == "C":
        return dict(availability_time="post-origination", source_window=src_win,
                    uses_target=False, uses_future_behavior=True,
                    allowed_for_origination_pd=False, allowed_for_behavioral_pd=False,
                    allowed_for_profit=False, leakage_risk="high",
                    reason_if_not_allowed_for_pd="late behavioral source (m4-m12)")
    if level == "D":
        return dict(availability_time="post-origination", source_window=src_win,
                    uses_target=False, uses_future_behavior=True,
                    allowed_for_origination_pd=False, allowed_for_behavioral_pd=False,
                    allowed_for_profit=False, leakage_risk="high",
                    reason_if_not_allowed_for_pd="aggregate behavioral target-proxy")
    if level == "E":
        return dict(availability_time="origination", source_window="static",
                    uses_target=False, uses_future_behavior=False,
                    allowed_for_origination_pd=False, allowed_for_behavioral_pd=False,
                    allowed_for_profit=True, leakage_risk="medium",
                    reason_if_not_allowed_for_pd=
                        "loan-term/duration/zero-int artifact transform")
    if level == "F":
        return dict(availability_time="post-origination", source_window=src_win,
                    uses_target=False, uses_future_behavior=True,
                    allowed_for_origination_pd=False, allowed_for_behavioral_pd=True,
                    allowed_for_profit=False, leakage_risk="medium",
                    reason_if_not_allowed_for_pd="early behavioral source (m1-m3)")
    if level == "G":
        return dict(availability_time="origination", source_window="static",
                    uses_target=False, uses_future_behavior=False,
                    allowed_for_origination_pd=True, allowed_for_behavioral_pd=True,
                    allowed_for_profit=False, leakage_risk="low",
                    reason_if_not_allowed_for_pd="")
    # H
    return dict(availability_time="origination", source_window="random",
                uses_target=False, uses_future_behavior=False,
                allowed_for_origination_pd=True, allowed_for_behavioral_pd=True,
                allowed_for_profit=False, leakage_risk="low",
                reason_if_not_allowed_for_pd="")


def f6b_bins(df: pd.DataFrame, aliases: dict) -> tuple[dict, list[dict]]:
    """One-hot decile/quartile bin indicators for selected variables."""
    log("Family F6B: one-hot bin indicators")
    out: dict[str, np.ndarray] = {}
    catalog: list[dict] = []

    # Variable -> bin spec list of (n_bins, suffix_label)
    safe_app_numeric = []
    for c in ("act_age", "app_age", "app_income", "app_spendings",
              "app_number_of_children", "app_nom_cars"):
        if c in df.columns and c not in CATEGORICAL_SAFE:
            # check numeric
            if pd.api.types.is_numeric_dtype(df[c]):
                safe_app_numeric.append(c)
    loan = aliases.get("loan_amount")
    tenor = aliases.get("n_installments")
    inst = aliases.get("installment")

    # Top-N important behavioral vars for binning (level F + C; first 18)
    behav_to_bin = []
    candidates = [
        "act_due_m2", "act_due_m3", "act_paid_installments_m2",
        "act_paid_installments_m3", "act_utl_m2", "act_utl_m3",
        "act_dueutl_m2", "act_dueutl_m3", "act_cc_m1", "act_cc_m2",
        "act_dueinc_m2", "act_dueinc_m3", "coll_status_m2",
        "coll_status_m3", "act_loaninc_m1", "act_cus_utl_m1",
        "act_cus_cc_m1", "max_due",
    ]
    for c in candidates:
        if c in df.columns:
            behav_to_bin.append(c)

    targets: list[tuple[str, list[tuple[int, str]]]] = []
    for c in safe_app_numeric:
        targets.append((c, [(10, "decile"), (4, "quartile")]))
    for c in (loan, tenor, inst):
        if c is not None and c in df.columns:
            targets.append((c, [(10, "decile"), (4, "quartile")]))
    for c in behav_to_bin:
        targets.append((c, [(10, "decile")]))

    for col, specs in targets:
        v = df[col].to_numpy(np.float64)
        for n_bins, label in specs:
            try:
                bins = pd.qcut(v, n_bins, labels=False, duplicates="drop")
            except Exception:
                continue
            n_unique = pd.Series(bins).nunique()
            if n_unique < 2:
                continue
            # one-hot
            for b in range(n_unique):
                fname = f"{col}_{label}_{b+1}"
                arr = (bins == b).astype(np.float32)
                out[fname] = arr
                lvl = _level_for_source(col)
                cat_kwargs = _gov_for_level(lvl, col, "F6B", f"{label}_indicator")
                catalog.append(make_catalog_row(
                    name=fname, feature_family="F6B", source_columns=col,
                    formula=f"({col} in {label} bin {b+1} of {n_unique})",
                    description=f"{label} bin {b+1} indicator of {col}",
                    **cat_kwargs,
                ))

    log(f"  F6B generated: {len(out)} features")
    return out, catalog


def f6c_noisy(df: pd.DataFrame, numeric_orig: list[str], rng: np.random.Generator
              ) -> tuple[dict, list[dict]]:
    """Noisy copies: var + N(0, 0.1*std(var))."""
    log(f"Family F6C: noisy copies over {len(numeric_orig)} numeric originals")
    out: dict[str, np.ndarray] = {}
    catalog: list[dict] = []
    n = len(df)
    for col in numeric_orig:
        v = df[col].to_numpy(np.float32)
        sd = np.nanstd(v, ddof=1)
        if not np.isfinite(sd) or sd == 0:
            sd = 1.0
        noise = rng.normal(0, 0.1 * sd, size=n).astype(np.float32)
        fname = f"{col}_noisy"
        out[fname] = (v + noise).astype(np.float32)
        lvl = _level_for_source(col)
        cat_kwargs = _gov_for_level(lvl, col, "F6C", "noisy_copy")
        catalog.append(make_catalog_row(
            name=fname, feature_family="F6C", source_columns=col,
            formula=f"{col} + N(0, 0.1*std({col}))",
            description=f"noisy copy of {col}",
            **cat_kwargs,
        ))
    log(f"  F6C generated: {len(out)} features")
    return out, catalog


def f6d_random(df: pd.DataFrame, rng: np.random.Generator) -> tuple[dict, list[dict]]:
    """Pure random negative controls (level H)."""
    log("Family F6D: pure random negative controls")
    out: dict[str, np.ndarray] = {}
    catalog: list[dict] = []
    n = len(df)
    spec = [("uniform", 33, lambda: rng.uniform(0, 1, n).astype(np.float32)),
            ("normal",  34, lambda: rng.normal(0, 1, n).astype(np.float32)),
            ("int",     33, lambda: rng.integers(0, 100, n).astype(np.float32))]
    for label, count, fn in spec:
        for i in range(1, count + 1):
            fname = f"random_{label}_{i}"
            out[fname] = fn()
            catalog.append(make_catalog_row(
                name=fname, feature_family="F6D", source_columns="(none)",
                formula=f"{label} random draw, seed={SEED}",
                description="pure random negative control",
                availability_time="origination", source_window="random",
                uses_target=False, uses_future_behavior=False,
                allowed_for_origination_pd=True,
                allowed_for_behavioral_pd=True,
                allowed_for_profit=False,
                leakage_risk="low",
                reason_if_not_allowed_for_pd="",
            ))
    log(f"  F6D generated: {len(out)} features")
    return out, catalog


def f6e_synth_bureau(df: pd.DataFrame, aliases: dict, rng: np.random.Generator
                     ) -> tuple[dict, list[dict]]:
    """Synthetic bureau-like features from safe app vars + noise ONLY."""
    log("Family F6E: synthetic bureau-like (safe app vars + noise only)")
    out: dict[str, np.ndarray] = {}
    catalog: list[dict] = []
    n = len(df)
    age = aliases.get("age")
    inc = "app_income" if "app_income" in df.columns else None
    spend = "app_spendings" if "app_spendings" in df.columns else None
    nch = "app_number_of_children" if "app_number_of_children" in df.columns else None
    cars = "app_nom_cars" if "app_nom_cars" in df.columns else None

    # --- helpers ---
    def add_synth(name: str, arr: np.ndarray, sources: list[str], formula: str) -> None:
        # Verify no forbidden sources
        for s in sources:
            if s in df.columns:
                lvl = _level_for_source(s)
                if lvl in ("A", "C", "D", "E", "F"):
                    raise ValueError(
                        f"F6E violation: {name} uses forbidden source {s} (level {lvl})")
        out[name] = arr.astype(np.float32, copy=False)
        catalog.append(make_catalog_row(
            name=name, feature_family="F6E",
            source_columns=",".join(sources) if sources else "(noise only)",
            formula=formula,
            description="synthetic bureau-like, safe app + noise only, "
                        "not calibrated to target",
            availability_time="origination", source_window="static",
            uses_target=False, uses_future_behavior=False,
            allowed_for_origination_pd=True,
            allowed_for_behavioral_pd=True,
            allowed_for_profit=False,
            leakage_risk="low",
            reason_if_not_allowed_for_pd="",
        ))

    age_arr = df[age].to_numpy(np.float32) if age else np.zeros(n, np.float32)
    inc_arr = df[inc].to_numpy(np.float32) if inc else np.zeros(n, np.float32)
    spend_arr = df[spend].to_numpy(np.float32) if spend else np.zeros(n, np.float32)
    nch_arr = df[nch].to_numpy(np.float32) if nch else np.zeros(n, np.float32)
    cars_arr = df[cars].to_numpy(np.float32) if cars else np.zeros(n, np.float32)

    def cl(arr, lo, hi):
        return np.clip(arr, lo, hi).astype(np.float32)

    # --- 1. Credit score variants (10) ---
    for i, (a, b, c, sigma) in enumerate([
        (1e-4, 2.0, 0.0, 50),  (5e-5, 3.0, 0.0, 40),  (8e-5, 1.5, 0.0, 60),
        (1e-4, 0.0, -0.001, 55), (1.2e-4, 2.5, -0.0005, 45),
        (0.0, 4.0, 0.0, 80), (1e-4, 2.0, -0.0008, 30),
        (7e-5, 1.0, 0.0, 70), (9e-5, 2.5, -0.0003, 50),
        (1.1e-4, 1.8, 0.0, 35),
    ], start=1):
        noise = rng.normal(0, sigma, n).astype(np.float32)
        score = a * inc_arr + b * age_arr + c * spend_arr + 500 + noise
        add_synth(f"synth_credit_score_v{i}", cl(score, 300, 850),
                  [s for s in (inc, age, spend) if s],
                  f"clip({a}*income + {b}*age + {c}*spend + 500 + N(0,{sigma}), 300, 850)")

    # --- 2. Credit line counts (10) ---
    for i, (k, base) in enumerate([
        (5, 0), (10, 0), (8, 1), (4, 2), (12, 0),
        (6, 1), (7, 0), (9, 2), (3, 3), (15, 0),
    ], start=1):
        lam = np.maximum(0, (age_arr - 18) / k) + base
        arr = rng.poisson(lam).astype(np.float32)
        names = ["synth_n_credit_lines", "synth_n_active_lines", "synth_n_closed_lines",
                 "synth_n_revolving_lines", "synth_n_installment_lines",
                 "synth_n_mortgage_lines", "synth_n_auto_lines",
                 "synth_n_student_lines", "synth_n_card_lines",
                 "synth_n_lines_total"]
        add_synth(names[i-1], arr,
                  [age] if age else [],
                  f"Poisson(lambda=max(0, (age-18)/{k}) + {base})")

    # --- 3. Account age features (10) ---
    for i, (mult, sigma) in enumerate([
        (1.5, 5), (1.0, 8), (2.0, 6), (0.5, 10), (1.2, 7),
        (1.8, 4), (0.8, 9), (1.3, 6), (1.6, 5), (1.1, 8),
    ], start=1):
        lam = np.maximum(0, age_arr - 18) * mult
        arr = (rng.poisson(lam).astype(np.float32) +
               rng.normal(0, sigma, n).astype(np.float32))
        names = ["synth_oldest_account_months", "synth_avg_account_age_months",
                 "synth_newest_account_months", "synth_credit_history_years",
                 "synth_oldest_revolving_months", "synth_avg_revolving_age",
                 "synth_oldest_installment_months", "synth_oldest_mortgage_months",
                 "synth_avg_age_credit_lines", "synth_oldest_card_months"]
        add_synth(names[i-1], np.maximum(arr, 0),
                  [age] if age else [],
                  f"Poisson(max(0, age-18)*{mult}) + N(0,{sigma})")

    # --- 4. Inquiries (10): pure Poisson noise ---
    for i, lam in enumerate([0.5, 1.0, 1.5, 2.0, 0.3, 0.8, 1.2, 0.6, 1.0, 0.4], start=1):
        arr = rng.poisson(lam, n).astype(np.float32)
        names = ["synth_inquiries_3m", "synth_inquiries_6m", "synth_inquiries_12m",
                 "synth_inquiries_24m", "synth_hard_pulls_3m", "synth_hard_pulls_6m",
                 "synth_hard_pulls_12m", "synth_soft_pulls_3m",
                 "synth_soft_pulls_12m", "synth_disputes_24m"]
        add_synth(names[i-1], arr, [], f"Poisson(lambda={lam}) [pure noise]")

    # --- 5. Utilization (10): Beta + small income signal ---
    for i, (a, b) in enumerate([
        (2, 5), (3, 6), (1, 4), (2, 4), (4, 8),
        (2, 7), (3, 5), (1, 5), (2, 6), (3, 7),
    ], start=1):
        beta = rng.beta(a, b, n).astype(np.float32)
        small_inc = (inc_arr - inc_arr.mean()) / (inc_arr.std() + 1e-6) * 0.05
        arr = np.clip(beta + small_inc, 0, 1).astype(np.float32)
        names = ["synth_utilization_pct", "synth_revolving_util",
                 "synth_installment_util", "synth_high_balance_util",
                 "synth_avg_util", "synth_max_util", "synth_min_util",
                 "synth_util_revolving_3m", "synth_util_installment_3m",
                 "synth_util_overall_6m"]
        add_synth(names[i-1], arr, [inc] if inc else [],
                  f"clip(Beta({a},{b}) + 0.05*zscore(income), 0, 1)")

    # --- 6. Payment history (10): age + income normalized + noise ---
    for i, sigma in enumerate([5, 10, 8, 12, 6, 7, 9, 11, 4, 13], start=1):
        # base score 50, +up to 50 from age 25-65 maturity, noise
        age_signal = np.clip((age_arr - 25) / 40, 0, 1) * 30
        inc_signal = np.clip((inc_arr / max(inc_arr.max(), 1)), 0, 1) * 20
        score = 50 + age_signal + inc_signal + rng.normal(0, sigma, n).astype(np.float32)
        score = np.clip(score, 0, 100).astype(np.float32)
        names = ["synth_payment_history_score", "synth_months_since_late",
                 "synth_pct_on_time", "synth_n_late_30", "synth_n_late_60",
                 "synth_n_late_90", "synth_avg_days_late",
                 "synth_max_days_late", "synth_n_missed_payments",
                 "synth_pmt_consistency_score"]
        add_synth(names[i-1], score, [s for s in (age, inc) if s],
                  f"clip(50 + 30*age_norm + 20*inc_norm + N(0,{sigma}), 0, 100)")

    # --- 7. Derogatory (10): low-rate Poisson ---
    for i, lam in enumerate([0.1, 0.3, 0.5, 0.05, 0.2, 0.15, 0.4, 0.08, 0.25, 0.12], start=1):
        arr = rng.poisson(lam, n).astype(np.float32)
        names = ["synth_derogatory_marks", "synth_collections_count",
                 "synth_charge_offs", "synth_bankruptcies",
                 "synth_public_records", "synth_tax_liens",
                 "synth_judgments", "synth_foreclosures",
                 "synth_repossessions", "synth_settlements"]
        add_synth(names[i-1], arr, [], f"Poisson(lambda={lam}) [pure noise]")

    # --- 8. Balances (10): income * Beta ---
    for i, (a, b) in enumerate([
        (2, 5), (1, 6), (3, 4), (2, 7), (4, 5),
        (1, 4), (2, 6), (3, 5), (1, 8), (2, 4),
    ], start=1):
        bal = inc_arr * rng.beta(a, b, n).astype(np.float32)
        names = ["synth_total_balance", "synth_revolving_balance",
                 "synth_installment_balance", "synth_avg_balance_6m",
                 "synth_total_debt", "synth_credit_card_balance",
                 "synth_auto_loan_balance", "synth_mortgage_balance",
                 "synth_student_loan_balance", "synth_other_balance"]
        add_synth(names[i-1], bal, [inc] if inc else [],
                  f"income * Beta({a},{b})")

    # --- 9. Limits (10): income * LogNormal ---
    for i, sigma in enumerate([0.3, 0.5, 0.4, 0.6, 0.2, 0.7, 0.5, 0.4, 0.3, 0.6], start=1):
        ln = rng.lognormal(0, sigma, n).astype(np.float32)
        lim = inc_arr * ln
        names = ["synth_total_limit", "synth_revolving_limit",
                 "synth_available_credit", "synth_avg_limit",
                 "synth_highest_limit", "synth_lowest_limit",
                 "synth_revolving_avail", "synth_card_limit",
                 "synth_secured_limit", "synth_unsecured_limit"]
        add_synth(names[i-1], lim, [inc] if inc else [],
                  f"income * LogNormal(0, {sigma})")

    # --- 10. Bureau ratios (10): combinations of synth balance/limits ---
    bal_arr = out["synth_total_balance"]
    lim_arr = out["synth_total_limit"]
    rev_bal = out["synth_revolving_balance"]
    rev_lim = out["synth_revolving_limit"]
    add_synth("synth_util_to_limit", _safe_div(bal_arr, lim_arr),
              ["synth_total_balance", "synth_total_limit"],
              "synth_total_balance / synth_total_limit")
    add_synth("synth_revolving_util_ratio", _safe_div(rev_bal, rev_lim),
              ["synth_revolving_balance", "synth_revolving_limit"],
              "synth_revolving_balance / synth_revolving_limit")
    if inc:
        add_synth("synth_balance_to_income_ratio", _safe_div(bal_arr, inc_arr),
                  ["synth_total_balance", inc],
                  f"synth_total_balance / {inc}")
        add_synth("synth_debt_to_income_synth", _safe_div(bal_arr, inc_arr),
                  ["synth_total_balance", inc],
                  f"synth_total_balance / {inc} (DTI proxy)")
        add_synth("synth_payment_to_income", _safe_div(bal_arr * 0.03, inc_arr),
                  ["synth_total_balance", inc],
                  f"(synth_total_balance * 0.03) / {inc}")
        add_synth("synth_avail_credit_pct", _safe_div(lim_arr - bal_arr, lim_arr),
                  ["synth_total_limit", "synth_total_balance"],
                  "(synth_total_limit - synth_total_balance) / synth_total_limit")
        add_synth("synth_revolving_to_total_ratio", _safe_div(rev_bal, bal_arr),
                  ["synth_revolving_balance", "synth_total_balance"],
                  "synth_revolving_balance / synth_total_balance")
        add_synth("synth_lim_to_income", _safe_div(lim_arr, inc_arr),
                  ["synth_total_limit", inc],
                  f"synth_total_limit / {inc}")
        add_synth("synth_avail_to_income",
                  _safe_div(lim_arr - bal_arr, inc_arr),
                  ["synth_total_limit", "synth_total_balance", inc],
                  f"(synth_total_limit - synth_total_balance) / {inc}")
        add_synth("synth_n_lines_x_util",
                  out["synth_n_credit_lines"] * out["synth_utilization_pct"],
                  ["synth_n_credit_lines", "synth_utilization_pct"],
                  "synth_n_credit_lines * synth_utilization_pct")

    # --- 11. Age proxies (10) ---
    for i, sigma in enumerate([2, 5, 1, 8, 3, 4, 6, 7, 1.5, 9], start=1):
        if age:
            arr = age_arr + rng.normal(0, sigma, n).astype(np.float32)
        else:
            arr = rng.normal(35, sigma, n).astype(np.float32)
        names = ["synth_credit_age_v1", "synth_credit_age_v2",
                 "synth_thin_file_flag", "synth_oldest_tradeline_v1",
                 "synth_age_of_oldest", "synth_age_of_newest",
                 "synth_avg_account_age", "synth_credit_age_years",
                 "synth_credit_history_v1", "synth_age_proxy_v3"]
        add_synth(names[i-1], arr, [age] if age else [],
                  f"age + N(0,{sigma}) (or N(35,{sigma}) if no age)")

    # --- 12. Income proxies (10) ---
    for i, sigma in enumerate([0.05, 0.10, 0.15, 0.08, 0.12, 0.20, 0.06, 0.18, 0.09, 0.14], start=1):
        if inc:
            arr = inc_arr * (1 + rng.normal(0, sigma, n).astype(np.float32))
        else:
            arr = rng.lognormal(8, sigma, n).astype(np.float32)
        names = ["synth_monthly_obligations", "synth_disposable_income",
                 "synth_income_stability_score", "synth_employment_months",
                 "synth_self_reported_income", "synth_verified_income",
                 "synth_gross_income_v1", "synth_net_income_v1",
                 "synth_total_income_v1", "synth_household_income_v1"]
        add_synth(names[i-1], arr, [inc] if inc else [],
                  f"income * (1 + N(0,{sigma}))")

    # --- 13. Segments (20): binary indicators from categorical & app vars ---
    seg_count = 0
    cat_keys = [k for k in ("app_nom_branch", "app_nom_marital_status",
                             "app_nom_home_status", "app_nom_gender",
                             "app_nom_job_code", "app_nom_city")
                if k in df.columns]
    for cat in cat_keys[:6]:
        codes = pd.Categorical(df[cat]).codes.astype(np.int64)
        # top-3 most common levels per categorical -> 3 indicators each
        uniq, counts = np.unique(codes, return_counts=True)
        top = uniq[np.argsort(counts)[::-1][:3]]
        for j, t in enumerate(top, start=1):
            if seg_count >= 14:
                break
            arr = (codes == t).astype(np.float32)
            fname = f"synth_seg_{cat}_top{j}"
            add_synth(fname, arr, [cat], f"({cat} == top_level_{j}).astype(int)")
            seg_count += 1
        if seg_count >= 14:
            break
    # 6 more segment flags from binary thresholds on app numeric vars
    if inc and seg_count < 20:
        median_inc = np.nanmedian(inc_arr)
        add_synth("synth_seg_high_income_flag",
                  (inc_arr > median_inc).astype(np.float32),
                  [inc], f"(income > median(income)).astype(int)")
        seg_count += 1
    if age and seg_count < 20:
        add_synth("synth_seg_prime_age_30_50",
                  ((age_arr >= 30) & (age_arr <= 50)).astype(np.float32),
                  [age], "(age in [30,50]).astype(int)")
        seg_count += 1
    if age and seg_count < 20:
        add_synth("synth_seg_senior_flag",
                  (age_arr >= 60).astype(np.float32),
                  [age], "(age >= 60).astype(int)")
        seg_count += 1
    if spend and seg_count < 20:
        med_sp = np.nanmedian(spend_arr)
        add_synth("synth_seg_high_spending_flag",
                  (spend_arr > med_sp).astype(np.float32),
                  [spend], "(spendings > median(spendings)).astype(int)")
        seg_count += 1
    if nch and seg_count < 20:
        add_synth("synth_seg_has_children",
                  (nch_arr > 0).astype(np.float32),
                  [nch], "(n_children > 0).astype(int)")
        seg_count += 1
    if cars and seg_count < 20:
        add_synth("synth_seg_has_cars",
                  (cars_arr > 0).astype(np.float32),
                  [cars], "(n_cars > 0).astype(int)")
        seg_count += 1
    # pad with Bernoulli flags if still under 20
    while seg_count < 20:
        p = float(rng.uniform(0.2, 0.8))
        fname = f"synth_seg_bernoulli_{seg_count+1}"
        add_synth(fname, rng.binomial(1, p, n).astype(np.float32),
                  [], f"Bernoulli(p={p:.3f}) [pure noise]")
        seg_count += 1

    # --- 14. Interactions (20): products of safe app numerics & internal F6E ---
    interactions = []
    if age and inc:
        interactions.append(("synth_int_age_x_income", age_arr * inc_arr,
                             [age, inc], f"{age} * {inc}"))
    if age and spend:
        interactions.append(("synth_int_age_x_spend", age_arr * spend_arr,
                             [age, spend], f"{age} * {spend}"))
    if age and nch:
        interactions.append(("synth_int_age_x_nchildren", age_arr * nch_arr,
                             [age, nch], f"{age} * {nch}"))
    if inc and spend:
        interactions.append(("synth_int_inc_x_spend", inc_arr * spend_arr,
                             [inc, spend], f"{inc} * {spend}"))
    if inc and nch:
        interactions.append(("synth_int_inc_x_nchildren", inc_arr * nch_arr,
                             [inc, nch], f"{inc} * {nch}"))
    if spend and nch:
        interactions.append(("synth_int_spend_x_nchildren", spend_arr * nch_arr,
                             [spend, nch], f"{spend} * {nch}"))
    # within-F6E products
    interactions += [
        ("synth_int_score_x_util",
         out["synth_credit_score_v1"] * out["synth_utilization_pct"],
         ["synth_credit_score_v1", "synth_utilization_pct"],
         "synth_credit_score_v1 * synth_utilization_pct"),
        ("synth_int_balance_x_score",
         out["synth_total_balance"] * out["synth_credit_score_v1"],
         ["synth_total_balance", "synth_credit_score_v1"],
         "synth_total_balance * synth_credit_score_v1"),
        ("synth_int_inquiries_x_age",
         out["synth_inquiries_12m"] * (age_arr if age else np.ones(n)),
         ["synth_inquiries_12m"] + ([age] if age else []),
         f"synth_inquiries_12m * {age or '1'}"),
        ("synth_int_lines_x_score",
         out["synth_n_credit_lines"] * out["synth_credit_score_v1"],
         ["synth_n_credit_lines", "synth_credit_score_v1"],
         "synth_n_credit_lines * synth_credit_score_v1"),
        ("synth_int_util_x_inquiries",
         out["synth_utilization_pct"] * out["synth_inquiries_12m"],
         ["synth_utilization_pct", "synth_inquiries_12m"],
         "synth_utilization_pct * synth_inquiries_12m"),
        ("synth_int_age_x_score",
         (age_arr if age else np.ones(n)) * out["synth_credit_score_v1"],
         ([age] if age else []) + ["synth_credit_score_v1"],
         f"{age or '1'} * synth_credit_score_v1"),
        ("synth_int_inc_x_score",
         (inc_arr if inc else np.ones(n)) * out["synth_credit_score_v1"],
         ([inc] if inc else []) + ["synth_credit_score_v1"],
         f"{inc or '1'} * synth_credit_score_v1"),
        ("synth_int_balance_x_util",
         out["synth_total_balance"] * out["synth_utilization_pct"],
         ["synth_total_balance", "synth_utilization_pct"],
         "synth_total_balance * synth_utilization_pct"),
        ("synth_int_lim_x_util",
         out["synth_total_limit"] * out["synth_utilization_pct"],
         ["synth_total_limit", "synth_utilization_pct"],
         "synth_total_limit * synth_utilization_pct"),
        ("synth_int_n_lines_x_inquiries",
         out["synth_n_credit_lines"] * out["synth_inquiries_12m"],
         ["synth_n_credit_lines", "synth_inquiries_12m"],
         "synth_n_credit_lines * synth_inquiries_12m"),
        ("synth_int_oldest_x_score",
         out["synth_oldest_account_months"] * out["synth_credit_score_v1"],
         ["synth_oldest_account_months", "synth_credit_score_v1"],
         "synth_oldest_account_months * synth_credit_score_v1"),
        ("synth_int_pmt_hist_x_util",
         out["synth_payment_history_score"] * out["synth_utilization_pct"],
         ["synth_payment_history_score", "synth_utilization_pct"],
         "synth_payment_history_score * synth_utilization_pct"),
        ("synth_int_derog_x_score",
         out["synth_derogatory_marks"] * out["synth_credit_score_v1"],
         ["synth_derogatory_marks", "synth_credit_score_v1"],
         "synth_derogatory_marks * synth_credit_score_v1"),
        ("synth_int_dti_x_score",
         out["synth_debt_to_income_synth"] * out["synth_credit_score_v1"]
         if "synth_debt_to_income_synth" in out else
         out["synth_total_balance"] * out["synth_credit_score_v1"],
         ["synth_debt_to_income_synth", "synth_credit_score_v1"]
         if "synth_debt_to_income_synth" in out else
         ["synth_total_balance", "synth_credit_score_v1"],
         "DTI * synth_credit_score_v1"),
    ]
    for name, arr, sources, formula in interactions[:20]:
        if name not in out:
            add_synth(name, arr, sources, formula)

    # --- 15. Pure noise (40 features) ---
    for i in range(1, 11):
        add_synth(f"synth_noise_normal_{i}", rng.normal(0, 1, n).astype(np.float32),
                  [], "N(0,1) [pure noise]")
    for i in range(1, 11):
        add_synth(f"synth_noise_uniform_{i}", rng.uniform(0, 1, n).astype(np.float32),
                  [], "Uniform(0,1) [pure noise]")
    for i in range(1, 11):
        a, b = 2 + (i % 4), 4 + (i % 5)
        add_synth(f"synth_noise_beta_{i}", rng.beta(a, b, n).astype(np.float32),
                  [], f"Beta({a},{b}) [pure noise]")
    for i in range(1, 11):
        lam = 0.5 + (i * 0.3)
        add_synth(f"synth_noise_poisson_{i}", rng.poisson(lam, n).astype(np.float32),
                  [], f"Poisson({lam:.2f}) [pure noise]")

    log(f"  F6E generated: {len(out)} features")
    return out, catalog


# =============================================================================
# Step D: Validate
# =============================================================================

def validate_outputs(df_full: pd.DataFrame, catalog_df: pd.DataFrame, n_orig_rows: int) -> dict:
    log("Validating outputs...")
    checks = {}
    # 1. Row count unchanged
    checks["row_count_unchanged"] = (len(df_full) == n_orig_rows)
    log(f"  rows: {len(df_full):,} (expected {n_orig_rows:,}) -> "
        f"{'PASS' if checks['row_count_unchanged'] else 'FAIL'}")
    # 2. No infinities
    n_inf = int(np.isinf(df_full.select_dtypes(include="number").to_numpy()).sum())
    checks["no_infinities"] = (n_inf == 0)
    log(f"  infinities: {n_inf} -> {'PASS' if n_inf == 0 else 'WARN'}")
    # 3. Catalog completeness
    cat_cols = set(catalog_df["feature_name"])
    df_cols = set(df_full.columns)
    missing_in_catalog = df_cols - cat_cols
    extra_in_catalog = cat_cols - df_cols
    checks["catalog_completeness"] = (not missing_in_catalog and not extra_in_catalog)
    log(f"  catalog rows: {len(catalog_df)}, df cols: {len(df_full.columns)}")
    if missing_in_catalog:
        log(f"  MISSING from catalog: {list(missing_in_catalog)[:5]}...")
    if extra_in_catalog:
        log(f"  EXTRA in catalog: {list(extra_in_catalog)[:5]}...")
    # 4. uses_target == 1 only for target column
    n_uses_target = int(catalog_df["uses_target"].sum())
    checks["uses_target_count"] = (n_uses_target == 1)
    log(f"  uses_target=true count: {n_uses_target} -> "
        f"{'PASS' if n_uses_target == 1 else 'WARN'}")
    return checks


# =============================================================================
# Step E: Save outputs
# =============================================================================

def try_save_parquet(df: pd.DataFrame, out_path: Path) -> tuple[bool, str]:
    try:
        df.to_parquet(out_path, compression="snappy", index=False)
        return True, "parquet (pyarrow/snappy)"
    except Exception as e:
        return False, f"parquet failed: {e}"


def save_csvgz(df: pd.DataFrame, out_path: Path) -> str:
    df.to_csv(out_path, compression="gzip", index=False)
    return "csv.gz"


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    rule()
    log("Phase 1.5 Feature Factory")
    rule()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Step A: Load + classify ----
    df = load_abt(INPUT_CSV)
    n_rows_orig = len(df)
    aliases = detect_aliases(set(df.columns))
    log(f"Schema aliases detected: {aliases}")
    drop_cols, dup_info = check_duplicate_columns(df)
    if drop_cols:
        df = df.drop(columns=drop_cols)
        log(f"Dropped duplicate columns: {drop_cols}")
        # re-detect aliases after drops
        aliases = detect_aliases(set(df.columns))
        log(f"Re-detected aliases after drops: {aliases}")

    orig_catalog = classify_all_originals(df)
    series = detect_behavioral_series(df)
    log(f"Behavioral series detected: {len(series)}")
    for name, months in series.items():
        log(f"  {name}: m{months[0]}..m{months[-1]} ({len(months)} months)")

    # split column
    split_col = aliases.get("split")

    # numeric originals (for F6A/F6C): exclude target/id/split/categorical
    excluded_for_numeric_transform = (
        ID_COLS | SPLIT_COLS | META_COLS | CATEGORICAL_SAFE
    )
    numeric_orig: list[str] = []
    for col in df.columns:
        if col in excluded_for_numeric_transform:
            continue
        # skip target
        if any(re.match(p, col) for p in TARGET_PATTERNS):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_orig.append(col)
    log(f"Numeric originals (for F6A/F6C transforms): {len(numeric_orig)}")

    # ---- Step C: Generate ----
    rng = np.random.default_rng(SEED)
    all_features: dict[str, np.ndarray] = {}
    gen_catalog: list[dict] = []
    f5a_fb: dict = {}

    # F1
    f1_out, f1_cat = f1_rolling(df, series)
    all_features.update(f1_out); gen_catalog.extend(f1_cat); del f1_out; gc.collect()
    # F2
    f2_out, f2_cat = f2_trends(df, series)
    all_features.update(f2_out); gen_catalog.extend(f2_cat); del f2_out; gc.collect()
    # F3
    f3_out, f3_cat = f3_ratios(df, aliases)
    all_features.update(f3_out); gen_catalog.extend(f3_cat); del f3_out
    # F4
    f4_out, f4_cat = f4_interactions(df, aliases)
    all_features.update(f4_out); gen_catalog.extend(f4_cat); del f4_out
    # F5A
    f5a_out, f5a_cat, f5a_fb = f5a_app_group_stats(df, split_col)
    all_features.update(f5a_out); gen_catalog.extend(f5a_cat); del f5a_out
    # F5B
    f5b_out, f5b_cat = f5b_loanterm_group_stats(df, split_col, aliases)
    all_features.update(f5b_out); gen_catalog.extend(f5b_cat); del f5b_out
    # F6A
    f6a_out, f6a_cat = f6a_rank_pct(df, numeric_orig)
    all_features.update(f6a_out); gen_catalog.extend(f6a_cat); del f6a_out; gc.collect()
    # F6B
    f6b_out, f6b_cat = f6b_bins(df, aliases)
    all_features.update(f6b_out); gen_catalog.extend(f6b_cat); del f6b_out
    # F6C
    f6c_out, f6c_cat = f6c_noisy(df, numeric_orig, rng)
    all_features.update(f6c_out); gen_catalog.extend(f6c_cat); del f6c_out; gc.collect()
    # F6D
    f6d_out, f6d_cat = f6d_random(df, rng)
    all_features.update(f6d_out); gen_catalog.extend(f6d_cat); del f6d_out
    # F6E
    f6e_out, f6e_cat = f6e_synth_bureau(df, aliases, rng)
    all_features.update(f6e_out); gen_catalog.extend(f6e_cat); del f6e_out; gc.collect()

    log(f"Total generated features: {len(all_features)}")

    # ---- Build expanded ABT ----
    log("Assembling expanded ABT...")
    gen_df = pd.DataFrame(all_features)
    expanded = pd.concat([df.reset_index(drop=True), gen_df.reset_index(drop=True)],
                         axis=1)
    log(f"  expanded: {len(expanded):,} rows x {len(expanded.columns)} cols")
    log(f"  memory: {expanded.memory_usage(deep=True).sum() / 1024**2:.0f} MB")
    del gen_df, all_features; gc.collect()

    # ---- Build full catalog ----
    full_catalog = pd.DataFrame(orig_catalog + gen_catalog, columns=GOV_FIELDS)
    log(f"Full catalog: {len(full_catalog)} rows")

    # ---- Step D: validate ----
    val = validate_outputs(expanded, full_catalog, n_rows_orig)

    # ---- Step E: save ----
    log("Saving outputs...")
    abt_path_pq = OUTPUT_DIR / "thesis_wide_abt_expanded.parquet"
    abt_path_gz = OUTPUT_DIR / "thesis_wide_abt_expanded.csv.gz"
    saved_format: str = ""
    ok, info = try_save_parquet(expanded, abt_path_pq)
    if ok:
        saved_format = "parquet"
        log(f"  saved: {abt_path_pq} ({info})")
    else:
        log(f"  parquet unavailable: {info}")
        log(f"  falling back to csv.gz...")
        save_csvgz(expanded, abt_path_gz)
        saved_format = "csv.gz"
        log(f"  saved: {abt_path_gz}")

    catalog_path = OUTPUT_DIR / "feature_catalog.csv"
    full_catalog.to_csv(catalog_path, index=False)
    log(f"  saved: {catalog_path}")

    # family summary
    fam_summary = full_catalog.groupby("feature_family").agg(
        count=("feature_name", "count"),
        allowed_orig_pd=("allowed_for_origination_pd", "sum"),
        allowed_beh_pd=("allowed_for_behavioral_pd", "sum"),
        allowed_profit=("allowed_for_profit", "sum"),
        leakage_high=("leakage_risk", lambda s: (s == "high").sum()),
        leakage_medium=("leakage_risk", lambda s: (s == "medium").sum()),
        leakage_low=("leakage_risk", lambda s: (s == "low").sum()),
    )
    summary_path = OUTPUT_DIR / "feature_family_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("Feature family summary\n")
        f.write("=" * 70 + "\n\n")
        f.write(fam_summary.to_string() + "\n")
    log(f"  saved: {summary_path}")

    # raw_feature_count
    excluded_from_raw = full_catalog[
        full_catalog["feature_family"].isin(
            ["ORIGINAL_TARGET", "ORIGINAL_ID", "ORIGINAL_SPLIT", "ORIGINAL_OTHER"]
        )
    ]
    raw_feature_count = len(full_catalog) - len(excluded_from_raw)

    # run_config
    run_config = {
        "phase": "1.5 Feature Factory",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "seed": SEED,
        "input_csv": str(INPUT_CSV),
        "output_dir": str(OUTPUT_DIR),
        "input_rows": n_rows_orig,
        "input_cols": n_rows_orig and (len(orig_catalog)),
        "drop_cols": drop_cols,
        "dup_info": dup_info,
        "aliases": aliases,
        "behavioral_series_count": len(series),
        "numeric_originals_count": len(numeric_orig),
        "total_columns_after": int(len(expanded.columns)),
        "total_features_generated": int(len(gen_catalog)),
        "raw_feature_count_excluding_id_target_split": int(raw_feature_count),
        "save_format": saved_format,
        "validation": val,
        "f5a_fallback_per_feature_sample":
            {k: f5a_fb[k] for k in list(f5a_fb)[:5]},
        "f5a_fallback_overall": (
            {"oot_features": len(f5a_fb),
             "max_fallback_rate": max((v["fallback_rate"] for v in f5a_fb.values()),
                                       default=0.0),
             "mean_fallback_rate": (sum(v["fallback_rate"] for v in f5a_fb.values()) /
                                     max(len(f5a_fb), 1))}),
    }
    with open(OUTPUT_DIR / "run_config.json", "w", encoding="utf-8") as f:
        json.dump(run_config, f, indent=2, default=str)
    log(f"  saved: {OUTPUT_DIR / 'run_config.json'}")

    # ---- Phase 1.5 report.md ----
    write_report(OUTPUT_DIR / "phase1_5_report.md",
                 expanded, full_catalog, fam_summary, run_config,
                 dup_info, aliases, series, f5a_fb, val)

    # ---- log file ----
    with open(OUTPUT_DIR / "extraction_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(_log_lines))

    rule()
    log("DONE.")
    rule()
    return 0


def write_report(path: Path, expanded: pd.DataFrame, catalog: pd.DataFrame,
                 fam_summary: pd.DataFrame, run_config: dict,
                 dup_info: dict, aliases: dict, series: dict,
                 f5a_fb: dict, val: dict) -> None:
    log("Writing phase1_5_report.md...")
    raw_count = run_config["raw_feature_count_excluding_id_target_split"]
    n_orig = sum(1 for r in catalog["feature_family"] if str(r).startswith("ORIGINAL"))
    n_gen = len(catalog) - n_orig

    # helpers
    fam_counts = catalog["feature_family"].value_counts()
    gov_summary = {
        "allowed_for_origination_pd_true": int(catalog["allowed_for_origination_pd"].sum()),
        "allowed_for_behavioral_pd_true": int(catalog["allowed_for_behavioral_pd"].sum()),
        "allowed_for_profit_true": int(catalog["allowed_for_profit"].sum()),
        "leakage_low": int((catalog["leakage_risk"] == "low").sum()),
        "leakage_medium": int((catalog["leakage_risk"] == "medium").sum()),
        "leakage_high": int((catalog["leakage_risk"] == "high").sum()),
        "uses_target_true": int(catalog["uses_target"].sum()),
        "uses_future_behavior_true": int(catalog["uses_future_behavior"].sum()),
    }

    sparse_features: list[tuple[str, float]] = []
    # spot-check NaN rates on generated columns (sample to control runtime)
    sample_cols = catalog[~catalog["feature_family"].str.startswith("ORIGINAL")][
        "feature_name"].sample(
        n=min(2000, n_gen),
        random_state=SEED,
    ).tolist()
    for c in sample_cols:
        if c in expanded.columns:
            nr = expanded[c].isna().mean()
            if nr > 0.5:
                sparse_features.append((c, float(nr)))
    sparse_features.sort(key=lambda x: -x[1])

    lines: list[str] = []
    lines.append("# Phase 1.5 Feature Factory Report\n")
    lines.append("\n## 1. Purpose\n")
    lines.append(
        f"Expand raw variable universe to >= 2000 raw features (excl. ID/target/split) "
        f"with governance metadata for every column.\n"
    )
    lines.append("\n## 2. Input\n")
    lines.append(
        f"- Cleaned wide ABT: {run_config['input_rows']:,} rows x "
        f"{run_config['input_cols']} cols\n"
        f"- Schema aliases detected: {aliases}\n"
        f"- Duplicate-column check: {dup_info}\n"
        f"- Dropped duplicates: {run_config['drop_cols']}\n"
    )
    lines.append("\n## 3. Methodology\n")
    lines.append(
        "Six families generated with auto-flagged governance via Rule Precedence "
        "(most restrictive level wins). Source-based restrictions override "
        "family-based defaults.\n"
        "\n- F1 Rolling stats: mean/std/min/max/median/last over {3m,6m,9m,12m} per "
        "behavioral series + first/last endpoints.\n"
        "- F2 Trend: slope/intercept/r2 over {3m,6m,12m} per series.\n"
        "- F3 Ratio: domain ratios with source-inherit governance.\n"
        "- F4 Interactions: products + polynomials, source-inherit.\n"
        "- F5A: app-only TRAIN-ONLY group statistics with global-train fallback.\n"
        "- F5B: loan-term group stats (level E inheritance).\n"
        "- F6A/B/C: rank/bin/noisy transforms with source-inherit governance.\n"
        "- F6D: pure random negative controls (level H, allowed for PD).\n"
        "- F6E: synthetic bureau-like from safe app + noise ONLY.\n"
    )
    lines.append("\n## 4. Output Summary\n")

    lines.append("\n### 4.1 Original column classification\n\n")
    lines.append("| Original family | Count |\n|---|---|\n")
    for fam in sorted(fam_counts.index):
        if str(fam).startswith("ORIGINAL"):
            lines.append(f"| {fam} | {fam_counts[fam]} |\n")

    lines.append("\n### 4.2 Generated family breakdown\n\n")
    lines.append("| Family | Count |\n|---|---|\n")
    for fam in sorted(fam_counts.index):
        if not str(fam).startswith("ORIGINAL"):
            lines.append(f"| {fam} | {fam_counts[fam]} |\n")

    lines.append(f"\n### 4.3 Combined catalog summary\n\n")
    lines.append("| Metric | Count |\n|---|---|\n")
    lines.append(f"| Total ABT columns | {len(expanded.columns)} |\n")
    lines.append(f"| Original columns | {n_orig} |\n")
    lines.append(f"| Generated columns | {n_gen} |\n")
    lines.append(f"| raw_feature_count (excl ID/target/split/meta) | {raw_count} |\n")

    lines.append(f"\n### 4.4 Governance breakdown\n\n")
    lines.append("| Metric | Count |\n|---|---|\n")
    for k, v in gov_summary.items():
        lines.append(f"| {k} | {v} |\n")

    lines.append(f"\n### 4.5 Rule Precedence verification (5 examples per level)\n\n")
    for level_name in ["A", "B", "C", "D", "E", "F", "G", "H"]:
        # find examples by family heuristic
        if level_name == "A":
            ex = catalog[catalog["uses_target"] == True]["feature_name"].head(5).tolist()
        elif level_name == "B":
            ex = catalog[catalog["feature_family"].isin(
                ["ORIGINAL_ID", "ORIGINAL_SPLIT", "ORIGINAL_OTHER"])
            ]["feature_name"].head(5).tolist()
        elif level_name == "C":
            ex = catalog[(catalog["leakage_risk"] == "high") &
                         (catalog["uses_future_behavior"] == True)]["feature_name"].head(5).tolist()
        elif level_name == "D":
            ex = catalog[catalog["reason_if_not_allowed_for_pd"].str.contains(
                "aggregate behavioral target-proxy", na=False)]["feature_name"].head(5).tolist()
        elif level_name == "E":
            ex = catalog[catalog["reason_if_not_allowed_for_pd"].str.contains(
                "loan-term", na=False)]["feature_name"].head(5).tolist()
        elif level_name == "F":
            ex = catalog[(catalog["leakage_risk"] == "medium") &
                         (catalog["uses_future_behavior"] == True)]["feature_name"].head(5).tolist()
        elif level_name == "G":
            ex = catalog[(catalog["allowed_for_origination_pd"] == True) &
                         (catalog["uses_future_behavior"] == False) &
                         (catalog["feature_family"] != "F6D")]["feature_name"].head(5).tolist()
        else:  # H
            ex = catalog[catalog["feature_family"] == "F6D"]["feature_name"].head(5).tolist()
        lines.append(f"\n**Level {level_name}**: {ex}\n")

    lines.append("\n### 4.6 Family 5A unseen-group fallback report\n\n")
    if f5a_fb:
        avg_fb = sum(v["fallback_rate"] for v in f5a_fb.values()) / len(f5a_fb)
        max_fb_feat = max(f5a_fb.items(), key=lambda kv: kv[1]["fallback_rate"])
        lines.append(f"- F5A features generated: {len(f5a_fb)}\n")
        lines.append(f"- Avg OOT fallback rate: {avg_fb:.4%}\n")
        lines.append(f"- Max OOT fallback rate: {max_fb_feat[1]['fallback_rate']:.4%} "
                     f"(in feature `{max_fb_feat[0]}`)\n")
    else:
        lines.append("- F5A skipped (no split column available).\n")

    lines.append("\n## 5. Validation Checks\n\n")
    for k, v in val.items():
        status = "PASS" if v else "WARN"
        lines.append(f"- {k}: {status}\n")
    lines.append(f"- Storage format: **{run_config['save_format']}**\n")
    lines.append(f"- Memory size: {expanded.memory_usage(deep=True).sum()/1024**2:.0f} MB\n")
    if sparse_features:
        lines.append(f"- Top 10 sparse features (>50% NaN, sampled):\n")
        for n, r in sparse_features[:10]:
            lines.append(f"  - `{n}`: {r:.2%}\n")
    else:
        lines.append("- No features with >50% NaN found in sampled subset.\n")

    lines.append("\n## 6. Limitations\n\n")
    lines.append(
        "- Family 5 target-encoding excluded by design.\n"
        "- Linear amortization assumption in some ratios.\n"
        "- Some rolling stats undefined for short-history series (act_cus_seniority "
        "m2-m6 only) -> NaN-heavy in 9m/12m windows.\n"
        "- F6E synthetic bureau features are NOT calibrated to target. Any predictive "
        "association arises indirectly via app-variable signal already in the simulator.\n"
    )

    lines.append("\n## 7. Next Steps (DO NOT EXECUTE YET)\n\n")
    lines.append(
        "- User reviews catalog.\n"
        "- Phase 2 rerun MUST filter via:\n"
        "  ```python\n"
        "  catalog['allowed_for_origination_pd'] == True\n"
        "  AND catalog['leakage_risk'] != 'high'\n"
        "  AND catalog['uses_target'] == False\n"
        "  AND catalog['uses_future_behavior'] == False\n"
        "  ```\n"
        "- Phase 2 should verify F6D random controls are NOT selected by Lasso "
        "(selection sanity check).\n"
    )

    path.write_text("".join(lines), encoding="utf-8")
    log(f"  saved: {path}")


if __name__ == "__main__":
    sys.exit(main())
