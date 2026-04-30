#!/usr/bin/env python3
"""Thorough data quality audit for thesis_wide_abt.csv."""
from __future__ import annotations
import sys
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 120)


def sep(title: str = "", width: int = 70) -> None:
    if title:
        print(f"\n{'=' * width}")
        print(f"  {title}")
        print(f"{'=' * width}")
    else:
        print("-" * width)


def flag(level: str, msg: str) -> None:
    print(f"  [{level}] {msg}")


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load(path: Path) -> pd.DataFrame:
    print(f"Loading {path} ...", flush=True)
    df = pd.read_csv(path, low_memory=False)
    print(f"  Shape: {df.shape[0]:,} rows × {df.shape[1]} cols", flush=True)
    return df


# ---------------------------------------------------------------------------
# 1. Null analysis
# ---------------------------------------------------------------------------
KNOWN_NULLABLE = {c for c in [
    "default_flag_12m",
    *[f"ags6_{s}"  for s in ["Mean_Due","Max_Due","Min_Due","Mean_Days","Max_Days","Min_Days",
                              "Mean_CMax_Days","Max_CMax_Days","Min_CMax_Days","Mean_CMax_Due","Max_CMax_Due","Min_CMax_Due"]],
    *[f"ags12_{s}" for s in ["Mean_Due","Max_Due","Min_Due","Mean_Days","Max_Days","Min_Days",
                              "Mean_CMax_Days","Max_CMax_Days","Min_CMax_Days","Mean_CMax_Due","Max_CMax_Due","Min_CMax_Due"]],
]}


def audit_nulls(df: pd.DataFrame) -> None:
    sep("1. NULL ANALYSIS")
    n = len(df)
    null_counts = df.isna().sum()
    null_cols = null_counts[null_counts > 0].sort_values(ascending=False)

    if null_cols.empty:
        flag("OK", "No null values in any column")
        return

    print(f"\n  Columns with nulls ({len(null_cols)} total):")
    print(f"  {'Column':<40} {'NullCount':>12} {'%':>8}  Status")
    sep()
    for col, cnt in null_cols.items():
        pct = cnt / n * 100
        if col in KNOWN_NULLABLE:
            status = "OK  (expected)"
        elif pct > 5:
            status = "ERROR — >5% unexpected nulls"
        elif pct > 0:
            status = "WARN — unexpected nulls"
        else:
            status = "OK"
        print(f"  {col:<40} {cnt:>12,} {pct:>7.2f}%  {status}")


# ---------------------------------------------------------------------------
# 2. Constant / near-constant columns
# ---------------------------------------------------------------------------
def audit_constants(df: pd.DataFrame) -> None:
    sep("2. CONSTANT / NEAR-CONSTANT COLUMNS")
    n = len(df)
    issues_found = False

    for col in df.columns:
        s = df[col].dropna()
        if len(s) == 0:
            continue
        # Constant
        if s.nunique() == 1:
            flag("ERROR", f"{col}: constant — only value = {s.iloc[0]!r}")
            issues_found = True
            continue
        # Near-constant: top value >99%
        top_val = s.value_counts().iloc[0]
        top_pct = top_val / n * 100
        if top_pct > 99:
            flag("WARN", f"{col}: near-constant — top value covers {top_pct:.1f}% of rows "
                         f"(value={s.value_counts().index[0]!r})")
            issues_found = True

    if not issues_found:
        flag("OK", "No constant or near-constant columns found")


# ---------------------------------------------------------------------------
# 3. Duplicate rows
# ---------------------------------------------------------------------------
def audit_duplicates(df: pd.DataFrame) -> None:
    sep("3. DUPLICATE ROWS")

    # Duplicate aid
    dup_aid = df["aid"].duplicated().sum()
    if dup_aid == 0:
        flag("OK", "No duplicate aid values")
    else:
        flag("ERROR", f"{dup_aid:,} duplicate aid values")

    # Duplicate (cid, fin_period)
    dup_pair = df.duplicated(subset=["cid", "fin_period"]).sum()
    if dup_pair == 0:
        flag("OK", "No duplicate (cid, fin_period) pairs")
    else:
        flag("WARN", f"{dup_pair:,} duplicate (cid, fin_period) pairs")


