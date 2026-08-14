"""Structured logging with in-memory ring buffer for /logs admin page."""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.config import CHURN_APP_ROOT

LOG_DIR = CHURN_APP_ROOT / "logs"
LOG_FILE = LOG_DIR / "app.log"
MAX_BUFFER = 500

_buffer: deque = deque(maxlen=MAX_BUFFER)
_lock = Lock()
_latency_samples: deque = deque(maxlen=2000)


class JsonRingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_data"):
            entry["data"] = record.extra_data
        with _lock:
            _buffer.appendleft(entry)


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("churnguard")
    if root.handlers:
        return root
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    ring = JsonRingHandler()
    root.addHandler(fh)
    root.addHandler(sh)
    root.addHandler(ring)
    return root


def get_recent_logs(limit: int = 100) -> list[dict]:
    with _lock:
        return list(_buffer)[:limit]


def record_latency_ms(ms: float, endpoint: str) -> None:
    with _lock:
        _latency_samples.append({"ms": ms, "endpoint": endpoint, "ts": datetime.now(timezone.utc).isoformat()})


def latency_stats() -> dict:
    with _lock:
        predict = [s["ms"] for s in _latency_samples if s["endpoint"] == "/api/predict"]
    if not predict:
        return {"avg_ms": 0, "p95_ms": 0, "sample_count": 0}
    predict.sort()
    n = len(predict)
    return {
        "avg_ms": round(sum(predict) / n, 2),
        "p95_ms": round(predict[int(n * 0.95)] if n else 0, 2),
        "sample_count": n,
    }


def log_event(logger: logging.Logger, level: int, msg: str, **data) -> None:
    record = logger.makeRecord(logger.name, level, "", 0, msg, (), None)
    record.extra_data = data
    logger.handle(record)
