"""
Phase 3 -- Score Calibration Experiment
=========================================
Generates scored OOT datasets at 4 Gini levels by injecting Gaussian noise
on the logit of the calibrated probabilities.

For each target Gini in [raw, 0.60, 0.45, 0.30]:
  - raw : copy predictions_oot_calibrated.parquet as-is
  - numeric:
      1. Binary-search sigma such that
         Gini(sigmoid(logit(prob_cal) + N(0,sigma^2))) ~= target
      2. Apply noise once with noise_random_state=42
      3. Re-calibrate via Platt on 80% OOT subsample (preserves mean calibration)
      4. Save predictions_gini_{target}.parquet

Run:
    python scripts/phase3_score_calibration.py
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

REPO_ROOT   = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "artifacts" / "phase3" / "run_config.json"
P3_DIR      = REPO_ROOT / "artifacts" / "phase3"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config():
    if not CONFIG_PATH.exists():
        sys.exit(f"ERROR: run_config.json not found. Run phase3_config.py first.")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def gini(y_true, y_score):
    return 2.0 * roc_auc_score(y_true, y_score) - 1.0


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def safe_logit(p, eps=1e-7):
    """Logit with clipping to avoid log(0)."""
    p = np.clip(p, eps, 1.0 - eps)
    return np.log(p / (1.0 - p))


def apply_noise(logits, sigma, rng_state=42):
    """Add N(0, sigma^2) noise to logits using a fixed RNG state."""
    rng = np.random.RandomState(rng_state)
    return logits + rng.normal(0.0, sigma, size=len(logits))


def binary_search_sigma(logits, y_true, target_gini,
                        sigma_min, sigma_max, tol, max_iter,
                        noise_rng=42):
    """
    Find sigma such that Gini(sigmoid(logits + N(0,sigma^2))) ~= target_gini.
    Uses a fixed noise seed for determinism: same sigma -> same Gini.
    """
    # Quick bounds check
    g_at_min = gini(y_true, sigmoid(apply_noise(logits, sigma_min, noise_rng)))
    g_at_max = gini(y_true, sigmoid(apply_noise(logits, sigma_max, noise_rng)))

    if target_gini > g_at_min:
        print(f"    WARNING: target Gini {target_gini:.3f} > Gini at sigma=0 "
              f"({g_at_min:.4f}). Cannot increase Gini via noise. "
              f"Returning sigma=0.")
        return 0.0, g_at_min

    if target_gini < g_at_max:
        print(f"    WARNING: target Gini {target_gini:.3f} < Gini at "
              f"sigma_max={sigma_max} ({g_at_max:.4f}). "
              f"Increase sigma_max. Returning sigma_max.")
        return sigma_max, g_at_max

    lo, hi = sigma_min, sigma_max
    for i in range(max_iter):
        mid = 0.5 * (lo + hi)
        g   = gini(y_true, sigmoid(apply_noise(logits, mid, noise_rng)))
        if abs(g - target_gini) < tol:
            print(f"    converged at iter {i+1}: sigma={mid:.4f} "
                  f"achieved Gini={g:.4f} (target={target_gini:.3f})")
            return mid, g
        # Gini decreases as sigma increases
        if g > target_gini:
            lo = mid    # need more noise
        else:
            hi = mid    # too much noise
    # Return best estimate
    mid = 0.5 * (lo + hi)
    g   = gini(y_true, sigmoid(apply_noise(logits, mid, noise_rng)))
    print(f"    max_iter reached: sigma={mid:.4f} achieved Gini={g:.4f} "
          f"(target={target_gini:.3f})")
    return mid, g


def platt_recalibrate(prob_noisy, y_true, rng_seed=42):
    """
    Fit a Platt calibrator on 80% of (prob_noisy, y_true) and apply to all.
    Returns calibrated probabilities for every row.
    """
    n = len(prob_noisy)
    # Stratified 80/20 split
    idx_all = np.arange(n)
    idx_fit, _ = train_test_split(
        idx_all,
        test_size=0.20,
        stratify=y_true,
        random_state=rng_seed,
    )
    platt = LogisticRegression(
        solver="lbfgs", max_iter=1000, random_state=rng_seed
    )
    platt.fit(
        prob_noisy[idx_fit].reshape(-1, 1),
        y_true[idx_fit],
    )
    prob_cal = platt.predict_proba(prob_noisy.reshape(-1, 1))[:, 1]
    return prob_cal, platt


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cfg      = load_config()
    sc_cfg   = cfg["score_calibration_experiment"]
    ss_cfg   = sc_cfg["sigma_search"]
    targets  = sc_cfg["target_ginis"]      # e.g. ["raw", 0.60, 0.45, 0.30]
    noise_rng = int(sc_cfg["noise_random_state"])

    np.random.seed(cfg["reproducibility"]["global_seed"])

    # Load calibrated OOT predictions
    cal_path = P3_DIR / "predictions_oot_calibrated.parquet"
    if not cal_path.exists():
        sys.exit(f"ERROR: {cal_path} not found. Run phase3_build_pd_model.py first.")

    df = pd.read_parquet(cal_path)
    print(f"[score_cal] loaded {len(df):,} OOT rows")

    y_true      = df["y_true"].values.astype(int)
    prob_cal    = df["prob_calibrated"].values.astype(float)
    logits_cal  = safe_logit(prob_cal)

    log_entries = {}

    for target in targets:
        label = "raw" if target == "raw" else f"{target:.2f}"
        print(f"\n[score_cal] target Gini = {label}")

        if target == "raw":
            # Pass-through: copy calibrated parquet as-is
            df_out = df.copy()
            achieved_gini = gini(y_true, prob_cal)
            mean_pred     = float(prob_cal.mean())
            mean_actual   = float(y_true.mean())
            brier         = float(brier_score_loss(y_true, prob_cal))
            entry = {
                "target_gini":   "raw",
                "sigma":         0.0,
                "achieved_gini": round(achieved_gini, 6),
                "mean_pred":     round(mean_pred, 6),
                "mean_actual":   round(mean_actual, 6),
                "brier_score":   round(brier, 6),
                "warnings":      [],
            }
        else:
            # Binary search sigma
            print(f"  binary search sigma in "
                  f"[{ss_cfg['sigma_min']}, {ss_cfg['sigma_max']}] ...")
            sigma, ach_before_recal = binary_search_sigma(
                logits_cal, y_true,
                target_gini=float(target),
                sigma_min=float(ss_cfg["sigma_min"]),
                sigma_max=float(ss_cfg["sigma_max"]),
                tol=float(ss_cfg["tol"]),
                max_iter=int(ss_cfg["max_iter"]),
                noise_rng=noise_rng,
            )

            # Apply noise once with fixed seed
            logits_noisy = apply_noise(logits_cal, sigma, noise_rng)
            prob_noisy   = sigmoid(logits_noisy).astype(np.float32)

            # Platt re-calibration on OOT subsample
            print(f"  re-calibrating after noise (sigma={sigma:.4f}) ...")
            prob_final, platt = platt_recalibrate(prob_noisy, y_true, noise_rng)
            prob_final = prob_final.astype(np.float32)

            achieved_gini = gini(y_true, prob_final)
            mean_pred     = float(prob_final.mean())
            mean_actual   = float(y_true.mean())
            brier         = float(brier_score_loss(y_true, prob_final))

            print(f"  achieved Gini (post recal): {achieved_gini:.4f}  "
                  f"mean_pred={mean_pred:.4f}  mean_actual={mean_actual:.4f}")

            w_list = []
            if abs(achieved_gini - float(target)) > 0.01:
                msg = (f"WARNING: achieved Gini {achieved_gini:.4f} deviates "
                       f"from target {target:.2f} by more than 0.01.")
                print(f"  {msg}")
                w_list.append(msg)
            if abs(mean_pred - mean_actual) > 0.005:
                msg = (f"WARNING: mean predicted {mean_pred:.4f} deviates "
                       f"from mean actual {mean_actual:.4f} by "
                       f"{abs(mean_pred-mean_actual)*100:.2f}pp (>0.5pp).")
                print(f"  {msg}")
                w_list.append(msg)

            # Build output dataframe (replace prob_calibrated with noise version)
            df_out = df.drop(columns=["prob_calibrated"]).copy()
            df_out["prob_calibrated"] = prob_final

            entry = {
                "target_gini":           float(target),
                "sigma":                 round(sigma, 6),
                "gini_before_recal":     round(float(ach_before_recal), 6),
                "achieved_gini":         round(achieved_gini, 6),
                "mean_pred":             round(mean_pred, 6),
                "mean_actual":           round(mean_actual, 6),
                "brier_score":           round(brier, 6),
                "platt_coef":            round(float(platt.coef_[0][0]), 6),
                "platt_intercept":       round(float(platt.intercept_[0]), 6),
                "warnings":              w_list,
            }

        log_entries[label] = entry

        out_name = f"predictions_gini_{label}.parquet"
        df_out.to_parquet(P3_DIR / out_name, index=False)
        print(f"  saved: {out_name}")

    # Save calibration log
    log_path = P3_DIR / "calibration_experiment_log.json"
    log_path.write_text(json.dumps(log_entries, indent=2), encoding="utf-8")
    print(f"\n[score_cal] log saved: {log_path}")
    print("[score_cal] DONE")


if __name__ == "__main__":
    main()
