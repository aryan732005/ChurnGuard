"""Input sanitization for API payloads and uploads."""

from __future__ import annotations

import re

ALLOWED_PREDICT_FIELDS = {
    "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
    "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity",
    "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
    "StreamingMovies", "Contract", "PaperlessBilling", "PaymentMethod",
    "MonthlyCharges", "TotalCharges",
}

_STRING_FIELDS = {
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
    "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod",
}

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_string(value: str, max_len: int = 64) -> str:
    cleaned = _CONTROL_CHARS.sub("", str(value)).strip()
    return cleaned[:max_len]


def sanitize_prediction_payload(data: dict) -> tuple[dict, list[str]]:
    """Strip unknown fields and sanitize strings. Returns (clean, errors)."""
    errors: list[str] = []
    extra = set(data.keys()) - ALLOWED_PREDICT_FIELDS
    if extra:
        errors.append(f"Unexpected fields rejected: {', '.join(sorted(extra))}")

    clean: dict = {}
    for key in ALLOWED_PREDICT_FIELDS:
        if key not in data:
            continue
        val = data[key]
        if key in _STRING_FIELDS:
            clean[key] = sanitize_string(val)
        else:
            clean[key] = val
    return clean, errors
