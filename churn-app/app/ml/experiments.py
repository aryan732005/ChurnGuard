"""Experiment runs: MLflow + stats.json fallback + retrain simulations."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import DATA_DIR, REPO_ROOT

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.mlflow_tracking import get_run_detail, list_mlflow_runs  # noqa: E402

RETRAIN_RUNS_PATH = DATA_DIR / "retrain_experiments.json"


def _load_stats() -> dict:
    path = DATA_DIR / "stats.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _stats_experiments(stats: dict) -> list[dict]:
    """Synthetic experiment rows from model_results (always available after train)."""
    results = stats.get("model_results", {})
    if not results:
        return []
    version = stats.get("model_version", {})
    base_date = version.get("date", "Training snapshot")
    rows = []
    for idx, (name, m) in enumerate(results.items()):
        rows.append({
            "run_id": f"stats-{idx}",
            "full_run_id": f"stats-{idx}",
            "date": base_date,
            "start_time": 0,
            "model_type": name,
            "accuracy": m.get("accuracy", 0),
            "precision": m.get("precision", 0),
            "recall": m.get("recall", 0),
            "f1_score": m.get("f1_score", 0),
            "roc_auc": m.get("roc_auc", 0),
            "pr_auc": m.get("pr_auc", 0),
            "model_version": version.get("version", "—"),
            "status": "completed",
            "source": "stats",
            "is_best": name == stats.get("best_model"),
        })
    return rows


def _load_retrain_runs() -> list[dict]:
    if not RETRAIN_RUNS_PATH.exists():
        return []
    return json.loads(RETRAIN_RUNS_PATH.read_text(encoding="utf-8"))


def save_retrain_experiment(payload: dict) -> dict:
    """Persist a retrain simulation as an experiment row."""
    runs = _load_retrain_runs()
    run_id = f"sim-{uuid.uuid4().hex[:8]}"
    entry = {
        "run_id": run_id,
        "full_run_id": run_id,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "start_time": int(datetime.now(timezone.utc).timestamp() * 1000),
        "model_type": "Retrain simulation (Logistic Regression)",
        "accuracy": payload.get("after", {}).get("accuracy", 0),
        "precision": 0,
        "recall": 0,
        "f1_score": payload.get("after", {}).get("f1_score", 0),
        "roc_auc": payload.get("after", {}).get("roc_auc", 0),
        "model_version": "simulation",
        "status": "completed",
        "source": "retrain_simulation",
        "detail": payload,
    }
    runs.insert(0, entry)
    RETRAIN_RUNS_PATH.write_text(json.dumps(runs[:50], indent=2), encoding="utf-8")
    return entry


def list_runs(
    model_type: str = "",
    date_from: str = "",
    limit: int = 100,
) -> list[dict]:
    """Merge MLflow runs, stats.json models, and retrain simulations."""
    stats = _load_stats()
    seen_names: set[str] = set()
    merged: list[dict] = []

    for r in list_mlflow_runs(limit=limit):
        r["source"] = "mlflow"
        r["status"] = r.get("status", "completed")
        merged.append(r)
        seen_names.add(r.get("model_type", ""))

    for r in _stats_experiments(stats):
        if r["model_type"] not in seen_names or r["source"] == "stats":
            merged.append(r)

    for r in _load_retrain_runs():
        merged.append(r)

    if model_type:
        q = model_type.lower()
        merged = [r for r in merged if q in r.get("model_type", "").lower()]

    if date_from:
        merged = [r for r in merged if r.get("date", "") >= date_from]

    merged.sort(key=lambda x: x.get("start_time", 0), reverse=True)
    return merged[:limit]


def get_run(run_id: str) -> dict | None:
    if run_id.startswith("sim-"):
        for r in _load_retrain_runs():
            if r["full_run_id"] == run_id or r["run_id"] == run_id:
                return _enrich_detail(r)
        return None

    if run_id.startswith("stats-"):
        stats = _load_stats()
        for r in _stats_experiments(stats):
            if r["full_run_id"] == run_id:
                return _enrich_detail(r, stats)
        return None

    detail = get_run_detail(run_id)
    if detail:
        detail["source"] = "mlflow"
        return _enrich_detail(detail)
    return None


def _enrich_detail(row: dict, stats: dict | None = None) -> dict:
    stats = stats or _load_stats()
    name = row.get("model_type", "")
    m = stats.get("model_results", {}).get(name, {})
    cm = m.get("confusion_matrix")
    if not cm and name == stats.get("best_model"):
        cm = stats.get("best_model_confusion_matrix")
    roc = stats.get("roc_curve", {}) if name == stats.get("best_model") else {}
    pr = stats.get("pr_curve", {}) if name == stats.get("best_model") else {}

    params = row.get("params") or {}
    if not params and m:
        params = {k: v for k, v in m.items() if k.startswith("cv_") or k in ("accuracy", "roc_auc")}
    if row.get("detail"):
        params = {"simulation": True, **(row.get("detail", {}).get("delta", {}))}

    return {
        **row,
        "hyperparameters": params if isinstance(params, dict) else {},
        "confusion_matrix": cm,
        "roc_curve": roc if name == stats.get("best_model") else {},
        "pr_curve": pr if name == stats.get("best_model") else {},
        "per_class": m.get("per_class", stats.get("best_model_per_class", {})),
        "note": row.get("detail", {}).get("note") if row.get("source") == "retrain_simulation" else "",
    }


def compare_runs(run_ids: list[str]) -> dict:
    runs = []
    for rid in run_ids[:3]:
        r = get_run(rid)
        if r:
            runs.append(r)
    return {"runs": runs, "count": len(runs)}
