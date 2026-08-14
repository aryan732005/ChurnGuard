"""Model version tagging and history."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def register_model_version(
    data_dir: Path,
    model_name: str,
    roc_auc: float,
    mlflow_run_id: str = "",
) -> dict[str, Any]:
    """Bump version, append history, return current version info."""
    history_path = data_dir / "model_versions.json"
    history: list[dict] = []
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))

    prev_auc = history[-1]["roc_auc"] if history else None
    version_num = len(history) + 1
    now = datetime.now(timezone.utc)

    entry = {
        "version": f"v{version_num}.0",
        "version_num": version_num,
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d %H:%M UTC"),
        "model_name": model_name,
        "roc_auc": round(float(roc_auc), 4),
        "roc_auc_delta": round(float(roc_auc - prev_auc), 4) if prev_auc is not None else None,
        "mlflow_run_id": mlflow_run_id,
    }
    history.append(entry)
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

    # NOTE: Training writes artifacts to models/ and updates model_version.json.
    # The running app loads artifacts at startup; after train_model.py completes,
    # restart the service (or implement a reload hook) to promote the new model live.
    # There is no automatic hot-swap — deployment should treat model/ stats/ updates
    # as a release step (see churn-app/README.md § Deployment & model versioning).

    current = {
        **entry,
        "history": history[-10:],
    }
    (data_dir / "model_version.json").write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current
