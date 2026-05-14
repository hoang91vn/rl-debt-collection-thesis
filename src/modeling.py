"""
Phase 2 modeling helpers: prescreening, Lasso selection, statsmodels logit, VIF.

All functions consume a wide ABT (post Phase 1.5 feature factory) plus a
target column ('default_flag_12m') and a list of candidate features. They are
written to be unit-testable: pure inputs in, deterministic outputs out (with
explicit random_state where stochastic).
"""
from __future__ import annotations
from typing import List, Sequence
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegressionCV
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler


# =============================================================================
# Stage 1 — univariate prescreening
# =============================================================================

def _univariate_gini(y: pd.Series, x: pd.Series) -> float:
    """Univariate |Gini| via roc_auc_score; returns 0.0 if degenerate."""
    mask = ~(x.isna() | y.isna())
    if mask.sum() < 100:
        return 0.0
    yv = y[mask].to_numpy()
    xv = x[mask].to_numpy()
    if len(np.unique(yv)) < 2 or len(np.unique(xv)) < 2:
        return 0.0
    try:
        auc = roc_auc_score(yv, xv)
    except Exception:
        return 0.0
    return abs(2.0 * auc - 1.0)


def run_stage1_prescreening(
    df: pd.DataFrame,
    target_col: str,
    features: Sequence[str],
    sparse_threshold: float = 0.5,
    gini_min: float = 0.02,
    stability_max: float = 0.2,
) -> pd.DataFrame:
    """Per-feature prescreening on TRAIN rows only.

    Filters:
      - sparsity:  pct_nan <= sparse_threshold
      - variance:  near-zero variance reject (numeric stddev > 0)
      - signal:    train_gini >= gini_min
      - stability: |train_gini - oot_gini| / max(train_gini, eps) <= stability_max

    Returns DataFrame indexed by feature with columns:
      ['feature', 'pct_nan', 'std', 'train_gini', 'oot_gini', 'gini_drop_pct',
       'pass_sparse', 'pass_variance', 'pass_signal', 'pass_stability', 'survives']
    """
    if "split" not in df.columns:
        raise ValueError("df must contain a 'split' column with 'train'/'oot' values")

    train_mask = df["split"] == "train"
    oot_mask = df["split"] == "oot"
    if train_mask.sum() == 0 or oot_mask.sum() == 0:
        raise ValueError("df has no train or oot rows")

    y_tr = df.loc[train_mask, target_col]
    y_oot = df.loc[oot_mask, target_col]

    rows = []
    for f in features:
        x_full = df[f]
        pct_nan = float(x_full.isna().mean())
        # std on train only
        try:
            std = float(x_full[train_mask].std(ddof=1))
        except (TypeError, ValueError):
            std = 0.0
        if not np.isfinite(std):
            std = 0.0
        # Univariate Gini
        train_gini = _univariate_gini(y_tr, x_full[train_mask])
        oot_gini = _univariate_gini(y_oot, x_full[oot_mask])
        eps = 1e-9
        gini_drop_pct = abs(train_gini - oot_gini) / max(train_gini, eps)

        pass_sparse = pct_nan <= sparse_threshold
        pass_variance = std > 0
        pass_signal = train_gini >= gini_min
        pass_stability = (
            train_gini < gini_min  # if no signal, stability is moot; rely on signal filter
            or gini_drop_pct <= stability_max
        )
        survives = pass_sparse and pass_variance and pass_signal and pass_stability

        rows.append({
            "feature": f,
            "pct_nan": round(pct_nan, 4),
            "std": round(std, 6),
            "train_gini": round(train_gini, 4),
            "oot_gini": round(oot_gini, 4),
            "gini_drop_pct": round(gini_drop_pct, 4),
            "pass_sparse": pass_sparse,
            "pass_variance": pass_variance,
            "pass_signal": pass_signal,
            "pass_stability": pass_stability,
            "survives": survives,
        })
    out = pd.DataFrame(rows)
    return out[out["survives"]].sort_values("train_gini", ascending=False).reset_index(drop=True)


# =============================================================================
# Stage 2 — Lasso (L1-penalised logistic regression)
# =============================================================================

