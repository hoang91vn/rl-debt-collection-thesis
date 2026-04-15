#!/usr/bin/env python3
"""Build thesis_abt.csv for profit-driven credit scoring analysis.

Reads simulator output from a run directory (abt_base_*.csv, accounts.csv,
transactions.csv) and produces a training-ready ABT with features at
origination + target + economics + split.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


# -- Constants ---------------------------------------------------------------

DEFAULT_DATA_DIR = Path("examples/thesis_baseline/runs/thesis_baseline")
DEFAULT_OUTPUT_DIR = Path("artifacts/thesis_abt")

ID_COLS = ["aid", "cid", "fin_period"]
APP_COLS = [
    "app_income",
    "app_loan_amount",
    "app_n_installments",
    "app_nom_branch",
    "app_nom_gender",
    "app_nom_job_code",
    "app_number_of_children",
    "app_nom_marital_status",
    "app_nom_city",
    "app_nom_home_status",
    "app_nom_cars",
    "app_spendings",
]
ACT_ORIG_COLS = ["act_age", "act_cc", "act_loaninc"]
ACT_CUS_COLS = [
    "act_cus_seniority",
    "act_cus_n_loans_hist",
    "act_cus_n_statC",
    "act_cus_n_statB",
    "act_cus_n_loans_act",
    "act_cus_utl",
    "act_cus_dueutl",
    "act_cus_cc",
]
LOAN_COLS = ["installment", "n_installments", "loan_amount"]
TARGET_COLS = ["default_flag"]
ECON_COLS = ["ead", "lgd", "paid_fraction"]
META_COLS = ["observation_status", "split", "period_terminal"]

FINAL_COLS = (
    ID_COLS
    + APP_COLS
    + ACT_ORIG_COLS
    + ACT_CUS_COLS
    + LOAN_COLS
    + TARGET_COLS
    + ECON_COLS
    + META_COLS
)


def log(msg: str) -> None:
    print(f"[build_thesis_abt] {msg}", flush=True)


# -- Step 1 ------------------------------------------------------------------

def load_origination_features(data_dir: Path) -> pd.DataFrame:
    """Read all abt_base_*.csv and keep rows where period == fin_period."""
    abt_files = sorted(data_dir.glob("abt_base_*.csv"))
    if not abt_files:
        raise FileNotFoundError(f"No abt_base_*.csv files found in {data_dir}")
    log(f"Step 1: loading {len(abt_files)} abt_base files")
    frames = []
    for f in abt_files:
        df = pd.read_csv(f)
        origination = df[df["period"] == df["fin_period"]]
        frames.append(origination)
    all_orig = pd.concat(frames, ignore_index=True)
    before = len(all_orig)
    all_orig = all_orig.drop_duplicates(subset=["aid"], keep="first")
    after = len(all_orig)
    if before != after:
        log(f"  note: dropped {before - after} duplicate origination rows")
    log(f"  {after:,} origination rows retained")
    return all_orig


# -- Step 2 ------------------------------------------------------------------

def load_accounts(data_dir: Path) -> pd.DataFrame:
    """Read accounts.csv and dedupe the duplicated 'aid' column (known CSV bug)."""
    log("Step 2: loading accounts.csv")
    path = data_dir / "accounts.csv"
    df = pd.read_csv(path)
    # Second 'aid' column is auto-renamed to 'aid.1' by pandas
    if "aid.1" in df.columns:
        df = df.drop(columns=["aid.1"])
    keep = ["aid", "installment", "n_installments", "loan_amount"]
    df = df[keep]
    log(f"  {len(df):,} account rows, columns kept: {keep}")
    return df


# -- Step 3 ------------------------------------------------------------------

def build_target(data_dir: Path) -> pd.DataFrame:
    """Build per-aid target and terminal metadata from transactions.csv."""
    log("Step 3: building target from transactions.csv")
    path = data_dir / "transactions.csv"
    tx = pd.read_csv(path)
    log(f"  read {len(tx):,} transaction rows")

    tx_sorted = tx.sort_values(["aid", "period"])

    # Terminal rows: status != 1 (active). Take first such row per aid.
    terminal_rows = tx_sorted[tx_sorted["status"] != 1]
    terminal_rows = terminal_rows.drop_duplicates(subset=["aid"], keep="first")
    log(f"  {len(terminal_rows):,} aids have a terminal row (status != 1)")

    terminal_out = pd.DataFrame(
        {
            "aid": terminal_rows["aid"].values,
            "default_flag": (terminal_rows["coll_status"] == 8).astype(int),
            "paid_terminal": terminal_rows["paid_installments"].astype(int).values,
            "period_terminal": terminal_rows["period"].astype(int).values,
        }
    )
    terminal_out["default_flag"] = terminal_out["default_flag"].astype("Int64")
    terminal_out["period_terminal"] = terminal_out["period_terminal"].astype("Int64")

    # Censored aids: still active at their last transaction row.
    all_aids = set(tx["aid"].unique())
    terminated_aids = set(terminal_rows["aid"].unique())
    censored_aids = all_aids - terminated_aids
    last_rows = tx_sorted.drop_duplicates(subset=["aid"], keep="last")
    censored_last = last_rows[last_rows["aid"].isin(censored_aids)]
    log(f"  {len(censored_last):,} aids are censored (still active at last period)")

    censored_out = pd.DataFrame(
        {
            "aid": censored_last["aid"].values,
            "default_flag": pd.array([pd.NA] * len(censored_last), dtype="Int64"),
            "paid_terminal": censored_last["paid_installments"].astype(int).values,
            "period_terminal": pd.array(
                [pd.NA] * len(censored_last), dtype="Int64"
            ),
        }
    )

    target = pd.concat([terminal_out, censored_out], ignore_index=True)
    return target


# -- Step 4 ------------------------------------------------------------------

def compute_economics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute ead, lgd, paid_fraction."""
    log("Step 4: computing economics (ead, lgd, paid_fraction)")
    df["ead"] = (df["n_installments"] - df["paid_terminal"]) * df["installment"]
    df["paid_fraction"] = df["paid_terminal"] / df["n_installments"]
    # LGD only defined for defaulted accounts.
    df["lgd"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
    defaulted_mask = df["default_flag"] == 1
    df.loc[defaulted_mask, "lgd"] = (
        df.loc[defaulted_mask, "ead"].astype(float)
        / df.loc[defaulted_mask, "loan_amount"].astype(float)
    )
    return df


# -- Step 5 / 6 --------------------------------------------------------------

def add_observation_and_split(df: pd.DataFrame) -> pd.DataFrame:
    """observation_status ∈ {defaulted, closed, censored}; split ∈ {train, oot}."""
    log("Step 5-6: adding observation_status and split")
    obs = pd.Series("censored", index=df.index, dtype="object")
    has_terminal = df["default_flag"].notna()
    obs.loc[has_terminal & (df["default_flag"] == 1)] = "defaulted"
    obs.loc[has_terminal & (df["default_flag"] == 0)] = "closed"
    df["observation_status"] = obs
    df["split"] = obs.where(obs == "censored", "train").mask(
        obs == "censored", "oot"
    )
    return df


# -- Report ------------------------------------------------------------------

def build_report(df: pd.DataFrame, run_dir: Path, csv_path: Path) -> str:
    train = df[df["split"] == "train"]
    oot = df[df["split"] == "oot"]
    defaulted = train[train["default_flag"] == 1]

    lines = []
    lines.append("thesis_abt report")
    lines.append("=" * 60)
    lines.append(f"Source run dir : {run_dir}")
    lines.append(f"Output CSV     : {csv_path}")
    lines.append(f"Rows in ABT    : {len(df):,}")
    lines.append("")

    lines.append("Split counts")
    lines.append("-" * 60)
    lines.append(f"  train (terminated) : {len(train):,}")
    lines.append(f"  oot   (censored)   : {len(oot):,}")
    pct_censored = len(oot) / len(df) if len(df) else 0
    lines.append(f"  censoring rate     : {pct_censored:.4f}")
    lines.append("")

    lines.append("observation_status distribution")
    lines.append("-" * 60)
    vc = df["observation_status"].value_counts()
    for k in ("defaulted", "closed", "censored"):
        lines.append(f"  {k:<10} : {int(vc.get(k, 0)):,}")
    lines.append("")

    lines.append("Target (train set)")
    lines.append("-" * 60)
    if len(train) > 0:
        n_def = int((train["default_flag"] == 1).sum())
        n_good = int((train["default_flag"] == 0).sum())
        rate = n_def / len(train)
        lines.append(f"  default_flag=1 : {n_def:,}")
        lines.append(f"  default_flag=0 : {n_good:,}")
        lines.append(f"  default rate   : {rate:.4f}")
    else:
        lines.append("  WARNING: train set empty")
    lines.append("")

    lines.append("Economics on defaulted accounts")
    lines.append("-" * 60)
    if len(defaulted) > 0:
        ead_d = defaulted["ead"].astype(float)
        lgd_d = defaulted["lgd"].astype(float)
        lines.append(
            f"  ead  min / mean / max : "
            f"{ead_d.min():,.0f} / {ead_d.mean():,.1f} / {ead_d.max():,.0f}"
        )
        lines.append(
            f"  lgd  min / mean / max : "
            f"{lgd_d.min():.4f} / {lgd_d.mean():.4f} / {lgd_d.max():.4f}"
        )
    else:
        lines.append("  WARNING: no defaulted rows")
    lines.append("")

    lines.append("Data quality — missing values")
    lines.append("-" * 60)
    # Expected nulls per spec:
    expected_nulls = {
        "default_flag": len(oot),
        "period_terminal": len(oot),
        "lgd": len(df) - len(defaulted),
    }
    nulls = df.isna().sum()
    nulls = nulls[nulls > 0]
    unexpected = []
    for col in df.columns:
        n = int(nulls.get(col, 0))
        if n == 0:
            continue
        exp = expected_nulls.get(col, 0)
        if n > exp:
            unexpected.append((col, n, exp))
    for col, n in sorted(expected_nulls.items()):
        actual = int(nulls.get(col, 0))
        lines.append(f"  {col:<20} : {actual:,} null (expected {n:,})")
    if unexpected:
        for col, n, exp in unexpected:
            lines.append(f"  WARN: {col} has {n:,} nulls; expected {exp:,}")
    else:
        lines.append("  no unexpected nulls")
    lines.append("")

    lines.append("Known redundancies (kept intentionally — sanity check)")
    lines.append("-" * 60)
    pairs = [
        ("app_loan_amount", "loan_amount"),
        ("app_n_installments", "n_installments"),
    ]
    for a, b in pairs:
        if a in df.columns and b in df.columns:
            equal = bool((df[a] == df[b]).all())
            lines.append(f"  {a} == {b} : {'OK' if equal else 'MISMATCH'}")
    # app_nom_branch ↔ branch: branch not kept separately in final schema
    lines.append("  app_nom_branch ↔ branch : branch not retained post-join")
    lines.append("")

    lines.append(f"Schema: {len(df.columns)} columns, in order:")
    lines.append("-" * 60)
    for i, c in enumerate(df.columns, 1):
        lines.append(f"  {i:2d}. {c}")

    return "\n".join(lines) + "\n"


# -- Main --------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Simulator run directory (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    data_dir: Path = args.data_dir.resolve()
    output_dir: Path = args.output_dir.resolve()

    log(f"data_dir   : {data_dir}")
    log(f"output_dir : {output_dir}")

    if not data_dir.exists():
        log(f"ERROR: data_dir does not exist: {data_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    features = load_origination_features(data_dir)
    accounts = load_accounts(data_dir)
    target = build_target(data_dir)

    log("Joining features + accounts + target on aid")
    df = features.merge(accounts, on="aid", how="left")
    df = df.merge(target, on="aid", how="left")
    log(f"  joined shape: {df.shape}")

    df = compute_economics(df)
    df = add_observation_and_split(df)

    log("Step 7: selecting final columns in order")
    missing = [c for c in FINAL_COLS if c not in df.columns]
    if missing:
        raise KeyError(f"Expected columns missing from joined frame: {missing}")
    df_final = df[FINAL_COLS].copy()

    csv_path = output_dir / "thesis_abt.csv"
    report_path = output_dir / "thesis_abt_report.txt"

    log(f"Writing {csv_path}")
    df_final.to_csv(csv_path, index=False)
    log(f"Writing {report_path}")
    report = build_report(df_final, data_dir, csv_path)
    report_path.write_text(report, encoding="utf-8")
    log("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