# ---------------------------------------------------------------------------
# 4. Target sanity
# ---------------------------------------------------------------------------
def audit_target(df: pd.DataFrame) -> None:
    sep("4. TARGET SANITY")
    n = len(df)

    # Distribution
    n1  = int((df["default_flag_12m"] == 1).sum())
    n0  = int((df["default_flag_12m"] == 0).sum())
    nna = int(df["default_flag_12m"].isna().sum())
    print(f"  default_flag_12m distribution:")
    print(f"    1   (defaulted) : {n1:>8,}  ({n1/n*100:.2f}%)")
    print(f"    0   (closed)    : {n0:>8,}  ({n0/n*100:.2f}%)")
    print(f"    NaN (censored)  : {nna:>8,}  ({nna/n*100:.2f}%)")

    # Cross-check: defaulted aids have observation_status == "defaulted"
    mask_flag1  = df["default_flag_12m"] == 1
    mask_status = df["observation_status"] == "defaulted"
    mismatch_1  = (mask_flag1 & ~mask_status).sum()
    mismatch_2  = (~mask_flag1 & mask_status).sum()
    if mismatch_1 == 0 and mismatch_2 == 0:
        flag("OK", "default_flag_12m==1 <-> observation_status=='defaulted' fully consistent")
    else:
        if mismatch_1:
            flag("ERROR", f"{mismatch_1:,} aids have default_flag_12m==1 but observation_status!='defaulted'")
        if mismatch_2:
            flag("ERROR", f"{mismatch_2:,} aids have observation_status=='defaulted' but default_flag_12m!=1")

    # Cross-check: censored aids have default_flag_12m == NaN
    mask_oot    = df["observation_status"] == "censored"
    mask_na     = df["default_flag_12m"].isna()
    mismatch_c1 = (mask_oot & ~mask_na).sum()
    mismatch_c2 = (~mask_oot & mask_na).sum()
    if mismatch_c1 == 0 and mismatch_c2 == 0:
        flag("OK", "censored ↔ default_flag_12m==NaN fully consistent")
    else:
        if mismatch_c1:
            flag("ERROR", f"{mismatch_c1:,} censored aids have non-NaN default_flag_12m")
        if mismatch_c2:
            flag("ERROR", f"{mismatch_c2:,} non-censored aids have NaN default_flag_12m")


# ---------------------------------------------------------------------------
# 5. Feature range sanity
# ---------------------------------------------------------------------------
EXPECTED_NON_NEGATIVE = [
    "app_income", "app_loan_amount", "app_n_installments", "app_spendings",
    "act_age", "installment", "n_installments", "loan_amount",
    "paid_fraction_at_obs",
]
for _base in ["act_due", "act_paid_installments", "act_cc", "act_days"]:
    EXPECTED_NON_NEGATIVE += [f"{_base}_m{m}" for m in range(1, 13)]

RATIO_COLS = (
    [f"act_utl_m{m}"    for m in range(1, 13)] +
    [f"act_dueutl_m{m}" for m in range(1, 13)] +
    ["paid_fraction_at_obs"]
)


def audit_ranges(df: pd.DataFrame) -> None:
    sep("5. FEATURE RANGE SANITY")

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    skip_cols = {"default_flag_12m"}  # nullable int, handled in section 4
    numeric_cols = [c for c in numeric_cols if c not in skip_cols]

    print(f"\n  Checking {len(numeric_cols)} numeric columns ...\n")
    print(f"  {'Column':<45} {'Min':>14} {'Max':>14} {'Mean':>14}  Flags")
    sep()

    issues: list[str] = []
    ok_count = 0

    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) == 0:
            continue
        cmin  = float(s.min())
        cmax  = float(s.max())
        cmean = float(s.mean())

        flags_col: list[str] = []

        # Negative where not expected
        if col in EXPECTED_NON_NEGATIVE and cmin < 0:
            flags_col.append(f"WARN: negative min={cmin:.4g}")

        # Ratio > 1 where not expected
        if col in RATIO_COLS and cmax > 1.0:
            flags_col.append(f"WARN: ratio col max={cmax:.4g} >1.0")

        # Extreme outlier: max > 100× mean (only for positive-mean cols)
        if cmean > 0 and cmax > 100 * cmean:
            flags_col.append(f"WARN: extreme outlier max={cmax:.4g} ({cmax/cmean:.0f}× mean)")

        if flags_col:
            issues.append((col, cmin, cmax, cmean, flags_col))
            print(f"  {col:<45} {cmin:>14.4g} {cmax:>14.4g} {cmean:>14.4g}  {' | '.join(flags_col)}")
        else:
            ok_count += 1

    sep()
    if issues:
        print(f"\n  {ok_count} columns OK, {len(issues)} columns with flags above.")
    else:
        flag("OK", f"All {ok_count} numeric columns pass range checks")


