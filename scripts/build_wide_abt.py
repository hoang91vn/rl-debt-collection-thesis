#!/usr/bin/env python3
"""Build thesis_wide_abt.csv for profit-driven credit scoring analysis.

One row per eligible aid.  Features = origination snapshot + behavioral
history flattened across months 1-12 (fin_period .. fin_period+11) +
aggregate features + summary_abt rolling stats at obs_period.
Target = WRITE_OFF in months 13-24 after origination.

Reads from a simulator run directory:
  abt_base_*.csv      (all period files)
  summary_abt_*.csv   (one per period, contains rolling aggregate columns)
  accounts.csv
  transactions.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DATA_DIR   = Path("examples/thesis_baseline/runs/thesis_baseline")
DEFAULT_OUTPUT_DIR = Path("artifacts/thesis_wide_abt_12m_500c_clean")

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

ORIG_COLS = ["act_age", "installment", "n_installments", "loan_amount"]

BEHAV_BASE = [
    "act_due",
    "act_paid_installments",
    "act_utl",
    "act_dueutl",
    "act_cc",
    "act_dueinc",
    "act_days",
    "act_loaninc",
    "coll_status",
]
CUS_BASE = [
    "act_cus_seniority",
    "act_cus_n_loans_hist",
    "act_cus_n_statC",
    "act_cus_n_statB",
    "act_cus_n_loans_act",
    "act_cus_utl",
    "act_cus_dueutl",
    "act_cus_cc",
]

MONTHS     = list(range(1, 13))          # months 1-12
BEHAV_FLAT = [f"{c}_m{m}" for c in BEHAV_BASE for m in MONTHS]
CUS_FLAT   = [f"{c}_m{m}" for c in CUS_BASE   for m in MONTHS]

AGG_COLS = [
    "max_due",
    "max_coll_status",
    "trend_due",
    "months_ever_due",
    "months_coll_2plus",
    "paid_fraction_at_obs",
]

# Rolling stats extracted from summary_abt_{obs_period}.csv
# ags6_*/ags12_* may be NaN for short-history accounts — rows are kept as-is.
SUMMARY_PREFIXES = ("agr6_", "ags6_", "agr12_", "ags12_")
_SUMMARY_SUFFIXES = [
    "Mean_Due",       "Max_Due",       "Min_Due",
    "Mean_Days",      "Max_Days",      "Min_Days",
    "Mean_CMax_Days", "Max_CMax_Days", "Min_CMax_Days",
    "Mean_CMax_Due",  "Max_CMax_Due",  "Min_CMax_Due",
]
SUMMARY_AGG_COLS = [
    f"{p}{s}" for p in SUMMARY_PREFIXES for s in _SUMMARY_SUFFIXES
]  # 4 x 12 = 48 columns

TARGET_COL = ["default_flag_12m"]
META_COLS  = ["observation_status", "split", "obs_period"]

FINAL_COLS = (
    ID_COLS
    + APP_COLS
    + ORIG_COLS
    + BEHAV_FLAT
    + CUS_FLAT
    + AGG_COLS
    + SUMMARY_AGG_COLS
    + TARGET_COL
    + META_COLS
)

# ---------------------------------------------------------------------------
# Cleaning constants (Step 8 — applied after FINAL_COLS selection)
# ---------------------------------------------------------------------------

# 8A: Constant columns — zero variance, all single-loan simulator artifacts
DROP_CONSTANT: list[str] = (
    # Origination-month constants: loan just started, nothing due/paid/utilised (8)
    ["act_due_m1", "act_paid_installments_m1", "act_utl_m1",
     "act_dueutl_m1", "act_dueinc_m1", "act_days_m1",
     "coll_status_m1", "act_cus_seniority_m1"]
    # Deterministic counter 1,2,...,12 — every account is its own first loan (12)
    + [f"act_cus_n_loans_hist_m{m}" for m in range(1, 13)]
    # Always 0 — no prior charge-offs in single-loan simulator (12)
    + [f"act_cus_n_statC_m{m}" for m in range(1, 13)]
    # Always 0 — no prior restructurings in single-loan simulator (12)
    + [f"act_cus_n_statB_m{m}" for m in range(1, 13)]
    # Deterministic active-loans counter mirrors n_loans_hist (12)
    + [f"act_cus_n_loans_act_m{m}" for m in range(1, 13)]
    # Always 0 at origination (1)
    + ["act_cus_dueutl_m1"]
    # Negative seniority constants m7..m12: -6,-7,...,-11 for all rows (6)
    + [f"act_cus_seniority_m{m}" for m in range(7, 13)]
)  # total: 8 + 12*4 + 1 + 6 = 63

# 8B: Sparse / near-zero summary_abt columns
DROP_SPARSE: list[str] = (
    # ags6_*  — 83.9% NaN (need 6+ months pre-obs history per account)
    [f"ags6_{s}"  for s in _SUMMARY_SUFFIXES]
    # ags12_* — 96.2% NaN (need 12+ months pre-obs history per account)
    + [f"ags12_{s}" for s in _SUMMARY_SUFFIXES]
    # 99.4% zeros — minimum rolling due almost always 0
    + ["agr12_Min_Due", "agr12_Min_CMax_Due"]
)  # total: 12 + 12 + 2 = 26

# 8C: Winsorise at 99th percentile (train-fit, applied to all)
WINSOR_COLS: list[str] = [f"act_dueinc_m{m}" for m in range(4, 13)]  # 9 cols

# 8D: Impute NaN with train median
# agr6_ x12  +  agr12_ x10  (excl. agr12_Min_Due, agr12_Min_CMax_Due dropped in 8B)
_DROPPED_AGR12 = {"agr12_Min_Due", "agr12_Min_CMax_Due"}
AGR_IMPUTE_COLS: list[str] = (
    [f"agr6_{s}"  for s in _SUMMARY_SUFFIXES]
    + [f"agr12_{s}" for s in _SUMMARY_SUFFIXES
       if f"agr12_{s}" not in _DROPPED_AGR12]
)  # 12 + 10 = 22


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[build_wide_abt] {msg}", flush=True)


def to_month_num(x: pd.Series | int) -> pd.Series | int:
    """Convert YYYYMM to a linear month count (2024*12+5 = 24293 for 202405)."""
    return (x // 100) * 12 + (x % 100)


def yyyymm_add_series(period: pd.Series, months: int) -> pd.Series:
    """Vectorised YYYYMM + N months -> YYYYMM.  Handles year roll-over."""
    total = (period // 100) * 12 + (period % 100) - 1 + months
    return (total // 12) * 100 + (total % 12) + 1


# ---------------------------------------------------------------------------
# Step 1 — Load data
# ---------------------------------------------------------------------------

def load_abt_base(data_dir: Path) -> pd.DataFrame:
    """Load all abt_base files, keeping only rows in the behavioral window
    (month offset 0-11 relative to fin_period of each account)."""
    abt_files = sorted(data_dir.glob("abt_base_*.csv"))
    if not abt_files:
        raise FileNotFoundError(f"No abt_base_*.csv files in {data_dir}")
    log(f"Step 1a: loading {len(abt_files)} abt_base files (behavioral window only)")
    frames = []
    for f in abt_files:
        df = pd.read_csv(f)
        fin_m  = to_month_num(df["fin_period"])
        per_m  = to_month_num(df["period"])
        offset = per_m - fin_m
        mask   = (offset >= 0) & (offset <= 11)
        df     = df[mask].copy()
        df["_offset"] = offset[mask].values
        frames.append(df)
    abt = pd.concat(frames, ignore_index=True)
    log(f"  behavioral rows loaded: {len(abt):,}")
    return abt


def load_accounts(data_dir: Path) -> pd.DataFrame:
    """Load accounts.csv, drop duplicate aid column (known simulator bug)."""
    log("Step 1b: loading accounts.csv")
    df = pd.read_csv(data_dir / "accounts.csv")
    if "aid.1" in df.columns:
        df = df.drop(columns=["aid.1"])
    keep = ["aid", "installment", "n_installments", "loan_amount"]
    log(f"  {len(df):,} account rows")
    return df[keep]


def load_transactions(data_dir: Path) -> pd.DataFrame:
    """Load transactions.csv."""
    log("Step 1c: loading transactions.csv")
    tx = pd.read_csv(data_dir / "transactions.csv")
    log(f"  {len(tx):,} transaction rows")
    return tx


# ---------------------------------------------------------------------------
# Step 2 — Origination snapshot (month 0)
# ---------------------------------------------------------------------------

def build_origination(abt: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Extract one origination row per aid (period == fin_period, offset == 0)
    and join loan-level columns from accounts.csv."""
    log("Step 2: building origination snapshot (offset == 0)")
    orig = abt[abt["_offset"] == 0].copy()
    orig = orig.drop_duplicates(subset=["aid"], keep="first")
    orig = orig.merge(accounts, on="aid", how="left")
    log(f"  {len(orig):,} aids with origination row")
    return orig


