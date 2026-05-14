"""
Phase 2B scorecard helpers — custom WoE binning.

Why custom: optbinning 0.20.0 has a sklearn API mismatch (uses deprecated
`force_all_finite`) that produces empty splits in this environment. Rolling
our own keeps full control over monotonicity enforcement and avoids the
external solver dependency.

Public API:
  - NumericBinner:    quantile binning + monotonic merge
  - CategoricalBinner: event-rate-sorted binning + min-size merge
  - apply_woe(df, binners): WoE-transform a dataframe in place
  - build_scorecard(model, binners, base_score, pdo, base_odds): produce
    feature/bin/WoE/beta/points table
  - score_from_woe(woe_df, binners, scorecard_table): compute total score per
    row

Conventions:
  - WoE is computed on TRAIN ONLY then frozen.
  - WoE = log( (events / total_events) / (non_events / total_non_events) )
  - With Laplace smoothing eps=0.5 to avoid log(0) on small bins.
  - Points alignment: factor = pdo / log(2). Higher score = lower default risk.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import math
import numpy as np
import pandas as pd


# =============================================================================
# Numeric binning
# =============================================================================

@dataclass
class NumericBinner:
    feature: str
    n_initial_bins: int = 20
    min_bin_size_frac: float = 0.05
    monotonic: bool = True
    smoothing: float = 0.5  # Laplace add-K for WoE
    # Frozen state after fit:
    cuts: List[float] = field(default_factory=list)         # ascending cut points (inner)
    bin_woe: List[float] = field(default_factory=list)       # one WoE per bin
    bin_event_rate: List[float] = field(default_factory=list)
    bin_count: List[int] = field(default_factory=list)
    bin_events: List[int] = field(default_factory=list)
    iv: float = 0.0
    monotonic_trend: str = ""  # 'ascending' / 'descending' / 'mixed'

    def fit(self, x: pd.Series, y: pd.Series) -> "NumericBinner":
        x = pd.to_numeric(x, errors="coerce")
        y = y.astype(int)
        valid = x.notna() & y.notna()
        x = x[valid].to_numpy(dtype=np.float64)
        y = y[valid].to_numpy(dtype=int)
        n_total = len(x)
        n_events_total = int(y.sum())
        n_nonevents_total = n_total - n_events_total

        if n_events_total == 0 or n_nonevents_total == 0:
            # Degenerate: single bin
            self.cuts = []
            self.bin_woe = [0.0]
            self.bin_event_rate = [n_events_total / max(n_total, 1)]
            self.bin_count = [n_total]
            self.bin_events = [n_events_total]
            self.iv = 0.0
            self.monotonic_trend = "flat"
            return self

        # 1) Quantile cuts (handle low-cardinality numerics)
        unique_vals = np.unique(x)
        if len(unique_vals) <= self.n_initial_bins:
            cuts = sorted(unique_vals.tolist())[:-1]  # use all but max as cuts
            cuts = [float(c) for c in cuts]
        else:
            qs = np.linspace(0, 1, self.n_initial_bins + 1)[1:-1]
            cuts = np.quantile(x, qs)
            cuts = sorted({float(round(c, 9)) for c in cuts})  # dedup ties

        # 2) Build initial bins
        bins = self._compute_bins(x, y, cuts)

        # 3) Merge bins below min size
        min_size = max(int(self.min_bin_size_frac * n_total), 1)
        bins = self._merge_small_bins(bins, x, y, cuts, min_size)
        cuts = [b["upper"] for b in bins[:-1]]

        # 4) Enforce monotonicity (recompute cuts iteratively)
        if self.monotonic:
            bins, cuts = self._enforce_monotonicity(bins, x, y, cuts)

        # 5) Final WoE + IV
        self.cuts = cuts
        self.bin_woe = [b["woe"] for b in bins]
        self.bin_event_rate = [b["event_rate"] for b in bins]
        self.bin_count = [b["n"] for b in bins]
        self.bin_events = [b["n_events"] for b in bins]
        self.iv = self._compute_iv(bins, n_events_total, n_nonevents_total)
        self.monotonic_trend = self._classify_trend(self.bin_woe)
        return self

    def transform(self, x: pd.Series) -> np.ndarray:
        """Return WoE for each value in x."""
        x_num = pd.to_numeric(x, errors="coerce").to_numpy(dtype=np.float64)
        idx = np.searchsorted(self.cuts, x_num, side="right")
        # NaN handling: assign to first bin (could also be a separate bin)
        woe_out = np.full(len(x_num), np.nan, dtype=np.float64)
        valid = ~np.isnan(x_num)
        woe_arr = np.array(self.bin_woe, dtype=np.float64)
        woe_out[valid] = woe_arr[np.clip(idx[valid], 0, len(self.bin_woe) - 1)]
        # Replace NaN (from x being NaN) with the population mean WoE = 0
        woe_out[~valid] = 0.0
        return woe_out

    def get_bin_label(self, idx: int) -> str:
        if idx == 0:
            lo = "(-inf"
        else:
            lo = f"[{self.cuts[idx-1]:.4g}"
        if idx == len(self.bin_woe) - 1:
            hi = "+inf)"
        else:
            hi = f"{self.cuts[idx]:.4g})"
        return f"{lo}, {hi}"

    # ---- internal ----
    def _compute_bins(self, x, y, cuts):
        edges = [-np.inf] + list(cuts) + [np.inf]
        bins = []
        n_events_total = int(y.sum())
        n_nonevents_total = len(y) - n_events_total
        for i in range(len(edges) - 1):
            mask = (x > edges[i]) & (x <= edges[i + 1])
            n = int(mask.sum())
            n_events = int(y[mask].sum())
            n_nonevents = n - n_events
            er = n_events / max(n, 1)
            ev_smooth = (n_events + self.smoothing) / (n_events_total + self.smoothing * 2)
            ne_smooth = (n_nonevents + self.smoothing) / (n_nonevents_total + self.smoothing * 2)
            woe = math.log(ev_smooth / ne_smooth)
            bins.append({
                "i": i, "lower": edges[i], "upper": edges[i + 1],
                "n": n, "n_events": n_events, "event_rate": er, "woe": woe,
            })
        return bins

    def _merge_small_bins(self, bins, x, y, cuts, min_size):
        # Merge with the smaller adjacent neighbour; iterate until all >= min_size
        while True:
            small = [b for b in bins if b["n"] < min_size]
            if not small or len(bins) <= 2:
                break
            # Merge the smallest one into its adjacent neighbour
            target = min(small, key=lambda b: b["n"])
            i = bins.index(target)
            if i == 0:
                neighbour = bins[1]; merge_idx = 1
            elif i == len(bins) - 1:
                neighbour = bins[-2]; merge_idx = -2
            else:
                # Merge into smaller neighbour
                neighbour = bins[i - 1] if bins[i - 1]["n"] <= bins[i + 1]["n"] else bins[i + 1]
                merge_idx = i - 1 if neighbour is bins[i - 1] else i + 1
            # Determine the cut to remove
            cut_to_remove = min(target["upper"], neighbour["upper"])
            if cut_to_remove < np.inf and cut_to_remove in cuts:
                cuts = [c for c in cuts if c != cut_to_remove]
            bins = self._compute_bins(x, y, cuts)
        return bins

    def _enforce_monotonicity(self, bins, x, y, cuts):
        # Determine intended direction using Spearman correlation between
        # bin midpoint (or centre rank) and bin event rate
        if len(bins) < 3:
            return bins, cuts
        midpoints = [
            (b["lower"] + b["upper"]) / 2 if np.isfinite(b["lower"]) and np.isfinite(b["upper"])
            else (b["upper"] - 1 if np.isinf(b["lower"]) else b["lower"] + 1)
            for b in bins
        ]
        ev_rates = [b["event_rate"] for b in bins]
        # Simple sign-based direction: count up-steps vs down-steps
        ups = sum(1 for a, b in zip(ev_rates, ev_rates[1:]) if b > a)
        downs = sum(1 for a, b in zip(ev_rates, ev_rates[1:]) if b < a)
        direction = "ascending" if ups >= downs else "descending"

        # Iteratively merge violating adjacent bins
        max_iter = 100
        for _ in range(max_iter):
            ev = [b["event_rate"] for b in bins]
            violations = []
            for i in range(len(ev) - 1):
                if direction == "ascending" and ev[i + 1] < ev[i]:
                    violations.append(i)
                if direction == "descending" and ev[i + 1] > ev[i]:
                    violations.append(i)
            if not violations:
                break
            # Merge first violation
            i = violations[0]
            cut_to_remove = bins[i]["upper"]
            if cut_to_remove in cuts:
                cuts = [c for c in cuts if c != cut_to_remove]
            bins = self._compute_bins(x, y, cuts)
            if len(bins) == 1:
                break
        return bins, cuts

    def _compute_iv(self, bins, n_ev_total, n_ne_total):
        iv = 0.0
        for b in bins:
            ev = (b["n_events"] + self.smoothing) / (n_ev_total + self.smoothing * 2)
            ne = (b["n"] - b["n_events"] + self.smoothing) / (n_ne_total + self.smoothing * 2)
            iv += (ev - ne) * math.log(ev / ne)
        return float(iv)

    def _classify_trend(self, woe):
        if len(woe) < 2:
            return "flat"
        diffs = [b - a for a, b in zip(woe, woe[1:])]
        if all(d >= -1e-9 for d in diffs):
            return "ascending"
        if all(d <= 1e-9 for d in diffs):
            return "descending"
        return "mixed"


# =============================================================================
# Categorical binning
# =============================================================================

@dataclass
class CategoricalBinner:
    feature: str
    min_bin_size_frac: float = 0.05
    smoothing: float = 0.5
    # Frozen state:
    category_to_bin: Dict[str, int] = field(default_factory=dict)
    bin_categories: List[List[str]] = field(default_factory=list)
    bin_woe: List[float] = field(default_factory=list)
    bin_event_rate: List[float] = field(default_factory=list)
    bin_count: List[int] = field(default_factory=list)
    bin_events: List[int] = field(default_factory=list)
    iv: float = 0.0

    def fit(self, x: pd.Series, y: pd.Series) -> "CategoricalBinner":
        x_str = x.astype(str).fillna("__NA__")
        y_int = y.astype(int)
        df = pd.DataFrame({"x": x_str, "y": y_int})
        n_total = len(df)
        n_ev_total = int(df["y"].sum())
        n_ne_total = n_total - n_ev_total
        if n_ev_total == 0 or n_ne_total == 0:
            cats = df["x"].unique().tolist()
            self.category_to_bin = {c: 0 for c in cats}
            self.bin_categories = [cats]
            self.bin_woe = [0.0]
            self.bin_event_rate = [0.0]
            self.bin_count = [n_total]
            self.bin_events = [n_ev_total]
            self.iv = 0.0
            return self

        # Per-category event rate
        agg = df.groupby("x")["y"].agg(["sum", "count"]).rename(
            columns={"sum": "n_events", "count": "n"}
        )
        agg["event_rate"] = agg["n_events"] / agg["n"]
        agg = agg.sort_values("event_rate")  # ascending

        # Greedy merge: ensure every bin has at least min_size
        min_size = max(int(self.min_bin_size_frac * n_total), 50)
        bins: List[List[str]] = []
        current: List[str] = []
        current_n = 0
        for cat, row in agg.iterrows():
            current.append(cat)
            current_n += int(row["n"])
            if current_n >= min_size:
                bins.append(current)
                current = []
                current_n = 0
        if current:
            if bins:
                bins[-1].extend(current)
            else:
                bins.append(current)

        # Compute WoE per merged bin
        cat_to_bin: Dict[str, int] = {}
        bin_woe = []
        bin_er = []
        bin_count = []
        bin_events = []
        iv = 0.0
        for bi, cats in enumerate(bins):
            sub = df[df["x"].isin(cats)]
            n = len(sub)
            n_events = int(sub["y"].sum())
            er = n_events / max(n, 1)
            ev_s = (n_events + self.smoothing) / (n_ev_total + self.smoothing * 2)
            ne_s = (n - n_events + self.smoothing) / (n_ne_total + self.smoothing * 2)
            woe = math.log(ev_s / ne_s)
            iv += (ev_s - ne_s) * woe
            bin_woe.append(woe)
            bin_er.append(er)
            bin_count.append(n)
            bin_events.append(n_events)
            for c in cats:
                cat_to_bin[c] = bi
        self.category_to_bin = cat_to_bin
        self.bin_categories = bins
        self.bin_woe = bin_woe
        self.bin_event_rate = bin_er
        self.bin_count = bin_count
        self.bin_events = bin_events
        self.iv = float(iv)
        return self

    def transform(self, x: pd.Series) -> np.ndarray:
        x_str = x.astype(str).fillna("__NA__")
        out = np.zeros(len(x_str), dtype=np.float64)
        for i, val in enumerate(x_str.to_numpy()):
            bi = self.category_to_bin.get(val, None)
            if bi is None:
                # Unseen category in OOT -> use closest bin by event rate
                # (here, default to bin with median event rate, i.e., fall through to 0 WoE)
                out[i] = 0.0
            else:
                out[i] = self.bin_woe[bi]
        return out

    def get_bin_label(self, idx: int) -> str:
        cats = self.bin_categories[idx]
        return ", ".join(str(c) for c in cats[:6]) + ("..." if len(cats) > 6 else "")


# =============================================================================
# WoE transformation + scorecard helpers
# =============================================================================

def apply_woe(df: pd.DataFrame, binners: Dict[str, "object"], suffix: str = "_woe") -> pd.DataFrame:
    """Apply each binner to its feature; return new df with `<feature><suffix>` cols."""
    out = df.copy()
    for fname, b in binners.items():
        if fname not in df.columns:
            raise ValueError(f"feature {fname} missing in df")
        out[f"{fname}{suffix}"] = b.transform(df[fname])
    return out


def build_scorecard(
    feature_betas: Dict[str, float],
    intercept: float,
    binners: Dict[str, "object"],
    base_score: float = 300.0,
    pdo: float = 20.0,
    base_odds: float = 1.0 / 50.0,  # 1 bad : 50 good at base
) -> pd.DataFrame:
    """Build a scorecard table. Higher score = lower risk.

    factor = pdo / log(2)
    offset = base_score - factor * log(base_odds)
    Per-bin points = -(beta_feature * woe_bin) * factor
    Intercept points = offset - factor * intercept (split equally across n_features)
    """
    factor = pdo / math.log(2)
    offset = base_score - factor * math.log(base_odds)
    n_features = len(feature_betas)
    intercept_per_feature = (offset - factor * intercept) / max(n_features, 1)

    rows = []
    for fname, beta in feature_betas.items():
        b = binners[fname]
        for i, woe in enumerate(b.bin_woe):
            pts_woe = -(beta * woe) * factor
            pts_total = pts_woe + intercept_per_feature
            label = b.get_bin_label(i)
            rows.append({
                "feature": fname,
                "bin_index": i,
                "bin_label": label,
                "n": b.bin_count[i],
                "n_events": b.bin_events[i],
                "event_rate": b.bin_event_rate[i],
                "woe": woe,
                "beta": beta,
                "points_from_woe": round(pts_woe, 2),
                "points_intercept_share": round(intercept_per_feature, 2),
                "points_total": round(pts_total, 2),
            })
    cols = ["feature", "bin_index", "bin_label", "n", "n_events", "event_rate",
            "woe", "beta", "points_from_woe", "points_intercept_share", "points_total"]
    return pd.DataFrame(rows, columns=cols)


def score_from_woe(woe_df: pd.DataFrame, scorecard: pd.DataFrame) -> np.ndarray:
    """Apply scorecard points to a WoE-transformed dataframe.

    Each row's score = sum over features of (points_from_woe selected by bin) +
    sum of points_intercept_share.

    woe_df must contain `<feature>_woe` columns. We use the unique mapping from
    woe value -> points_from_woe within each feature (deterministic since
    scorecard builds points = -beta * woe * factor).
    """
    factor_pts = {}
    intercept_share_total = scorecard.groupby("feature")["points_intercept_share"].first().sum()
    out = np.full(len(woe_df), float(intercept_share_total), dtype=np.float64)
    for fname, sub in scorecard.groupby("feature"):
        # WoE -> points map
        woe_to_pts = dict(zip(sub["woe"].round(8), sub["points_from_woe"]))
        col = woe_df[f"{fname}_woe"].round(8).to_numpy()
        pts = np.array([woe_to_pts.get(v, 0.0) for v in col], dtype=np.float64)
        out += pts
    return out