# ---------------------------------------------------------------------------
# 6. Train/OOT split sanity
# ---------------------------------------------------------------------------
def audit_split(df: pd.DataFrame) -> None:
    sep("6. TRAIN / OOT SPLIT SANITY")

    print("\n  fin_period distribution by split:")
    grp = df.groupby("split")["fin_period"].agg(["min", "max", "count"])
    grp.columns = ["fin_period_min", "fin_period_max", "count"]
    for split, row in grp.iterrows():
        print(f"    {split:<8}: fin_period {int(row['fin_period_min'])} → {int(row['fin_period_max'])}"
              f"   ({int(row['count']):,} rows)")

    # Time purity: max train fin_period < min OOT fin_period
    if "train" in grp.index and "oot" in grp.index:
        train_max = grp.loc["train", "fin_period_max"]
        oot_min   = grp.loc["oot",   "fin_period_min"]
        if train_max < oot_min:
            flag("OK", f"Time purity confirmed — train max fin_period {int(train_max)} < "
                       f"oot min fin_period {int(oot_min)}")
        else:
            flag("ERROR", f"Time contamination — train max fin_period {int(train_max)} "
                          f">= oot min fin_period {int(oot_min)}")
    else:
        flag("WARN", "Could not find both 'train' and 'oot' splits for time-purity check")

    # obs_period distribution
    print("\n  obs_period range by split:")
    grp2 = df.groupby("split")["obs_period"].agg(["min", "max"])
    for split, row in grp2.iterrows():
        print(f"    {split:<8}: obs_period {int(row['min'])} → {int(row['max'])}")


# ---------------------------------------------------------------------------
# 7. Economics sanity (defaulted only)
# ---------------------------------------------------------------------------
def audit_economics(df: pd.DataFrame) -> None:
    sep("7. ECONOMICS SANITY (defaulted accounts only)")

    defaulted = df[df["observation_status"] == "defaulted"]
    n_def = len(defaulted)
    print(f"\n  Defaulted accounts: {n_def:,}")

    if n_def == 0:
        flag("WARN", "No defaulted accounts found — skipping economics checks")
        return

    # paid_fraction_at_obs
    if "paid_fraction_at_obs" in defaulted.columns:
        pf = defaulted["paid_fraction_at_obs"].dropna()
        print(f"\n  paid_fraction_at_obs (on defaulted):")
        print(f"    min={pf.min():.4f}  max={pf.max():.4f}  mean={pf.mean():.4f}")
        if (pf > 1.0).any():
            flag("WARN", f"{(pf>1.0).sum():,} defaulted accounts have paid_fraction_at_obs > 1.0")
        elif (pf < 0).any():
            flag("WARN", f"{(pf<0).sum():,} defaulted accounts have paid_fraction_at_obs < 0")
        else:
            flag("OK", "paid_fraction_at_obs in [0, 1] for all defaulted accounts")

    # act_due at observation (last behavioral month)
    if "act_due_m12" in defaulted.columns:
        due = defaulted["act_due_m12"].dropna()
        print(f"\n  act_due_m12 (on defaulted — EAD proxy):")
        print(f"    min={due.min():.4f}  max={due.max():.4f}  mean={due.mean():.4f}")
        if (due < 0).any():
            flag("ERROR", f"{(due<0).sum():,} defaulted accounts have negative act_due_m12")
        else:
            flag("OK", "act_due_m12 >= 0 for all defaulted accounts")

    # act_loaninc (loan-to-income ratio — LGD proxy)
    if "act_loaninc_m12" in defaulted.columns:
        li = defaulted["act_loaninc_m12"].dropna()
        print(f"\n  act_loaninc_m12 (on defaulted — LGD-related):")
        print(f"    min={li.min():.4f}  max={li.max():.4f}  mean={li.mean():.4f}")
        if (li < 0).any():
            flag("WARN", f"{(li<0).sum():,} defaulted accounts have negative act_loaninc_m12")
        else:
            flag("OK", "act_loaninc_m12 >= 0 for all defaulted accounts")

    # Check if explicit ead/lgd columns exist
    for col in ["ead", "lgd", "loss"]:
        if col in defaulted.columns:
            s = defaulted[col].dropna()
            print(f"\n  {col} (on defaulted):")
            print(f"    min={s.min():.4f}  max={s.max():.4f}  mean={s.mean():.4f}")
            if col == "lgd":
                if (s > 1.0).any():
                    flag("ERROR", f"{(s>1.0).sum():,} accounts have lgd > 1.0")
                if (s < 0).any():
                    flag("ERROR", f"{(s<0).sum():,} accounts have lgd < 0")
                if (s <= 1.0).all() and (s >= 0).all():
                    flag("OK", "lgd in [0, 1] for all defaulted accounts")
            elif col == "ead":
                if (s < 0).any():
                    flag("ERROR", f"{(s<0).sum():,} accounts have ead < 0")
                else:
                    flag("OK", "ead >= 0 for all defaulted accounts")

    if not any(c in defaulted.columns for c in ["ead", "lgd", "loss"]):
        flag("WARN", "No explicit ead/lgd columns in schema — economics checks limited to act_due/paid_fraction proxies")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path,
                        default=Path("artifacts/thesis_wide_abt_12m_500c/thesis_wide_abt.csv"))
    args = parser.parse_args()

    csv_path = args.csv.resolve()
    df = load(csv_path)

    audit_nulls(df)
    audit_constants(df)
    audit_duplicates(df)
    audit_target(df)
    audit_ranges(df)
    audit_split(df)
    audit_economics(df)

    sep("AUDIT COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
