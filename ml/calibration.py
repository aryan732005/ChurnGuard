"""Probability calibration: reliability curves and Platt / isotonic correction."""

from __future__ import annotations

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


def reliability_bins(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> dict:
    """Binned predicted vs observed churn rate for reliability diagram."""
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy="quantile")
    return {
        "predicted_mean": [round(float(v), 4) for v in prob_pred],
        "observed_rate": [round(float(v), 4) for v in prob_true],
        "n_bins": n_bins,
    }


def brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(np.mean((y_prob - y_true) ** 2))


def fit_calibrator(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    method: str = "auto",
) -> tuple[object, str, float, float]:
    """
    Fit calibration on validation probabilities.
    Returns (calibrator, method_used, brier_before, brier_after).
    """
    b_before = brier_score(y_true, y_prob)

    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(y_prob, y_true)
    iso_probs = iso.predict(y_prob)
    b_iso = brier_score(y_true, iso_probs)

    platt = LogisticRegression(max_iter=1000)
    platt.fit(y_prob.reshape(-1, 1), y_true)
    platt_probs = platt.predict_proba(y_prob.reshape(-1, 1))[:, 1]
    b_platt = brier_score(y_true, platt_probs)

    if method == "isotonic":
        chosen, name = iso, "isotonic"
        b_after = b_iso
    elif method == "platt":
        chosen, name = platt, "platt"
        b_after = b_platt
    else:
        if b_iso <= b_platt:
            chosen, name = iso, "isotonic"
            b_after = b_iso
        else:
            chosen, name = platt, "platt"
            b_after = b_platt

    return chosen, name, round(b_before, 4), round(b_after, 4)


def apply_calibrator(calibrator, y_prob: np.ndarray, method: str) -> np.ndarray:
    """Apply fitted isotonic or Platt calibrator to raw probabilities."""
    if method == "isotonic":
        return calibrator.predict(y_prob)
    return calibrator.predict_proba(y_prob.reshape(-1, 1))[:, 1]


def calibration_report(
    y_true: np.ndarray,
    y_prob_raw: np.ndarray,
    y_prob_cal: np.ndarray,
) -> dict:
    """Full calibration stats for stats.json."""
    before = reliability_bins(y_true, y_prob_raw)
    after = reliability_bins(y_true, y_prob_cal)
    return {
        "before": before,
        "after": after,
        "brier_before": brier_score(y_true, y_prob_raw),
        "brier_after": brier_score(y_true, y_prob_cal),
        "roi_note": (
            "ROI estimates multiply predicted probabilities by revenue assumptions. "
            "Uncalibrated probabilities systematically over- or under-state expected churners — "
            "use calibrated scores (after isotonic/Platt) for campaign sizing."
        ),
    }
