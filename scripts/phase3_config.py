"""
Phase 3 -- Config Generator
============================
Generates artifacts/phase3/run_config.json with all experiment assumptions.
All downstream Phase 3 scripts read paths and parameters from this config.

Run:
    python scripts/phase3_config.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO_ROOT   = Path(__file__).resolve().parents[1]
ABT_CSV     = REPO_ROOT / "artifacts" / "thesis_wide_abt_12m_500c_clean" / "thesis_wide_abt.csv"
OUT_DIR     = REPO_ROOT / "artifacts" / "phase3"
OUT_PATH    = OUT_DIR / "run_config.json"


def generate_config() -> dict:
    # Read only the two small columns needed for month discovery.
    print("[config] reading fin_period/split from ABT ...")
    df_meta = pd.read_csv(
        ABT_CSV,
        usecols=["fin_period", "split"],
        dtype={"fin_period": int, "split": str},
    )
    train_months = sorted(
        df_meta.loc[df_meta["split"] == "train", "fin_period"]
               .dropna().unique().tolist()
    )
    oot_months = sorted(
        df_meta.loc[df_meta["split"] == "oot", "fin_period"]
               .dropna().unique().tolist()
    )
    print(f"[config]   train months ({len(train_months)}): "
          f"{train_months[0]} .. {train_months[-1]}")
    print(f"[config]   oot   months ({len(oot_months)}):   "
          f"{oot_months[0]} .. {oot_months[-1]}")

    config = {
        "data": {
            "abt_path": (ABT_CSV).relative_to(REPO_ROOT).as_posix(),
            "train_months": [str(m) for m in train_months],
            "oot_months":   [str(m) for m in oot_months],
            "population_filter": "n_installments != 12",
        },
        "features": {
            "numeric": [
                "app_income",
                "app_number_of_children",
                "app_spendings",
                "act_age",
            ],
            "categorical": [
                "app_nom_gender",
                "app_nom_marital_status",
                "app_nom_home_status",
                "app_nom_cars",
                "app_nom_job_code",
            ],
        },
        "pd_model": {
            "algorithm": "LogisticRegression",
            "params": {
                "max_iter":      1000,
                "class_weight":  "balanced",
                "random_state":  42,
            },
            "imputation": {"numeric": "median", "categorical": "mode"},
        },
        "calibration": {
            "method":           "platt_scaling",
            "holdout_fraction": 0.2,
            "random_state":     42,
        },
        "score_calibration_experiment": {
            "method":        "gaussian_noise_on_logit",
            "target_ginis":  ["raw", 0.60, 0.45, 0.30],
            "sigma_search": {
                "method":    "binary_search",
                "tol":       0.005,
                "max_iter":  50,
                "sigma_min": 0.0,
                "sigma_max": 20.0,
            },
            "noise_random_state": 42,
        },
        "profit": {
            "formula": (
                "expected_revenue = (1-PD)*APR*EAD*duration_years; "
                "expected_loss = PD*LGD*EAD"
            ),
            "ead_definition":        "loan_amount_at_origination",
            "duration_years_formula": "n_installments / 12",
            "apr": {
                "base":        0.20,
                "sensitivity": [0.15, 0.20, 0.25, 0.30],
            },
            "lgd": {
                "base":        0.75,
                "sensitivity": [0.60, 0.75, 0.90],
            },
        },
        "cutoff_optimization": {
            "accuracy_criterion": "youdens_j",
            "profit_criterion":   "argmax_expected_profit",
            "threshold_grid": {
                "start": 0.01,
                "stop":  0.99,
                "step":  0.01,
            },
        },
        "reproducibility": {"global_seed": 42},
    }
    return config


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    config = generate_config()
    OUT_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"[config] saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