# ---------------------------------------------------------------------------
# Step 3 — Eligibility filter
# ---------------------------------------------------------------------------

def compute_eligibility(
    abt: pd.DataFrame,
    orig: pd.DataFrame,
    tx: pd.DataFrame,
) -> tuple[set[str], pd.DataFrame]:
    """Return (eligible_aids, drop_summary).

    Check A: abt_base must have all 12 behavioral offsets (0-11).
    Check B: no WRITE_OFF (coll_status==8) at period <= obs_period
             (obs_period = fin_period + 12 months, offset 12).
    """
    log("Step 3: eligibility filter")
    total = len(orig)

    # --- Check A: full 12-month behavioral history ---
    counts = abt.groupby("aid")["_offset"].nunique()
    pass_a = set(counts[counts == 12].index)
    fail_a = set(orig["aid"]) - pass_a
    log(f"  Check A -- full 12-month history : {len(pass_a):,} pass, {len(fail_a):,} fail")

    # --- Check B: no early WRITE_OFF (at or before obs_period = offset 12) ---
    fin_period_map = orig.set_index("aid")["fin_period"]
    tx_a = tx[tx["aid"].isin(pass_a)].copy()
    tx_a["_fin_month"] = to_month_num(tx_a["aid"].map(fin_period_map))
    tx_a["_per_month"] = to_month_num(tx_a["period"])
    tx_a["_offset"]    = tx_a["_per_month"] - tx_a["_fin_month"]
    early_wo_aids = set(
        tx_a.loc[
            (tx_a["coll_status"] == 8) & (tx_a["_offset"] <= 12), "aid"
        ].unique()
    )
    fail_b = early_wo_aids
    log(f"  Check B -- early WRITE_OFF       : {len(fail_b):,} fail")

    eligible = pass_a - fail_b
    log(f"  Eligible : {len(eligible):,} / {total:,} total aids")

    drop_summary = pd.DataFrame([{
        "total_aids":                  total,
        "fail_a_insufficient_history": len(fail_a),
        "fail_b_early_default":        len(fail_b),
        "eligible":                    len(eligible),
    }])
    return eligible, drop_summary


