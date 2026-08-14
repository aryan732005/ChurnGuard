"""
Feature engineering for churn prediction.

Applied on raw dataframe before label encoding / one-hot encoding.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SERVICE_COLS = [
    "PhoneService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "MultipleLines",
]

ENGINEERED_FEATURES_DOC = [
    {
        "name": "tenure_bucket",
        "rationale": "Non-linear tenure effect — early-tenure customers churn differently from veterans.",
    },
    {
        "name": "avg_charge_per_month",
        "rationale": "Monetary (M): average spend rate = TotalCharges / tenure — normalises cumulative billing.",
    },
    {
        "name": "charge_delta",
        "rationale": "Trend proxy: MonthlyCharges minus avg_charge_per_month — rising bill vs historical average.",
    },
    {
        "name": "service_count",
        "rationale": "Frequency proxy: count of active add-on services (Yes responses).",
    },
    {
        "name": "is_auto_pay",
        "rationale": "Automatic payment methods correlate with lower involuntary churn.",
    },
    {
        "name": "contract_month_to_month",
        "rationale": "High-risk contract flag for interaction with payment method.",
    },
    {
        "name": "contract_x_electronic_check",
        "rationale": "Interaction: month-to-month + electronic check — highest-risk combo in Telco literature.",
    },
    {
        "name": "tenure_short",
        "rationale": "Binary: tenure ≤ 12 months (recency proxy — new customers).",
    },
    {
        "name": "tenure_long",
        "rationale": "Binary: tenure > 48 months (loyalty proxy).",
    },
]


def apply_feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineered columns to a copy of the raw customer dataframe."""
    out = df.copy()

    if "TotalCharges" in out.columns:
        out["TotalCharges"] = pd.to_numeric(out["TotalCharges"], errors="coerce")
        out["TotalCharges"] = out["TotalCharges"].fillna(out["TotalCharges"].median())

    tenure = out["tenure"].astype(float).clip(lower=0)
    monthly = out["MonthlyCharges"].astype(float)

    out["avg_charge_per_month"] = out["TotalCharges"] / np.maximum(tenure, 1)
    out["charge_delta"] = monthly - out["avg_charge_per_month"]

    out["tenure_bucket"] = pd.cut(
        tenure,
        bins=[-1, 12, 24, 36, 48, 72],
        labels=["0-12", "13-24", "25-36", "37-48", "49-72"],
    ).astype(str)

    out["tenure_short"] = (tenure <= 12).astype(int)
    out["tenure_long"] = (tenure > 48).astype(int)

    def _is_yes(series: pd.Series) -> pd.Series:
        return series.astype(str).str.lower().eq("yes").astype(int)

    svc_cols = [c for c in SERVICE_COLS if c in out.columns]
    if svc_cols:
        out["service_count"] = sum(_is_yes(out[c]) for c in svc_cols)
    else:
        out["service_count"] = 0

    if "PaymentMethod" in out.columns:
        out["is_auto_pay"] = out["PaymentMethod"].str.contains("automatic", case=False, na=False).astype(int)
    else:
        out["is_auto_pay"] = 0

    if "Contract" in out.columns:
        out["contract_month_to_month"] = (out["Contract"] == "Month-to-month").astype(int)
        if "PaymentMethod" in out.columns:
            out["contract_x_electronic_check"] = (
                (out["Contract"] == "Month-to-month")
                & (out["PaymentMethod"] == "Electronic check")
            ).astype(int)
        else:
            out["contract_x_electronic_check"] = 0
    else:
        out["contract_month_to_month"] = 0
        out["contract_x_electronic_check"] = 0

    return out


def write_feature_engineering_markdown(path: str) -> None:
    """Write docs/feature_engineering.md."""
    lines = [
        "# Feature Engineering",
        "",
        "Engineered features are computed from snapshot-time columns only (no future information).",
        "",
        "| Feature | Rationale |",
        "|---------|-----------|",
    ]
    for entry in ENGINEERED_FEATURES_DOC:
        lines.append(f"| `{entry['name']}` | {entry['rationale']} |")

    lines.extend([
        "",
        "## Raw features retained",
        "",
        "Demographics (gender, SeniorCitizen, Partner, Dependents), tenure, contract, ",
        "payment method, service flags, MonthlyCharges, and TotalCharges (reviewed in leakage audit).",
        "",
        "## Recency / frequency / monetary",
        "",
        "- **Recency:** `tenure`, `tenure_short`, `tenure_long`, `tenure_bucket`",
        "- **Frequency:** `service_count` (active add-ons)",
        "- **Monetary:** `MonthlyCharges`, `avg_charge_per_month`, `charge_delta`",
        "",
        "## Interactions",
        "",
        "`contract_x_electronic_check` captures the high-risk month-to-month + electronic check segment.",
    ])

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
