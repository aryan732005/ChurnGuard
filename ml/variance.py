"""Multi-seed variance reporting for model metrics."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    average_precision_score,
)
from sklearn.model_selection import train_test_split


METRIC_NAMES = ["accuracy", "precision", "recall", "f1_score", "roc_auc", "pr_auc"]


def evaluate_probs(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
    }


def multi_seed_variance(
    model_factory,
    X: np.ndarray,
    y: np.ndarray,
    seeds: list[int] | None = None,
    test_size: float = 0.2,
    fit_fn=None,
) -> dict:
    """
    Train/evaluate across multiple random seeds; report mean ± std.
    model_factory(seed) -> fresh unfitted model.
    fit_fn(model, X_train, y_train) optional custom fit.
    """
    if seeds is None:
        seeds = [11, 22, 33, 42, 55]

    runs: list[dict] = []
    for seed in seeds:
        idx = np.arange(len(y))
        train_idx, test_idx = train_test_split(
            idx, test_size=test_size, random_state=seed, stratify=y
        )
        X_tr, X_te = X[train_idx], X[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]

        model = model_factory(seed)
        if fit_fn:
            fit_fn(model, X_tr, y_tr)
        else:
            model.fit(X_tr, y_tr)

        y_prob = model.predict_proba(X_te)[:, 1]
        runs.append(evaluate_probs(y_te, y_prob))

    summary = {}
    for metric in METRIC_NAMES:
        vals = [r[metric] for r in runs]
        summary[metric] = {
            "mean": round(float(np.mean(vals)), 4),
            "std": round(float(np.std(vals)), 4),
            "values": [round(v, 4) for v in vals],
        }

    return {
        "seeds": seeds,
        "n_runs": len(seeds),
        "metrics": summary,
        "note": (
            f"Metrics reported as mean ± std over {len(seeds)} stratified hold-out splits "
            "(different random seeds). Complements single-split test metrics and 5-fold CV."
        ),
    }
