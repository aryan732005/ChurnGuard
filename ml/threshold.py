"""Cost-sensitive decision threshold optimization."""

from __future__ import annotations

import numpy as np


def expected_cost(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float,
    cost_fp: float,
    cost_fn: float,
) -> float:
    """Total misclassification cost at a given threshold."""
    y_pred = (y_prob >= threshold).astype(int)
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    return fp * cost_fp + fn * cost_fn


def optimal_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    cost_fp: float,
    cost_fn: float,
    n_steps: int = 91,
) -> dict:
    """
    Find threshold minimizing expected business cost on held-out probabilities.
    cost_fp = retention offer wasted on non-churner.
    cost_fn = lost LTV from missed churner.
    """
    thresholds = np.linspace(0.05, 0.95, n_steps)
    costs = [expected_cost(y_true, y_prob, t, cost_fp, cost_fn) for t in thresholds]
    best_idx = int(np.argmin(costs))
    best_t = float(thresholds[best_idx])
    # Floor: extremely low thresholds flag nearly everyone when FN cost >> FP cost
    if best_t < 0.15:
        viable = [(t, c) for t, c in zip(thresholds, costs) if t >= 0.15]
        if viable:
            best_t = min(viable, key=lambda x: x[1])[0]
            best_idx = int(np.argmin([abs(t - best_t) for t in thresholds]))

    y_pred = (y_prob >= best_t).astype(int)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())

    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0

    reasoning = (
        f"Threshold {best_t:.2f} minimises expected cost with FP cost ${cost_fp:.0f} "
        f"(retention offer) vs FN cost ${cost_fn:.0f} (lost LTV). "
        f"At 0.50 default, more false alarms or missed churners would cost more in aggregate."
    )

    curve = [
        {
            "threshold": round(float(t), 3),
            "expected_cost": round(float(c), 2),
        }
        for t, c in zip(thresholds[::4], costs[::4])
    ]

    return {
        "optimal_threshold": round(best_t, 3),
        "default_threshold": 0.5,
        "cost_fp": cost_fp,
        "cost_fn": cost_fn,
        "expected_cost_at_optimal": round(float(costs[best_idx]), 2),
        "expected_cost_at_default": round(
            float(expected_cost(y_true, y_prob, 0.5, cost_fp, cost_fn)), 2
        ),
        "precision_at_optimal": round(prec, 4),
        "recall_at_optimal": round(rec, 4),
        "confusion_at_optimal": [[tn, fp], [fn, tp]],
        "reasoning": reasoning,
        "cost_curve": curve,
        "roi_alignment_note": (
            "Dashboard ROI calculator uses the same FP cost (offer) and FN cost (LTV) "
            "assumptions. Campaign targeting should use this threshold, not 0.50."
        ),
    }
