"""MLflow experiment tracking for training runs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
MLRUNS_DIR = BASE_DIR / "mlruns"
EXPERIMENT_NAME = "churnguard-training"


def _ensure_mlflow():
    import mlflow
    os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    MLRUNS_DIR.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(str(MLRUNS_DIR.as_uri()))
    mlflow.set_experiment(EXPERIMENT_NAME)
    return mlflow


def log_training_run(
    params: dict[str, Any],
    metrics: dict[str, float],
    model,
    scaler,
    feature_names: list[str],
    tags: dict[str, str] | None = None,
) -> str:
    """Log a full training run; returns MLflow run_id."""
    mlflow = _ensure_mlflow()
    with mlflow.start_run(run_name=tags.get("run_name") if tags else None) as run:
        for k, v in params.items():
            mlflow.log_param(k, v)
        for k, v in metrics.items():
            mlflow.log_metric(k, float(v))
        if tags:
            mlflow.set_tags(tags)
        import mlflow.sklearn
        mlflow.sklearn.log_model(model, "churn_model")
        import pickle
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pickle.dump(scaler, open(tmp_path / "scaler.pkl", "wb"))
            pickle.dump(feature_names, open(tmp_path / "feature_names.pkl", "wb"))
            mlflow.log_artifacts(str(tmp_path))
        return run.info.run_id


def list_mlflow_runs(limit: int = 50) -> list[dict]:
    """List past MLflow runs."""
    try:
        from mlflow.tracking import MlflowClient
        _ensure_mlflow()
        client = MlflowClient()
        exp = client.get_experiment_by_name(EXPERIMENT_NAME)
        if exp is None:
            return []
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=["start_time DESC"],
            max_results=limit,
        )
        out = []
        for r in runs:
            m = r.data.metrics
            p = r.data.params
            status = r.info.status or "FINISHED"
            status_map = {"FINISHED": "completed", "FAILED": "failed", "RUNNING": "running"}
            out.append({
                "run_id": r.info.run_id[:8],
                "full_run_id": r.info.run_id,
                "start_time": r.info.start_time or 0,
                "date": _format_ts(r.info.start_time),
                "model_type": p.get("best_model", p.get("model_type", "—")),
                "accuracy": round(m.get("accuracy", 0), 4),
                "precision": round(m.get("precision", 0), 4),
                "recall": round(m.get("recall", 0), 4),
                "f1_score": round(m.get("f1_score", 0), 4),
                "roc_auc": round(m.get("roc_auc", 0), 4),
                "pr_auc": round(m.get("pr_auc", 0), 4),
                "model_version": r.data.tags.get("model_version", "—"),
                "status": status_map.get(status, "completed"),
                "params": dict(p),
            })
        return out
    except Exception:
        return []


def get_run_detail(run_id: str) -> dict | None:
    """Fetch single MLflow run by full or partial id."""
    try:
        from mlflow.tracking import MlflowClient
        _ensure_mlflow()
        client = MlflowClient()
        # Resolve partial id
        full_id = run_id
        if len(run_id) <= 8:
            exp = client.get_experiment_by_name(EXPERIMENT_NAME)
            if not exp:
                return None
            for r in client.search_runs([exp.experiment_id], max_results=200):
                if r.info.run_id.startswith(run_id):
                    full_id = r.info.run_id
                    break
        run = client.get_run(full_id)
        m = run.data.metrics
        p = run.data.params
        status_map = {"FINISHED": "completed", "FAILED": "failed", "RUNNING": "running"}
        return {
            "run_id": full_id[:8],
            "full_run_id": full_id,
            "start_time": run.info.start_time or 0,
            "date": _format_ts(run.info.start_time),
            "model_type": p.get("best_model", "—"),
            "accuracy": round(m.get("accuracy", 0), 4),
            "precision": round(m.get("precision", 0), 4),
            "recall": round(m.get("recall", 0), 4),
            "f1_score": round(m.get("f1_score", 0), 4),
            "roc_auc": round(m.get("roc_auc", 0), 4),
            "pr_auc": round(m.get("pr_auc", 0), 4),
            "model_version": run.data.tags.get("model_version", "—"),
            "status": status_map.get(run.info.status or "FINISHED", "completed"),
            "params": dict(p),
        }
    except Exception:
        return None


def list_runs(limit: int = 50) -> list[dict]:
    """Backward-compatible alias."""
    return list_mlflow_runs(limit)


def _format_ts(ms: int | None) -> str:
    if not ms:
        return "—"
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