def run_lasso_selection(
    df: pd.DataFrame,
    features: Sequence[str],
    target_col: str,
    cv: int = 3,
    n_cs: int = 5,
    random_state: int = 42,
    max_iter: int = 2000,
    solver: str = "liblinear",
    use_cv: bool = False,
    fixed_c: float = 0.05,
    train_subsample: int | None = 100_000,
) -> List[str]:
    """L1-penalised logistic regression on TRAIN rows; returns features with
    nonzero coefficient at the chosen inverse regularisation strength C.

    Two modes:
      use_cv=False (default, fast): single fit at fixed_c (industry standard
        for feature selection; CV-tuning the L1 penalty is well-known to be
        unstable for variable selection — Hastie & Tibshirani, 2015).
      use_cv=True: LogisticRegressionCV with `cv` folds and `n_cs` candidate
        Cs (slower but tunes the penalty by CV-AUC).

    `train_subsample` (default 100,000): cap the training rows to keep wall
    time bounded. Set to None to use all rows. Stratified subsample with
    `random_state` for reproducibility. Only applies when use_cv=False.

    Inputs are standardised (column-wise) before fitting. NaNs are filled with
    the train median before scaling. Solver defaults to 'liblinear' (fast for
    binary L1).
    """
    from sklearn.linear_model import LogisticRegression
    if not features:
        return []
    train_mask = df["split"] == "train"
    X = df.loc[train_mask, list(features)].copy()
    y = df.loc[train_mask, target_col].astype(int).to_numpy()

    # Median-impute NaNs (column-wise) using train medians
    medians = X.median(numeric_only=True)
    X = X.fillna(medians)
    keep = X.columns[~X.isna().any()].tolist()
    X = X[keep]

    if X.shape[1] == 0:
        return []

    # Stratified subsample for fast mode
    if not use_cv and train_subsample is not None and len(X) > train_subsample:
        rng = np.random.default_rng(random_state)
        pos_idx = np.where(y == 1)[0]
        neg_idx = np.where(y == 0)[0]
        n_pos = len(pos_idx)
        n_neg = len(neg_idx)
        # Maintain class ratio in the subsample
        target_pos = int(round(train_subsample * n_pos / (n_pos + n_neg)))
        target_neg = train_subsample - target_pos
        sel_pos = rng.choice(pos_idx, size=min(target_pos, n_pos), replace=False)
        sel_neg = rng.choice(neg_idx, size=min(target_neg, n_neg), replace=False)
        sel = np.concatenate([sel_pos, sel_neg])
        rng.shuffle(sel)
        X = X.iloc[sel]
        y = y[sel]

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X.to_numpy(dtype=np.float64))

    if use_cv:
        n_jobs = None if solver == "liblinear" else -1
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lasso = LogisticRegressionCV(
                Cs=n_cs, cv=cv, penalty="l1", solver=solver,
                scoring="roc_auc", max_iter=max_iter,
                random_state=random_state, n_jobs=n_jobs,
            )
            lasso.fit(Xs, y)
        coefs = lasso.coef_.ravel()
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lasso = LogisticRegression(
                penalty="l1", C=fixed_c, solver=solver,
                max_iter=max_iter, random_state=random_state,
            )
            lasso.fit(Xs, y)
        coefs = lasso.coef_.ravel()

    survivors = [f for f, c in zip(keep, coefs) if abs(c) > 1e-10]
    return survivors


# =============================================================================
# Stage 3 — statsmodels logit + VIF
# =============================================================================

def fit_logit_statsmodels(
    df: pd.DataFrame,
    features: Sequence[str],
    target_col: str,
):
    """Fit statsmodels Logit on TRAIN rows; returns the fitted results object.

    Adds an intercept ('const'). NaN rows in features are dropped.
    """
    import statsmodels.api as sm
    train_mask = df["split"] == "train"
    X = df.loc[train_mask, list(features)].copy()
    y = df.loc[train_mask, target_col].astype(int)
    keep = ~X.isna().any(axis=1)
    X = X.loc[keep]
    y = y.loc[keep]
    X = sm.add_constant(X, has_constant="add")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return sm.Logit(y, X).fit(disp=False, maxiter=200)


def compute_vif(df: pd.DataFrame, features: Sequence[str]) -> pd.DataFrame:
    """Variance Inflation Factor per feature on TRAIN rows.

    VIF = 1 / (1 - R^2_of_OLS_regress_of_feature_on_others).
    """
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    import statsmodels.api as sm
    train_mask = df["split"] == "train"
    X = df.loc[train_mask, list(features)].copy()
    X = X.fillna(X.median(numeric_only=True))
    X = X.dropna(axis=1, how="any")  # drop any all-NaN cols
    Xc = sm.add_constant(X, has_constant="add").to_numpy(dtype=np.float64)
    rows = []
    cols = ["const"] + list(X.columns)
    for i, name in enumerate(cols):
        if name == "const":
            continue
        try:
            v = variance_inflation_factor(Xc, i)
        except Exception:
            v = float("nan")
        rows.append({"feature": name, "vif": v})
    return pd.DataFrame(rows).sort_values("vif", ascending=False).reset_index(drop=True)