# ---------------------------------------------------------------------------
# Step 4 — Flatten behavioral features (months 1-12)
# ---------------------------------------------------------------------------

def flatten_behavioral(abt: pd.DataFrame, eligible: set[str]) -> pd.DataFrame:
    """Pivot BEHAV_BASE + CUS_BASE columns across months 1-12 for eligible aids."""
    log("Step 4: flattening behavioral features (months 1-12)")
    beh = abt[abt["aid"].isin(eligible)].copy()
    beh["m"] = beh["_offset"] + 1   # 1-indexed

    all_base_cols  = BEHAV_BASE + CUS_BASE
    pivot_frames: list[pd.DataFrame] = []
    for col in all_base_cols:
        piv = beh.pivot_table(
            index="aid", columns="m", values=col, aggfunc="first"
        )
        piv.columns = [f"{col}_m{int(c)}" for c in piv.columns]
        pivot_frames.append(piv)

    wide = pd.concat(pivot_frames, axis=1).reset_index()
    log(f"  behavioral pivot: {wide.shape[0]:,} aids x {wide.shape[1] - 1} feature columns")
    return wide


# ---------------------------------------------------------------------------
# Step 5 — Aggregate features
# ---------------------------------------------------------------------------

def compute_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Compute 6 aggregate features from the flattened behavioral columns."""
    log("Step 5: computing aggregate features")
    due_cols = [f"act_due_m{m}"     for m in MONTHS]
    cs_cols  = [f"coll_status_m{m}" for m in MONTHS]

    df["max_due"]              = df[due_cols].max(axis=1)
    df["max_coll_status"]      = df[cs_cols].max(axis=1)
    df["trend_due"]            = df["act_due_m12"] - df["act_due_m1"]
    df["months_ever_due"]      = (df[due_cols] > 0).sum(axis=1).astype(int)
    df["months_coll_2plus"]    = (df[cs_cols] >= 2).sum(axis=1).astype(int)
    df["paid_fraction_at_obs"] = (
        df["act_paid_installments_m12"] / df["n_installments"]
    )
    return df


# ---------------------------------------------------------------------------
# Step 6 — 12-month default target
# ---------------------------------------------------------------------------

def build_target(tx: pd.DataFrame, aids_df: pd.DataFrame) -> pd.DataFrame:
    """Assign default_flag_12m in {1, 0, NaN}.

    Target window: months 13-24 after origination (offsets 12-23 from fin_period).
    - 1  : WRITE_OFF (coll_status==8) found in window.
    - 0  : No WRITE_OFF AND target window fully covered by simulation.
    - NaN: Censored (simulation ended before fin_period+23).
    """
    log("Step 6: building 12-month default target")
    sim_last_period = int(tx["period"].max())
    sim_last_month  = to_month_num(sim_last_period)
    log(f"  simulation last period: {sim_last_period}")

    aids_df = aids_df.copy()
    aids_df["_fin_month"]        = to_month_num(aids_df["fin_period"])
    aids_df["_target_end_month"] = aids_df["_fin_month"] + 23
    aids_df["_is_covered"]       = aids_df["_target_end_month"] <= sim_last_month

    tx_e = tx[tx["aid"].isin(aids_df["aid"])].copy()
    tx_e = tx_e.merge(aids_df[["aid", "_fin_month"]], on="aid", how="left")
    tx_e["_per_month"] = to_month_num(tx_e["period"])
    tx_e["_offset"]    = tx_e["_per_month"] - tx_e["_fin_month"]

    wo_in_window = set(
        tx_e.loc[
            (tx_e["coll_status"] == 8) & tx_e["_offset"].between(12, 23), "aid"
        ].unique()
    )
    log(f"  WRITE_OFFs in target window (months 13-24): {len(wo_in_window):,}")

    aids_df["default_flag_12m"] = pd.array([pd.NA] * len(aids_df), dtype="Int64")
    aids_df.loc[aids_df["aid"].isin(wo_in_window), "default_flag_12m"] = 1
    no_wo_covered = ~aids_df["aid"].isin(wo_in_window) & aids_df["_is_covered"]
    aids_df.loc[no_wo_covered, "default_flag_12m"] = 0

    n1  = int((aids_df["default_flag_12m"] == 1).sum())
    n0  = int((aids_df["default_flag_12m"] == 0).sum())
    nna = int(aids_df["default_flag_12m"].isna().sum())
    log(f"  default=1: {n1:,} | default=0: {n0:,} | censored (NaN): {nna:,}")

    return aids_df[["aid", "default_flag_12m"]]


# ---------------------------------------------------------------------------
# Step 7 — Observation status, split, obs_period
# ---------------------------------------------------------------------------

def add_obs_and_split(df: pd.DataFrame) -> pd.DataFrame:
    """Add observation_status in {defaulted, closed, censored},
    split in {train, oot}, and obs_period = fin_period + 12 months."""
    log("Step 7: adding observation_status, split, obs_period")

    obs = pd.Series("censored", index=df.index, dtype="object")
    has_target = df["default_flag_12m"].notna()
    obs.loc[has_target & (df["default_flag_12m"] == 1)] = "defaulted"
    obs.loc[has_target & (df["default_flag_12m"] == 0)] = "closed"
    df["observation_status"] = obs

    df["split"] = obs.map({"defaulted": "train", "closed": "train", "censored": "oot"})

    df["obs_period"] = yyyymm_add_series(df["fin_period"], 12).astype(int)
    return df


# ---------------------------------------------------------------------------
# Step 7b — summary_abt rolling stats at obs_period
# ---------------------------------------------------------------------------

def load_summary_abt_stats(data_dir: Path, obs_periods: list[int]) -> pd.DataFrame:
    """Read summary_abt_{obs_period}.csv for each unique obs_period and extract
    rolling aggregate columns (agr6_*, ags6_*, agr12_*, ags12_*).

    NaN values in ags6_*/ags12_* are retained — rows are never dropped.
    Returns DataFrame with columns: aid + all matched rolling-stat columns.
    """
    log("Step 7b: loading summary_abt rolling stats at obs_period")
    frames: list[pd.DataFrame] = []
    missing_periods: list[int] = []

    for period in sorted(set(obs_periods)):
        fpath = data_dir / f"summary_abt_{period}.csv"
        if not fpath.exists():
            log(f"  WARNING: {fpath.name} not found -- skipping period {period}")
            missing_periods.append(period)
            continue
        raw = pd.read_csv(fpath)
        agg_cols = [c for c in raw.columns if c.startswith(SUMMARY_PREFIXES)]
        frames.append(raw[["aid"] + agg_cols])
        log(f"  {fpath.name}: {len(raw):,} rows, {len(agg_cols)} rolling-stat cols")

    if not frames:
        raise FileNotFoundError(
            f"No summary_abt_*.csv found for any obs_period in: {sorted(set(obs_periods))}"
        )

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["aid"], keep="first")
    log(f"  combined: {len(combined):,} unique aids, {len(combined.columns) - 1} stat cols")

    if missing_periods:
        log(f"  WARNING: {len(missing_periods)} obs_period(s) had no file: {missing_periods}")

    return combined


# ---------------------------------------------------------------------------
# Step 8 — Data cleaning
# ---------------------------------------------------------------------------

def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply post-join cleaning steps 8A-8D.

    A) Drop 63 constant columns (single-loan simulator artifacts).
    B) Drop 26 sparse/near-zero summary_abt columns.
    C) Winsorise act_dueinc_m4..m12 at 99th pct — fit on train, apply to all.
    D) Impute 22 agr6_*/agr12_* NaN with train median — fit on train, apply to all.

    Returns (df_clean, clean_report) where clean_report contains drop lists,
    winsorise caps, and imputation medians for the report.
    """
    log("Step 8: data cleaning (drop / winsorise / impute)")
    train_mask = df["split"] == "train"
    report: dict = {}

    # 8A: Drop constant columns
    present_const = [c for c in DROP_CONSTANT if c in df.columns]
    absent_const  = [c for c in DROP_CONSTANT if c not in df.columns]
    df = df.drop(columns=present_const)
    report["dropped_constant"]        = present_const
    report["dropped_constant_absent"] = absent_const
    log(f"  8A: dropped {len(present_const)} constant cols"
        + (f" ({len(absent_const)} already absent)" if absent_const else ""))

    # 8B: Drop sparse / near-zero summary_abt columns
    present_sparse = [c for c in DROP_SPARSE if c in df.columns]
    absent_sparse  = [c for c in DROP_SPARSE if c not in df.columns]
    df = df.drop(columns=present_sparse)
    report["dropped_sparse"]        = present_sparse
    report["dropped_sparse_absent"] = absent_sparse
    log(f"  8B: dropped {len(present_sparse)} sparse cols"
        + (f" ({len(absent_sparse)} already absent)" if absent_sparse else ""))

    total_dropped = len(present_const) + len(present_sparse)
    log(f"  8A+8B total dropped: {total_dropped} cols")

    # 8C: Winsorise act_dueinc_m4..m12 at 99th pct (train-fit)
    winsor_caps: dict[str, float] = {}
    for col in WINSOR_COLS:
        if col not in df.columns:
            continue
        cap = float(df.loc[train_mask, col].quantile(0.99))
        winsor_caps[col] = cap
        df[col] = df[col].clip(upper=cap)
    report["winsor_caps"] = winsor_caps
    log(f"  8C: winsorised {len(winsor_caps)} act_dueinc cols at 99th pct (train-fit)")

    # 8D: Impute agr6_*/agr12_* NaN with train median
    impute_medians: dict[str, float] = {}
    for col in AGR_IMPUTE_COLS:
        if col not in df.columns:
            continue
        n_null = int(df[col].isna().sum())
        if n_null == 0:
            continue
        median = float(df.loc[train_mask, col].median())
        impute_medians[col] = median
        df[col] = df[col].fillna(median)
    report["impute_medians"] = impute_medians
    log(f"  8D: imputed {len(impute_medians)} agr cols with train median")

    log(f"  After cleaning: {df.shape[0]:,} rows x {df.shape[1]} cols")
    return df, report


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(
    df: pd.DataFrame,
    drop_summary: pd.DataFrame,
    run_dir: Path,
    csv_path: Path,
    clean_report: dict | None = None,
) -> str:
    train = df[df["split"] == "train"]
    oot   = df[df["split"] == "oot"]
    dr    = drop_summary.iloc[0]

    lines: list[str] = []
    lines.append("thesis_wide_abt report")
    lines.append("=" * 60)
    lines.append(f"Source run dir : {run_dir}")
    lines.append(f"Output CSV     : {csv_path}")
    lines.append("")

    # --- Eligibility ---
    lines.append("Eligibility filter")
    lines.append("-" * 60)
    lines.append(f"  Total aids (origination)           : {int(dr['total_aids']):,}")
    lines.append(f"  Dropped -- insufficient_history (A) : {int(dr['fail_a_insufficient_history']):,}")
    lines.append(f"  Dropped -- early_default (B)        : {int(dr['fail_b_early_default']):,}")
    lines.append(f"  Eligible (rows in wide ABT)        : {int(dr['eligible']):,}")
    lines.append("")

    # --- Cleaning summary ---
    if clean_report:
        lines.append("Cleaning summary (Step 8)")
        lines.append("-" * 60)
        n_const  = len(clean_report.get("dropped_constant", []))
        n_sparse = len(clean_report.get("dropped_sparse", []))
        lines.append(f"  8A dropped (constant cols)         : {n_const}")
        lines.append(f"  8B dropped (sparse/near-zero cols) : {n_sparse}")
        lines.append(f"  Total columns dropped              : {n_const + n_sparse}")
        lines.append("")

        lines.append("  8C Winsorise caps (99th pct, train-fit):")
        for col, cap in clean_report.get("winsor_caps", {}).items():
            lines.append(f"    {col:<30} cap = {cap:.6g}")
        lines.append("")

        lines.append("  8D Imputation medians (train-fit):")
        for col, med in clean_report.get("impute_medians", {}).items():
            lines.append(f"    {col:<40} median = {med:.6g}")
        lines.append("")

    # --- Split ---
    lines.append("Split counts")
    lines.append("-" * 60)
    lines.append(f"  train (terminated) : {len(train):,}")
    lines.append(f"  oot   (censored)   : {len(oot):,}")
    pct_cens = len(oot) / len(df) if len(df) else 0
    lines.append(f"  censoring rate     : {pct_cens:.4f}")
    lines.append("")

    # --- Observation status ---
    lines.append("observation_status distribution")
    lines.append("-" * 60)
    vc = df["observation_status"].value_counts()
    for k in ("defaulted", "closed", "censored"):
        lines.append(f"  {k:<10} : {int(vc.get(k, 0)):,}")
    lines.append("")

    # --- Target ---
    lines.append("Target -- default_flag_12m (train set)")
    lines.append("-" * 60)
    if len(train) > 0:
        n1   = int((train["default_flag_12m"] == 1).sum())
        n0   = int((train["default_flag_12m"] == 0).sum())
        rate = n1 / len(train)
        lines.append(f"  default_flag_12m=1 : {n1:,}")
        lines.append(f"  default_flag_12m=0 : {n0:,}")
        lines.append(f"  default rate       : {rate:.4f}")
    else:
        lines.append("  WARNING: train set empty")
    lines.append("")

    # --- Feature count (dynamic — reflects actual columns after cleaning) ---
    non_feature = set(ID_COLS + TARGET_COL + META_COLS)
    feature_cols = [c for c in df.columns if c not in non_feature]

    def _present(lst: list[str]) -> list[str]:
        return [c for c in lst if c in df.columns]

    orig_present  = _present(APP_COLS + ORIG_COLS)
    behav_present = _present(BEHAV_FLAT)
    cus_present   = _present(CUS_FLAT)
    agg_present   = _present(AGG_COLS)
    summ_present  = _present(SUMMARY_AGG_COLS)

    lines.append("Feature count")
    lines.append("-" * 60)
    lines.append(f"  Total columns         : {len(df.columns)}")
    lines.append(f"  IDs                   : {len(_present(ID_COLS))}")
    lines.append(f"  Target                : {len(_present(TARGET_COL))}")
    lines.append(f"  Meta                  : {len(_present(META_COLS))}")
    lines.append(f"  Feature columns       : {len(feature_cols)}")
    lines.append(f"    Origination         : {len(orig_present)}")
    lines.append(f"    Behavioral          : {len(behav_present)}")
    lines.append(f"    Customer            : {len(cus_present)}")
    lines.append(f"    Aggregates          : {len(agg_present)}")
    lines.append(f"    Summary_abt stats   : {len(summ_present)}")
    for pfx in SUMMARY_PREFIXES:
        n = sum(1 for c in summ_present if c.startswith(pfx))
        if n:
            lines.append(f"      {pfx:<10}      : {n}")
    lines.append("")

    # --- Null counts ---
    lines.append("Data quality -- null counts per column group")
    lines.append("-" * 60)
    nulls = df.isna().sum()
    groups = {
        "Origination": APP_COLS + ORIG_COLS,
        "Behavioral":  BEHAV_FLAT,
        "Customer":    CUS_FLAT,
        "Aggregates":  AGG_COLS,
        "Summary_abt": SUMMARY_AGG_COLS,
        "Target":      TARGET_COL,
        "Meta":        META_COLS,
    }
    unexpected: list[str] = []
    for grp, cols in groups.items():
        present = [c for c in cols if c in df.columns]
        if not present:
            continue
        n_nulls = int(nulls[present].sum())
        if grp == "Target":
            status = f"(expected {len(oot):,} for censored rows)"
        elif grp == "Summary_abt" and n_nulls > 0:
            status = "(expected -- agr6_/agr12_ imputed; ags dropped)"
        elif n_nulls == 0:
            status = "OK"
        else:
            status = f"WARN -- {n_nulls:,} unexpected"
            unexpected.append(grp)
        lines.append(f"  {grp:<15}: {n_nulls:>6,} nulls  {status}")

    lines.append("")
    if not unexpected:
        lines.append("  No unexpected nulls")
    lines.append("")

    # --- Schema ---
    lines.append(f"Schema: {len(df.columns)} columns, in order:")
    lines.append("-" * 60)
    for i, c in enumerate(df.columns, 1):
        lines.append(f"  {i:3d}. {c}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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

    data_dir:   Path = args.data_dir.resolve()
    output_dir: Path = args.output_dir.resolve()

    log(f"data_dir   : {data_dir}")
    log(f"output_dir : {output_dir}")

    if not data_dir.exists():
        log(f"ERROR: data_dir does not exist: {data_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load
    abt      = load_abt_base(data_dir)
    accounts = load_accounts(data_dir)
    tx       = load_transactions(data_dir)

    # 2. Origination snapshot
    orig = build_origination(abt, accounts)

    # 3. Eligibility
    eligible, drop_summary = compute_eligibility(abt, orig, tx)

    # 4. Flatten behavioral (months 1-12)
    behav_wide = flatten_behavioral(abt, eligible)

    # 5. Join origination + behavioral, compute aggregates
    orig_elig = orig[orig["aid"].isin(eligible)].copy()
    df = orig_elig.merge(behav_wide, on="aid", how="left")
    log(f"Joined origination + behavioral: {df.shape}")
    df = compute_aggregates(df)

    # 6. Target (months 13-24)
    target_df = build_target(tx, df[["aid", "fin_period"]])
    df = df.merge(target_df, on="aid", how="left")

    # 7. Obs status, split, obs_period
    df = add_obs_and_split(df)

    # 7b. summary_abt rolling stats at obs_period (left join -- NaN retained)
    obs_periods = df["obs_period"].dropna().astype(int).unique().tolist()
    summary_stats = load_summary_abt_stats(data_dir, obs_periods)
    df = df.merge(summary_stats, on="aid", how="left")
    log(f"After summary_abt join: {df.shape}")

    # 8a. Final column selection
    log("Step 8a: selecting final columns")
    missing = [c for c in FINAL_COLS if c not in df.columns]
    if missing:
        raise KeyError(f"Expected columns missing from DataFrame: {missing}")
    df_final = df[FINAL_COLS].copy()

    # 8b. Data cleaning (drop / winsorise / impute)
    df_final, clean_report = clean_dataset(df_final)

    csv_path    = output_dir / "thesis_wide_abt.csv"
    report_path = output_dir / "thesis_wide_abt_report.txt"

    log(f"Writing {csv_path}  ({len(df_final):,} rows x {len(df_final.columns)} cols)")
    df_final.to_csv(csv_path, index=False)

    report = build_report(df_final, drop_summary, data_dir, csv_path, clean_report)
    log(f"Writing {report_path}")
    report_path.write_text(report, encoding="utf-8")
    log("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
