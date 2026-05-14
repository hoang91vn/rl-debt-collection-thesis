"""
Calibration helpers for Phase 2A diagnostics + Phase 3 stress-test design.

Two responsibilities:

1. **Leak-free calibration** — fit Platt scaling and isotonic regression on a
   *calibration split carved from the training period* (NEVER OOT). The OOT
   set is reserved as the untouched holdout for final evaluation.

2. **Score-discrimination stress-test design** (Phase 3/4 work, design only).
   Generate PD score variants targeting specific Gini levels (e.g., 0.30,
   0.45, 0.60) by Gaussian logit perturbation, while preserving calibrated
   mean PD = portfolio base rate.

Public API:
  - make_calibration_split(df, train_max_excl_calib, calib_periods)
  - fit_platt(scores_calib, y_calib)
  - fit_isotonic(scores_calib, y_calib)
  - apply_calibrator(scores, calibrator, kind)
  - StressTestPlan: dataclass capturing the stress-test methodology
  - perturb_to_target_gini(scores, y, target_gini, seed): EXAMPLE/REFERENCE
    implementation; not executed in Phase 2A.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Sequence

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score


# =============================================================================
# Leak-free calibration
# =============================================================================

def make_calibration_split(
    df: pd.DataFrame,
    train_periods: Sequence[int],
    calib_periods: Sequence[int],
) -> pd.Series:
    """Return a Series with values in {'train_for_model', 'calib', 'oot', 'exclude'}.

    Inputs:
      df: must contain 'fin_period' and 'split' columns (split in {'train','oot'}).
      train_periods: cohorts used to fit the PD model
      calib_periods: cohorts used to fit Platt/isotonic calibration
        (must be a SUBSET of the original 'train' split — never OOT)

    Notes:
      - Original 'split' values 'train' that are NOT in train_periods + calib_periods
        are marked 'exclude'.
      - 'oot' rows pass through unchanged.
      - Calib_periods MUST come from the original train, not OOT.
    """
    if not set(calib_periods).issubset(set(train_periods) | set(calib_periods)):
        # train_periods + calib_periods together must form the original train set
        pass
    # Sanity: calib must come from rows originally split=='train'
    train_rows = df[df["split"] == "train"]
    calib_rows = df[df["fin_period"].isin(calib_periods)]
    if (calib_rows["split"] != "train").any():
        raise ValueError(
            "calib_periods contain cohorts NOT in original train split — "
            "this would leak OOT into calibration"
        )
    s = pd.Series("exclude", index=df.index, dtype="object")
    s.loc[df["fin_period"].isin(train_periods)] = "train_for_model"
    s.loc[df["fin_period"].isin(calib_periods)] = "calib"
    s.loc[df["split"] == "oot"] = "oot"
    return s


def fit_platt(scores: np.ndarray, y: np.ndarray) -> LogisticRegression:
    """Fit Platt scaling: logistic regression on raw PD scores.

    Returns a sklearn LogisticRegression fitted on (logit-of-pd, y) so that
    apply_calibrator returns calibrated probabilities."""
    s = np.asarray(scores, dtype=np.float64)
    yv = np.asarray(y, dtype=int)
    # Avoid log(0) / log(1)
    s = np.clip(s, 1e-9, 1 - 1e-9)
    logit_s = np.log(s / (1 - s)).reshape(-1, 1)
    lr = LogisticRegression(C=1e9, solver="lbfgs", max_iter=1000)
    lr.fit(logit_s, yv)
    return lr


def fit_isotonic(scores: np.ndarray, y: np.ndarray) -> IsotonicRegression:
    """Fit isotonic regression on raw PD scores."""
    s = np.asarray(scores, dtype=np.float64)
    yv = np.asarray(y, dtype=int)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(s, yv)
    return iso


def apply_calibrator(scores: np.ndarray, calibrator, kind: str) -> np.ndarray:
    """Apply a fitted calibrator. `kind` must be 'platt' or 'isotonic'."""
    s = np.asarray(scores, dtype=np.float64)
    if kind == "platt":
        s_clip = np.clip(s, 1e-9, 1 - 1e-9)
        logit = np.log(s_clip / (1 - s_clip)).reshape(-1, 1)
        return calibrator.predict_proba(logit)[:, 1]
    if kind == "isotonic":
        return calibrator.predict(s)
    raise ValueError(f"unknown calibrator kind: {kind}")


# =============================================================================
# Score-discrimination stress-test (PHASE 3/4 DESIGN ONLY — DO NOT EXECUTE NOW)
# =============================================================================

@dataclass
class StressTestPlan:
    """Stress-test methodology spec for Phase 3/4.

    Methodology:
      Take a calibrated PD score s (so mean(s) ≈ base_rate). Generate variants
      with target Gini in TARGET_GINIS by adding Gaussian noise to the *logit*
      of s, then re-calibrating to match base rate. The amount of noise sigma
      is solved by binary search to hit each target Gini ± tolerance.

    Why logit-noise and not raw-noise?
      Logit perturbation preserves the (0,1) range and degrades discrimination
      smoothly. Raw-probability noise would clip and create artefacts at the
      tails. Logit-noise is also closer to how real-world PD models degrade
      (e.g., from feature drift).

    Why re-calibrate after perturbation?
      Adding noise to the logit shifts the mean predicted probability away
      from the base rate. We re-fit a single-parameter shift (or Platt) on
      the perturbed logits using the calibration set so that mean(s_perturbed)
      = base_rate exactly. This isolates the discrimination shift from the
      calibration shift.

    Output regimes (per ChatGPT's framing for thesis methodology):
      - raw model PD (current Gini ≈ 0.71 on OOT)
      - target Gini = 0.60
      - target Gini = 0.45
      - target Gini = 0.30
    Each will be evaluated under the Phase 3 profit-cut-off framework.

    NOT EXECUTED in Phase 2A. Phase 3 will run perturb_to_target_gini below
    on the calibrated PD score from this run.
    """
    target_ginis: Tuple[float, ...] = (0.60, 0.45, 0.30)
    tolerance: float = 0.005  # acceptable +/- on Gini
    sigma_search_bounds: Tuple[float, float] = (0.0, 5.0)
    n_search_iter: int = 30
    base_rate_match: bool = True
    seed: int = 42
    notes: str = (
        "Logit-noise perturbation; re-calibrate mean to base rate after "
        "perturbation so that profit-cutoff comparison isolates discrimination "
        "shift from calibration shift."
    )


def perturb_to_target_gini(
    scores: np.ndarray,
    y: np.ndarray,
    target_gini: float,
    seed: int = 42,
    tolerance: float = 0.005,
    sigma_max: float = 5.0,
    n_iter: int = 30,
    re_calibrate: bool = True,
) -> Tuple[np.ndarray, dict]:
    """Reference implementation for Phase 3/4. Binary-search sigma so that
    Gini(scores_perturbed, y) ≈ target_gini.

    NOT EXECUTED in Phase 2A — included here as the canonical implementation
    for Phase 3 to call without re-implementing.

    Returns (perturbed_scores, metadata_dict).
    """
    rng = np.random.default_rng(seed)
    s = np.asarray(scores, dtype=np.float64)
    s_clip = np.clip(s, 1e-9, 1 - 1e-9)
    logit_s = np.log(s_clip / (1 - s_clip))
    yv = np.asarray(y, dtype=int)
    base_rate = float(yv.mean())

    def gini_at_sigma(sigma):
        eps = rng.normal(0, sigma, size=len(logit_s))
        new_logit = logit_s + eps
        new_s = 1.0 / (1.0 + np.exp(-new_logit))
        if re_calibrate:
            # Single shift: solve b such that mean(sigmoid(new_logit + b)) = base_rate
            # Binary-search on shift b.
            lo, hi = -5.0, 5.0
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                m = float(np.mean(1.0 / (1.0 + np.exp(-(new_logit + mid)))))
                if m < base_rate:
                    lo = mid
                else:
                    hi = mid
            b = 0.5 * (lo + hi)
            new_s = 1.0 / (1.0 + np.exp(-(new_logit + b)))
        if len(np.unique(yv)) < 2:
            return float("nan"), new_s
        auc = roc_auc_score(yv, new_s)
        return abs(2 * auc - 1.0), new_s

    # Binary search on sigma
    lo, hi = 0.0, sigma_max
    raw_gini, _ = gini_at_sigma(0.0)
    if target_gini >= raw_gini:
        return s, {"sigma": 0.0, "achieved_gini": raw_gini,
                   "note": "target_gini >= raw_gini; returning unmodified scores"}
    best = None
    for _ in range(n_iter):
        mid = 0.5 * (lo + hi)
        g, sp = gini_at_sigma(mid)
        if abs(g - target_gini) <= tolerance:
            best = (mid, g, sp)
            break
        if g > target_gini:
            lo = mid
        else:
            hi = mid
        best = (mid, g, sp)
    sigma_used, gini_used, sp = best
    return sp, {
        "sigma": float(sigma_used),
        "achieved_gini": float(gini_used),
        "target_gini": float(target_gini),
        "raw_gini": float(raw_gini),
        "tolerance_met": bool(abs(gini_used - target_gini) <= tolerance),
        "re_calibrated_to_base_rate": bool(re_calibrate),
        "base_rate": base_rate,
        "seed": seed,
    }
