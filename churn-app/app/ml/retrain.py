"""Simulated retrain on combined dataset (demo only — does not replace production model)."""

from __future__ import annotations

import io
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from app.config import DATA_DIR


def _quick_preprocess(df: pd.DataFrame):
    """Lightweight preprocessing aligned with main pipeline."""
    df = df.copy()
    if "customerID" in df.columns:
        df = df.drop(columns=["customerID"])
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df["TotalCharges"] = df["TotalCharges"].fillna(df["TotalCharges"].median())

    if df["Churn"].dtype == object:
        le_churn = LabelEncoder()
        df["Churn"] = le_churn.fit_transform(df["Churn"])

    binary_cols = ["gender", "Partner", "Dependents", "PhoneService", "PaperlessBilling"]
    for col in binary_cols:
        if col in df.columns and df[col].dtype == object:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))

    multi_cols = [
        "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
        "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
        "Contract", "PaymentMethod",
    ]
    present = [c for c in multi_cols if c in df.columns]
    df = pd.get_dummies(df, columns=present, drop_first=True)

    y = df["Churn"].values
    X = df.drop(columns=["Churn"])
    return X, y, list(X.columns)


def _train_and_score(X, y) -> dict[str, float]:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )
    model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    model.fit(X_train, y_train)
    prob = model.predict_proba(X_test)[:, 1]
    pred = model.predict(X_test)
    return {
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "f1_score": round(float(f1_score(y_test, pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, prob)), 4),
        "train_rows": len(y_train),
        "test_rows": len(y_test),
    }


def simulate_retrain(upload_csv: bytes, current_metrics: dict) -> dict[str, Any]:
    """
    Combine uploaded CSV with existing telco data, retrain a quick LR model,
    return before/after metrics. Simulation only.
    """
    base_path = DATA_DIR / "telco_churn.csv"
    if not base_path.exists():
        raise ValueError("Base dataset not found.")

    base_df = pd.read_csv(base_path)
    upload_df = pd.read_csv(io.BytesIO(upload_csv))

    if "Churn" not in upload_df.columns:
        raise ValueError('Uploaded CSV must include a "Churn" column for simulation retraining.')

    combined = pd.concat([base_df, upload_df], ignore_index=True)
    if "customerID" in combined.columns:
        combined = combined.drop_duplicates(subset=["customerID"])

    before = {
        "accuracy": current_metrics.get("accuracy", 0),
        "f1_score": current_metrics.get("f1_score", 0),
        "roc_auc": current_metrics.get("roc_auc", 0),
        "label": "Before (current production model)",
        "rows": len(base_df),
    }

    X, y, _ = _quick_preprocess(combined)
    after_scores = _train_and_score(X, y)
    after = {
        **after_scores,
        "label": "After (simulation retrain)",
        "rows": len(combined),
        "added_rows": len(upload_df),
    }

    return {
        "simulation": True,
        "note": (
            "This is a demonstration retrain using Logistic Regression on combined data. "
            "Production model artifacts are not overwritten."
        ),
        "before": before,
        "after": after,
        "delta": {
            "accuracy": round(after["accuracy"] - before["accuracy"], 4),
            "f1_score": round(after["f1_score"] - before["f1_score"], 4),
            "roc_auc": round(after["roc_auc"] - before["roc_auc"], 4),
        },
    }
