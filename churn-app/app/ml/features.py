"""Feature engineering at inference — mirrors ml/feature_engineering.py."""

from __future__ import annotations

import numpy as np
import pandas as pd

SERVICE_COLS = [
    "PhoneService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "MultipleLines",
]


def apply_feature_engineering_row(data: dict) -> dict:
    """Apply engineered features to a single prediction payload."""
    row = dict(data)
    tenure = float(row.get("tenure", 0))
    monthly = float(row.get("MonthlyCharges", 0))
    total = float(row.get("TotalCharges", 0))

    avg = total / max(tenure, 1)
    row["avg_charge_per_month"] = avg
    row["charge_delta"] = monthly - avg

    if tenure <= 12:
        bucket = "0-12"
    elif tenure <= 24:
        bucket = "13-24"
    elif tenure <= 36:
        bucket = "25-36"
    elif tenure <= 48:
        bucket = "37-48"
    else:
        bucket = "49-72"
    row["tenure_bucket"] = bucket
    row["tenure_short"] = int(tenure <= 12)
    row["tenure_long"] = int(tenure > 48)

    count = 0
    for col in SERVICE_COLS:
        if str(row.get(col, "")).lower() == "yes":
            count += 1
    row["service_count"] = count

    pm = str(row.get("PaymentMethod", ""))
    row["is_auto_pay"] = int("automatic" in pm.lower())
    contract = str(row.get("Contract", ""))
    row["contract_month_to_month"] = int(contract == "Month-to-month")
    row["contract_x_electronic_check"] = int(
        contract == "Month-to-month" and pm == "Electronic check"
    )
    return row


def apply_feature_engineering_df(df: pd.DataFrame) -> pd.DataFrame:
    """Apply engineered features to a dataframe."""
    rows = [apply_feature_engineering_row(r.to_dict()) for _, r in df.iterrows()]
    return pd.DataFrame(rows)
