"""Runtime drift detection against training reference profile."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from app.config import DATA_DIR
from app.ml.features import apply_feature_engineering_df

PSI_GREEN = 0.10
PSI_AMBER = 0.25

REFERENCE_PATH = DATA_DIR / "drift_reference.json"


def _load_reference() -> dict | None:
    if not REFERENCE_PATH.exists():
        return None
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))


def _psi_numeric(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
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


def _psi_categorical(ref_dist: dict, actual: pd.Series) -> float:
    eps = 1e-6
    act_counts = actual.astype(str).value_counts(normalize=True)
    cats = set(ref_dist.keys()) | set(act_counts.index)
    psi = 0.0
    for cat in cats:
        e = ref_dist.get(str(cat), eps)
        a = float(act_counts.get(str(cat), 0)) + eps
        psi += (a - e) * np.log(a / e)
    return float(abs(psi))


def _status(psi: float) -> str:
    if psi < PSI_GREEN:
        return "green"
    if psi < PSI_AMBER:
        return "amber"
    return "red"


def check_drift(incoming: pd.DataFrame) -> dict:
    """Compare batch/scoring data to training reference."""
    reference = _load_reference()
    if not reference:
        return {
            "overall_status": "unknown",
            "max_psi": 0,
            "features": [],
            "note": "Training reference not found. Run train_model.py.",
        }

    df = apply_feature_engineering_df(incoming)
    features = []

    for col, ref in reference.get("numeric", {}).items():
        if col not in df.columns:
            continue
        actual = pd.to_numeric(df[col], errors="coerce").dropna().values
        expected = np.array(ref.get("sample", []))
        if len(actual) < 5 or len(expected) < 5:
            continue
        psi = _psi_numeric(expected, actual)
        ks_stat, ks_p = stats.ks_2samp(expected, actual)
        features.append({
            "feature": col,
            "type": "numeric",
            "psi": round(psi, 4),
            "ks_statistic": round(float(ks_stat), 4),
            "ks_pvalue": round(float(ks_p), 4),
            "status": _status(psi),
        })

    for col, ref_dist in reference.get("categorical", {}).items():
        if col not in df.columns:
            continue
        act = df[col].dropna()
        if len(act) < 5:
            continue
        psi = _psi_categorical(ref_dist, act)
        features.append({
            "feature": col,
            "type": "categorical",
            "psi": round(psi, 4),
            "ks_statistic": None,
            "ks_pvalue": None,
            "status": _status(psi),
        })

    if not features:
        overall = "unknown"
    elif any(f["status"] == "red" for f in features):
        overall = "red"
    elif any(f["status"] == "amber" for f in features):
        overall = "amber"
    else:
        overall = "green"

    return {
        "overall_status": overall,
        "max_psi": round(max((f["psi"] for f in features), default=0.0), 4),
        "features": features,
        "thresholds": {"green": PSI_GREEN, "amber": PSI_AMBER},
        "note": (
            "PSI vs training distribution. Amber/red drift would trigger retrain in production."
        ),
    }
