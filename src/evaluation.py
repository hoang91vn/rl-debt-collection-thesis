"""
Phase 2 evaluation metrics: Gini, KS, Brier, calibration metrics, PSI.

All metrics are computed defensively (NaN-safe, length-zero-safe).
"""
from __future__ import annotations
from typing import Dict
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, brier_score_loss


def _clean(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    return y_true[mask], y_pred[mask]


def compute_gini(y_true, y_pred) -> float:
    """Gini = 2 * AUC - 1.  Returns NaN if degenerate."""
    y, p = _clean(y_true, y_pred)
    if len(y) < 2 or len(np.unique(y)) < 2:
        return float("nan")
    auc = roc_auc_score(y, p)
    return float(2.0 * auc - 1.0)


def compute_ks(y_true, y_pred) -> float:
    """Kolmogorov-Smirnov statistic between positive and negative score
    distributions.  Returns max separation in [0, 1]."""
    y, p = _clean(y_true, y_pred)
    if len(y) < 2 or len(np.unique(y)) < 2:
        return float("nan")
    pos = p[y == 1]
    neg = p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    pos_sorted = np.sort(pos)
    neg_sorted = np.sort(neg)
    grid = np.unique(np.concatenate([pos_sorted, neg_sorted]))
    cdf_pos = np.searchsorted(pos_sorted, grid, side="right") / len(pos_sorted)
    cdf_neg = np.searchsorted(neg_sorted, grid, side="right") / len(neg_sorted)
    return float(np.max(np.abs(cdf_pos - cdf_neg)))


def compute_brier(y_true, y_pred) -> float:
    """Brier score (mean squared error of predicted probabilities).
    Lower is better; range [0, 1]."""
    y, p = _clean(y_true, y_pred)
    if len(y) < 2:
        return float("nan")
    return float(brier_score_loss(y, p))


def compute_calibration_metrics(y_true, y_pred, n_bins: int = 10) -> Dict[str, float]:
    """Compute decile-based calibration:
      observed_to_expected_<i> for i in 1..n_bins   (= mean(y) / mean(pred) per bin)
      ece                                             (weighted mean abs(o-e))
    """
    y, p = _clean(y_true, y_pred)
    out: Dict[str, float] = {}
    if len(y) < n_bins:
        return out
    qs = np.linspace(0, 1, n_bins + 1)
    edges = np.unique(np.quantile(p, qs))
    if len(edges) < 3:
        return out
    edges[0] = -np.inf
    edges[-1] = np.inf
    bin_idx = np.digitize(p, edges) - 1
    n_total = len(y)
    ece = 0.0
    for b in range(n_bins):
        mask = bin_idx == b
        n_b = int(mask.sum())
        if n_b == 0:
            out[f"o_to_e_bin{b+1}"] = float("nan")
            continue
        obs = float(y[mask].mean())
        exp = float(p[mask].mean())
        out[f"o_to_e_bin{b+1}"] = obs / exp if exp > 0 else float("inf")
        ece += abs(obs - exp) * n_b / n_total
    out["ece"] = float(ece)
    out["n"] = float(len(y))
    out["base_rate"] = float(np.mean(y))
    out["mean_pred"] = float(np.mean(p))
    return out


def compute_psi(reference, current, n_bins: int = 10) -> float:
    """Population Stability Index (reference-fit decile bins). Lower is better.
    Standard thresholds: <0.10 stable, 0.10-0.25 minor shift, >0.25 major shift.
    """
    ref = pd.Series(reference).dropna().to_numpy()
    cur = pd.Series(current).dropna().to_numpy()
    if len(ref) == 0 or len(cur) == 0:
        return float("nan")
    qs = np.linspace(0, 1, n_bins + 1)
    edges = np.unique(np.quantile(ref, qs))
    if len(edges) < 3:
        return float("nan")
    edges[0] = -np.inf
    edges[-1] = np.inf
    ref_counts, _ = np.histogram(ref, bins=edges)
    cur_counts, _ = np.histogram(cur, bins=edges)
    ref_pct = np.clip(ref_counts / max(ref_counts.sum(), 1), 1e-6, None)
    cur_pct = np.clip(cur_counts / max(cur_counts.sum(), 1), 1e-6, None)
    return float(((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)).sum())
