"""Input validation for prediction forms and CSV uploads."""

from __future__ import annotations

import pandas as pd

REQUIRED_CSV_COLUMNS = [
    "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
    "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity",
    "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
    "StreamingMovies", "Contract", "PaperlessBilling", "PaymentMethod",
    "MonthlyCharges", "TotalCharges",
]

OPTIONAL_CSV_COLUMNS = ["customerID", "Churn"]

NUMERIC_FIELDS = {"tenure", "SeniorCitizen", "MonthlyCharges", "TotalCharges"}


def validate_prediction_input(data: dict) -> list[str]:
    """Validate single-customer prediction payload. Returns user-facing errors."""
    errors: list[str] = []

    try:
        tenure = int(data.get("tenure", ""))
        if tenure < 0 or tenure > 72:
            errors.append("Tenure must be between 0 and 72 months.")
    except (TypeError, ValueError):
        errors.append("Tenure must be a whole number between 0 and 72.")

    try:
        monthly = float(data.get("MonthlyCharges", ""))
        if monthly < 0 or monthly > 200:
            errors.append("Monthly charges must be between $0 and $200.")
    except (TypeError, ValueError):
        errors.append("Monthly charges must be a valid dollar amount.")

    try:
        total = float(data.get("TotalCharges", ""))
        if total < 0:
            errors.append("Total charges cannot be negative.")
    except (TypeError, ValueError):
        errors.append("Total charges must be a valid dollar amount.")

    phone = data.get("PhoneService", "Yes")
    multiple_lines = data.get("MultipleLines", "No")
    if phone == "No" and multiple_lines not in ("No phone service", "No"):
        errors.append('If phone service is No, multiple lines must be "No phone service".')

    internet = data.get("InternetService", "DSL")
    if internet == "No":
        for field in [
            "OnlineSecurity", "OnlineBackup", "DeviceProtection",
            "TechSupport", "StreamingTV", "StreamingMovies",
        ]:
            val = data.get(field, "No")
            if val not in ("No internet service", "No"):
                label = field.replace("Online", "Online ").replace("DeviceProtection", "Device Protection")
                errors.append(f'{label} must be "No internet service" when internet service is No.')

    return errors


def validate_csv_upload(df: pd.DataFrame | None, raw_size: int) -> list[str]:
    """Validate batch CSV structure and types."""
    errors: list[str] = []

    if raw_size == 0:
        errors.append("The uploaded file is empty.")
        return errors

    if df is None or df.empty:
        errors.append("No rows found in the CSV file.")
        return errors

    if len(df.columns) == 0:
        errors.append("The CSV has no columns.")
        return errors

    missing = [c for c in REQUIRED_CSV_COLUMNS if c not in df.columns]
    if missing:
        errors.append(
            "Missing required columns: " + ", ".join(missing[:8])
            + ("…" if len(missing) > 8 else "")
        )

    for col in NUMERIC_FIELDS:
        if col not in df.columns:
            continue
        coerced = pd.to_numeric(df[col], errors="coerce")
        if coerced.isna().all():
            errors.append(f'Column "{col}" must contain numeric values.')
        elif coerced.isna().any():
            bad = int(coerced.isna().sum())
            errors.append(f'Column "{col}" has {bad} non-numeric value(s).')

    return errors
