#!/usr/bin/env python3
"""Enrich thesis_abt.csv with per-loan profit columns.

Reads  : <input_dir>/thesis_abt.csv
Writes : <input_dir>/thesis_abt.csv   (overwrite — columns added/replaced)
         <input_dir>/thesis_abt_report.txt  (enrichment section appended)

Steps
-----
1. Fix lgd nulls  : set lgd = 0.0 for non-defaulted and OOT rows
2. Add profit cols: profit_r5 / r8 / r10 / r12 / r15
                    profit_if_approved == profit_r10 (base case alias)
3. Drop any stale intermediate columns left by previous runs
   (interest_income, loss)
4. Append enrichment summary to thesis_abt_report.txt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RATE_COLS = [0.05, 0.08, 0.10, 0.12, 0.15]   # annual net interest margin
BASE_RATE = 0.10                               # base case

# Columns this script manages (drop & recreate for idempotency)
MANAGED_COLS = (
    ["profit_r5", "profit_r8", "profit_r10", "profit_r12", "profit_r15",
     "profit_if_approved",
     # stale intermediates from any previous inline run
     "interest_income", "loss"]
)


def col_name(r: float) -> str:
    return f"profit_r{int(r * 100)}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sep(title: str = "", width: int = 60) -> None:
    if title:
        print(f"\n{'=' * width}")
        print(f"  {title}")
        print(f"{'=' * width}")
    else:
        print("-" * width)


def log(msg: str) -> None:
    print(f"[enrich_thesis_abt] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Step 1 — Fix lgd nulls
# ---------------------------------------------------------------------------

def fix_lgd(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    before = int(df["lgd"].isna().sum())
    df.loc[df["default_flag"] == 0,   "lgd"] = 0.0
    df.loc[df["default_flag"].isna(),  "lgd"] = 0.0
    after = int(df["lgd"].isna().sum())
    log(f"Step 1 -- lgd nulls: {before:,} -> {after:,}")
    return df, {"lgd_null_before": before, "lgd_null_after": after}


# ---------------------------------------------------------------------------
# Step 2 — Add profit columns
# ---------------------------------------------------------------------------

def add_profit_cols(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    # Drop any previously managed columns so the run is idempotent
    stale = [c for c in MANAGED_COLS if c in df.columns]
    if stale:
        df = df.drop(columns=stale)
        log(f"  Dropped {len(stale)} stale columns: {stale}")

    mask_known = df["default_flag"].notna()
    oot_count  = int(df["default_flag"].isna().sum())

    for r in RATE_COLS:
        cname = col_name(r)
        df[cname] = np.nan
        df.loc[mask_known, cname] = (
            (1 - df.loc[mask_known, "default_flag"]) * df.loc[mask_known, "loan_amount"] * r
            - df.loc[mask_known, "default_flag"]     * df.loc[mask_known, "ead"]          * df.loc[mask_known, "lgd"]
        )

    # Base case alias
    df["profit_if_approved"] = df[col_name(BASE_RATE)]

    log(f"Step 2 -- added profit cols for r = {[col_name(r) for r in RATE_COLS]}")
    log(f"          profit_if_approved = {col_name(BASE_RATE)} (base case)")
    log(f"          OOT rows (null profit): {oot_count:,}")

    return df, {"oot_count": oot_count}


# ---------------------------------------------------------------------------
# Step 3 — Compute summary stats
# ---------------------------------------------------------------------------

def compute_summary(df: pd.DataFrame) -> dict:
    train     = df[df["split"] == "train"]
    def_rows  = train[train["default_flag"] == 1]
    nd_rows   = train[train["default_flag"] == 0]

    mean_all     = float(train["profit_if_approved"].mean())
    mean_def     = float(def_rows["profit_if_approved"].mean())
    mean_nodef   = float(nd_rows["profit_if_approved"].mean())
    n_train      = len(train)
    n_def        = len(def_rows)
    n_nodef      = len(nd_rows)

    # Sensitivity means on train
    sensitivity: dict[float, float] = {}
    for r in RATE_COLS:
        sensitivity[r] = float(train[col_name(r)].mean())

    # Breakeven rate: solve mean((1-d)*L*r - d*EAD*LGD) = 0 analytically
    # => r* = mean(d * EAD * LGD) / mean((1-d) * L)
    expected_loss   = float((train["default_flag"] * train["ead"] * train["lgd"]).mean())
    expected_income = float(((1 - train["default_flag"]) * train["loan_amount"]).mean())
    breakeven_r     = expected_loss / expected_income if expected_income > 0 else float("nan")

    return {
        "n_train":       n_train,
        "n_defaulted":   n_def,
        "n_nondefault":  n_nodef,
        "mean_profit_all":    mean_all,
        "mean_profit_def":    mean_def,
        "mean_profit_nodef":  mean_nodef,
        "sensitivity":        sensitivity,
        "breakeven_r":        breakeven_r,
    }


# ---------------------------------------------------------------------------
# Step 4 — Append enrichment section to report
# ---------------------------------------------------------------------------

def append_report(report_path: Path, lgd_info: dict, profit_info: dict, stats: dict) -> None:
    lines = [
        "",
        "Enrichment -- profit columns",
        "-" * 60,
        f"  Rate assumption (base case)    : r = {BASE_RATE:.2f} (annual net interest margin)",
        f"  Sensitivity rates              : r = {[f'{r:.2f}' for r in RATE_COLS]}",
        "",
        "  Step 1 -- lgd null fix:",
        f"    lgd nulls before : {lgd_info['lgd_null_before']:,}",
        f"    lgd nulls after  : {lgd_info['lgd_null_after']:,}  (0 = fixed)",
        "",
        "  Step 2 -- profit columns added:",
        *[f"    {col_name(r):<20}  (r={r:.2f})" for r in RATE_COLS],
        f"    profit_if_approved  = {col_name(BASE_RATE)} (base case alias)",
        f"    OOT rows (null)     : {profit_info['oot_count']:,}",
        "",
        "  Train-set summary (default_flag known):",
        f"    n_train              : {stats['n_train']:,}",
        f"    n_defaulted          : {stats['n_defaulted']:,}",
        f"    n_non-defaulted      : {stats['n_nondefault']:,}",
        "",
        f"    Mean profit_if_approved (all train)   : {stats['mean_profit_all']:>10.4f}",
        f"    Mean profit_if_approved (defaulted)   : {stats['mean_profit_def']:>10.4f}",
        f"    Mean profit_if_approved (non-default) : {stats['mean_profit_nodef']:>10.4f}",
        "",
        "  Sensitivity -- mean profit on train:",
        *[f"    r={r:.2f}  {col_name(r):<20}: {stats['sensitivity'][r]:>10.4f}"
          for r in RATE_COLS],
        "",
        f"  Breakeven rate (mean profit = 0): r* = {stats['breakeven_r']:.4f} "
        f"({stats['breakeven_r'] * 100:.2f}%)",
        "  Note: at base case r=0.10, portfolio is profitable but close to breakeven.",
    ]

    with open(report_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    log(f"Step 3 -- appended enrichment section to {report_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enrich thesis_abt.csv with lgd fix and profit columns."
    )
    parser.add_argument(
        "--input-dir", type=Path,
        default=Path("artifacts/thesis_abt"),
        help="Directory containing thesis_abt.csv and thesis_abt_report.txt",
    )
    args = parser.parse_args()

    input_dir   = args.input_dir.resolve()
    csv_path    = input_dir / "thesis_abt.csv"
    report_path = input_dir / "thesis_abt_report.txt"

    if not csv_path.exists():
        log(f"ERROR: {csv_path} not found")
        return 1

    # Load
    log(f"Loading {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    log(f"  Shape: {df.shape[0]:,} rows x {df.shape[1]} cols")

    # Step 1
    df, lgd_info = fix_lgd(df)

    # Step 2
    df, profit_info = add_profit_cols(df)

    # Summary stats
    stats = compute_summary(df)

    # Print summary
    sep("Summary")
    print(f"  Train set ({stats['n_train']:,} rows):")
    print(f"    Mean profit_if_approved (all)         : {stats['mean_profit_all']:>10.4f}")
    print(f"    Mean profit_if_approved (defaulted)   : {stats['mean_profit_def']:>10.4f}")
    print(f"    Mean profit_if_approved (non-default) : {stats['mean_profit_nodef']:>10.4f}")
    print()
    print(f"  Sensitivity -- mean profit on train:")
    for r in RATE_COLS:
        print(f"    r={r:.2f}  {col_name(r):<20}: {stats['sensitivity'][r]:>10.4f}")
    print()
    print(f"  Breakeven rate : r* = {stats['breakeven_r']:.4f}  ({stats['breakeven_r']*100:.2f}%)")
    print()
    print(f"  Null count checks:")
    oot = profit_info["oot_count"]
    for c in [col_name(r) for r in RATE_COLS] + ["profit_if_approved"]:
        n = int(df[c].isna().sum())
        status = "OK" if n == oot else f"MISMATCH expected {oot:,}"
        print(f"    {c:<25}  nulls={n:,}  {status}")
    print(f"    lgd null after fix          :  nulls={lgd_info['lgd_null_after']:,}  "
          f"{'OK' if lgd_info['lgd_null_after'] == 0 else 'WARN'}")

    # Write CSV
    log(f"Writing {csv_path}  ({df.shape[0]:,} rows x {df.shape[1]} cols)")
    df.to_csv(csv_path, index=False)

    # Append to report
    if report_path.exists():
        append_report(report_path, lgd_info, profit_info, stats)
    else:
        log(f"WARNING: {report_path} not found -- skipping report append")

    sep("Done")
    log(f"Final schema: {df.shape[1]} cols")
    log(f"New cols: {[col_name(r) for r in RATE_COLS] + ['profit_if_approved']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
