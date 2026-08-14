"""Training reference distributions and drift detection (PSI / KS)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


PSI_GREEN = 0.10
PSI_AMBER = 0.25

NUMERIC_DRIFT_COLS = ["tenure", "MonthlyCharges", "TotalCharges", "avg_charge_per_month", "service_count"]
CATEGORICAL_DRIFT_COLS = ["Contract", "PaymentMethod", "InternetService"]


def _psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """Population Stability Index for numeric feature."""
    eps = 1e-6
    breaks = np.quantile(expected, np.linspace(0, 1, buckets + 1))
    breaks = np.unique(breaks)
    if len(breaks) < 3:
        return 0.0

    exp_hist, _ = np.histogram(expected, bins=breaks)
    act_hist, _ = np.histogram(actual, bins=breaks)

    exp_pct = exp_hist / max(len(expected), 1) + eps
    act_pct = act_hist / max(len(actual), 1) + eps
    exp_pct = exp_pct / exp_pct.sum()
    act_pct = act_pct / act_pct.sum()

    return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))


def _categorical_psi(expected: pd.Series, actual: pd.Series) -> float:
    eps = 1e-6
    exp_counts = expected.value_counts(normalize=True)
    act_counts = actual.value_counts(normalize=True)
    all_cats = set(exp_counts.index) | set(act_counts.index)
    psi = 0.0
    for cat in all_cats:
        e = exp_counts.get(cat, eps)
        a = act_counts.get(cat, eps)
        psi += (a - e) * np.log(a / e)
    return float(abs(psi))


def build_reference_profile(df: pd.DataFrame) -> dict:
    """Snapshot training distributions for drift comparison."""
    profile: dict = {"numeric": {}, "categorical": {}}

    for col in NUMERIC_DRIFT_COLS:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        profile["numeric"][col] = {
            "mean": round(float(series.mean()), 4),
            "std": round(float(series.std()), 4),
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
            "sample": series.values[:5000].tolist(),
        }

    for col in CATEGORICAL_DRIFT_COLS:
        if col not in df.columns:
            continue
        vc = df[col].value_counts(normalize=True)
        profile["categorical"][col] = {str(k): round(float(v), 4) for k, v in vc.items()}

    return profile


def save_reference_profile(profile: dict, path: Path | str) -> None:
    Path(path).write_text(json.dumps(profile), encoding="utf-8")


def load_reference_profile(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def drift_status(psi: float) -> str:
    if psi < PSI_GREEN:
        return "green"
    if psi < PSI_AMBER:
        return "amber"
    return "red"


def compute_drift(incoming: pd.DataFrame, reference: dict) -> dict:
    """Compare batch upload against training reference."""
    if not reference:
        return {
            "overall_status": "unknown",
            "features": [],
            "note": "No training reference profile available.",
        }

    features = []

    for col, ref in reference.get("numeric", {}).items():
        if col not in incoming.columns:
            continue
        actual = pd.to_numeric(incoming[col], errors="coerce").dropna().values
        expected = np.array(ref.get("sample", []))
        if len(actual) < 5 or len(expected) < 5:
            continue
        psi = _psi(expected, actual)
        ks_stat, ks_p = stats.ks_2samp(expected, actual)
        status = drift_status(psi)
        features.append({
            "feature": col,
            "type": "numeric",
            "psi": round(psi, 4),
            "ks_statistic": round(float(ks_stat), 4),
            "ks_pvalue": round(float(ks_p), 4),
            "status": status,
        })

    for col, ref_dist in reference.get("categorical", {}).items():
        if col not in incoming.columns:
            continue
        exp_series = pd.Series(list(ref_dist.keys()) * 100)  # placeholder weights
        # rebuild expected from proportions
        exp_parts = []
        for cat, pct in ref_dist.items():
            exp_parts.extend([cat] * max(1, int(pct * 1000)))
        exp_series = pd.Series(exp_parts)
        act_series = incoming[col].dropna()
        if len(act_series) < 5:
            continue
        psi = _categorical_psi(exp_series, act_series)
        status = drift_status(psi)
        features.append({
            "feature": col,
            "type": "categorical",
            "psi": round(psi, 4),
            "ks_statistic": None,
            "ks_pvalue": None,
            "status": status,
        })

    if not features:
        overall = "unknown"
    elif any(f["status"] == "red" for f in features):
        overall = "red"
    elif any(f["status"] == "amber" for f in features):
        overall = "amber"
    else:
        overall = "green"

    max_psi = max((f["psi"] for f in features), default=0.0)

    return {
        "overall_status": overall,
        "max_psi": round(max_psi, 4),
        "features": features,
        "thresholds": {"green": PSI_GREEN, "amber": PSI_AMBER},
        "note": (
            "PSI < 0.10 stable (green), 0.10–0.25 moderate drift (amber), > 0.25 significant (red). "
            "In production, amber/red would trigger investigation and likely retrain."
        ),
    }
