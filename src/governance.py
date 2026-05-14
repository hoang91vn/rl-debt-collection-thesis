"""
Governance helpers for Phase 2 PD model selection.

Filters the feature catalog produced by phase1_5_feature_factory according to
the v5 prompt acceptance contract:
  - allowed_for_origination_pd == True
  - leakage_risk != 'high'
  - uses_target == False
  - uses_future_behavior == False

Plus defensive validators for score/scorem absence and loan-term exclusion.
"""
from __future__ import annotations
from typing import List, Sequence
import pandas as pd

# Hard-coded loan-term column markers used by validate_no_loan_term_in_pd().
# Any feature whose source_columns mention one of these must NOT have
# allowed_for_origination_pd=True.
LOAN_TERM_MARKERS = ("loan_amount", "n_installments", "installment", "principal", "term", "tenor")

# ID/target/split/meta columns kept alongside features for downstream joins.
META_COLUMNS_DEFAULT = ["default_flag_12m", "split", "aid", "fin_period"]


def filter_pd_eligible(catalog: pd.DataFrame) -> List[str]:
    """Return feature names that pass the origination-PD eligibility filter.

    A feature is PD-eligible iff:
      allowed_for_origination_pd == True
      AND leakage_risk != 'high'
      AND uses_target == False
      AND uses_future_behavior == False
    """
    required = {
        "feature_name",
        "allowed_for_origination_pd",
        "leakage_risk",
        "uses_target",
        "uses_future_behavior",
    }
    missing = required - set(catalog.columns)
    if missing:
        raise ValueError(f"catalog missing required columns: {missing}")

    mask = (
        (catalog["allowed_for_origination_pd"] == True)
        & (catalog["leakage_risk"] != "high")
        & (catalog["uses_target"] == False)
        & (catalog["uses_future_behavior"] == False)
    )
    return catalog.loc[mask, "feature_name"].tolist()


def validate_no_score_columns(df: pd.DataFrame) -> bool:
    """Return True iff no column is the simulator's tautological 'score' or 'scorem'.

    Note: synthetic bureau-like features (synth_bureau_score_*) are allowed
    because they are built from safe app vars + noise, not from the simulator's
    score column.
    """
    forbidden = {"score", "scorem"}
    present = [c for c in df.columns if c.lower() in forbidden]
    return len(present) == 0


def validate_no_loan_term_in_pd(df: pd.DataFrame, catalog: pd.DataFrame) -> bool:
    """Return True iff no PD-eligible feature is sourced from a loan term.

    Cross-checks: any feature in `df.columns` that is also marked
    allowed_for_origination_pd=True must NOT have a loan-term marker in
    source_columns. Excludes synth_* features (they intentionally compose
    synthetic balances/limits and are NOT real loan-term derivatives).
    """
    pd_eligible = set(filter_pd_eligible(catalog))
    df_cols = set(df.columns)
    eligible_in_df = pd_eligible & df_cols

    cat_idx = catalog.set_index("feature_name")
    violations: List[str] = []
    for f in eligible_in_df:
        if f.startswith("synth_"):
            continue
        sources = str(cat_idx.at[f, "source_columns"] or "").lower()
        for marker in LOAN_TERM_MARKERS:
            # Word-ish boundary to avoid matching 'app_n_installments' substring
            # in a noise feature accidentally; the catalog's source_columns is
            # comma-delimited so use simple contains.
            if marker in sources and not f.startswith("synth_"):
                violations.append(f)
                break
    return len(violations) == 0


def get_meta_columns() -> List[str]:
    """Return the list of meta columns to keep alongside features."""
    return list(META_COLUMNS_DEFAULT)


def summarise_eligible_pool(catalog: pd.DataFrame) -> pd.DataFrame:
    """Return per-family count of PD-eligible features (diagnostic only)."""
    mask = (
        (catalog["allowed_for_origination_pd"] == True)
        & (catalog["leakage_risk"] != "high")
        & (catalog["uses_target"] == False)
        & (catalog["uses_future_behavior"] == False)
    )
    return (
        catalog.loc[mask, "feature_family"]
        .value_counts()
        .rename_axis("feature_family")
        .reset_index(name="pd_eligible_count")
    )
