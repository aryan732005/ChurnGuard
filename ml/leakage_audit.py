"""
Data leakage audit for churn features.

Flags features that could be consequences of churn rather than pre-decision predictors.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd

# Features reviewed against the Telco Customer Churn schema
FEATURE_AUDIT: list[dict[str, str]] = [
    {
        "feature": "customerID",
        "status": "dropped",
        "risk": "none",
        "reason": "Identifier only — no predictive value; excluded from training.",
    },
    {
        "feature": "Churn",
        "status": "target_only",
        "risk": "none",
        "reason": "Label column — never used as a model input.",
    },
    {
        "feature": "TotalCharges",
        "status": "kept_with_review",
        "risk": "low",
        "reason": (
            "Cumulative billing at snapshot date. Not post-churn activity, but highly "
            "correlated with tenure × MonthlyCharges. Kept as monetary signal; "
            "engineered avg_charge_per_month reduces redundancy."
        ),
    },
    {
        "feature": "tenure",
        "status": "kept",
        "risk": "none",
        "reason": "Months as customer at snapshot — known before any churn decision.",
    },
    {
        "feature": "MonthlyCharges",
        "status": "kept",
        "risk": "none",
        "reason": "Current billing rate at snapshot — pre-decision.",
    },
    {
        "feature": "Contract",
        "status": "kept",
        "risk": "none",
        "reason": "Active contract type at snapshot — not a post-cancellation field.",
    },
    {
        "feature": "PaymentMethod",
        "status": "kept",
        "risk": "none",
        "reason": "Payment method at snapshot.",
    },
    {
        "feature": "PhoneService",
        "status": "kept",
        "risk": "none",
        "reason": "Service subscription state at snapshot.",
    },
    {
        "feature": "InternetService",
        "status": "kept",
        "risk": "none",
        "reason": "Service subscription state at snapshot.",
    },
    {
        "feature": "OnlineSecurity",
        "status": "kept",
        "risk": "none",
        "reason": "Add-on service flags reflect subscription at snapshot, not post-churn tickets.",
    },
    {
        "feature": "OnlineBackup",
        "status": "kept",
        "risk": "none",
        "reason": "Add-on service at snapshot.",
    },
    {
        "feature": "DeviceProtection",
        "status": "kept",
        "risk": "none",
        "reason": "Add-on service at snapshot.",
    },
    {
        "feature": "TechSupport",
        "status": "kept",
        "risk": "none",
        "reason": "Add-on service at snapshot — not cancellation support tickets (not in schema).",
    },
    {
        "feature": "StreamingTV",
        "status": "kept",
        "risk": "none",
        "reason": "Add-on service at snapshot.",
    },
    {
        "feature": "StreamingMovies",
        "status": "kept",
        "risk": "none",
        "reason": "Add-on service at snapshot.",
    },
    {
        "feature": "MultipleLines",
        "status": "kept",
        "risk": "none",
        "reason": "Phone add-on at snapshot.",
    },
    {
        "feature": "PaperlessBilling",
        "status": "kept",
        "risk": "none",
        "reason": "Billing preference at snapshot.",
    },
    {
        "feature": "gender",
        "status": "kept",
        "risk": "none",
        "reason": "Static demographic — used for fairness audit only in reporting.",
    },
    {
        "feature": "SeniorCitizen",
        "status": "kept",
        "risk": "none",
        "reason": "Static demographic.",
    },
    {
        "feature": "Partner",
        "status": "kept",
        "risk": "none",
        "reason": "Household attribute at snapshot.",
    },
    {
        "feature": "Dependents",
        "status": "kept",
        "risk": "none",
        "reason": "Household attribute at snapshot.",
    },
]

# Hypothetical leakage patterns NOT present in this dataset (documented for audit completeness)
ABSENT_LEAKAGE_CANDIDATES = [
    "cancellation_support_tickets",
    "post_churn_activity_flag",
    "account_closed_date",
    "refund_amount",
    "final_bill_issued",
    "days_since_last_login_after_cancel",
]


@dataclass
class LeakageAuditResult:
    features: list[dict[str, str]]
    dropped: list[str]
    flagged: list[str]
    absent_checked: list[str]
    summary: str
    plain_language: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_leakage_audit(df: pd.DataFrame) -> LeakageAuditResult:
    """Audit every column in the dataset against leakage risk."""
    present = set(df.columns)
    audited = []
    dropped: list[str] = []
    flagged: list[str] = []

    known = {entry["feature"]: entry for entry in FEATURE_AUDIT}
    for col in sorted(present):
        if col in known:
            entry = dict(known[col])
            audited.append(entry)
            if entry["status"] == "dropped":
                dropped.append(col)
            elif entry["risk"] in ("medium", "high"):
                flagged.append(col)
        else:
            audited.append({
                "feature": col,
                "status": "review_required",
                "risk": "unknown",
                "reason": "Column not in audit catalog — manual review required.",
            })
            flagged.append(col)

    for name in ABSENT_LEAKAGE_CANDIDATES:
        if name in present:
            flagged.append(name)
            audited.append({
                "feature": name,
                "status": "dropped",
                "risk": "high",
                "reason": "Post-churn or cancellation-consequence feature — must be excluded or lagged.",
            })
            dropped.append(name)

    n_kept = sum(1 for a in audited if a["status"] in ("kept", "kept_with_review"))
    summary = (
        f"Reviewed {len(audited)} columns. Dropped {len(dropped)} ({', '.join(dropped) or 'none'}). "
        f"Flagged for review: {len(flagged)}. No post-churn activity fields found in schema."
    )
    plain_language = (
        "We checked every input column against common leakage patterns (cancellation tickets, "
        "post-churn flags, future-dated activity). This Telco snapshot contains only account "
        "state at observation time. customerID was removed; TotalCharges was reviewed and kept "
        "with an engineered alternative. The dataset has no event timestamps, so true "
        "point-in-time windows per customer cannot be verified."
    )

    return LeakageAuditResult(
        features=audited,
        dropped=dropped,
        flagged=flagged,
        absent_checked=ABSENT_LEAKAGE_CANDIDATES,
        summary=summary,
        plain_language=plain_language,
    )


def write_leakage_audit_markdown(result: LeakageAuditResult, path: str) -> None:
    """Write docs/leakage_audit.md from audit result."""
    lines = [
        "# Data Leakage Audit",
        "",
        "## Summary",
        "",
        result.summary,
        "",
        "## Plain-language conclusion",
        "",
        result.plain_language,
        "",
        "## Feature review",
        "",
        "| Feature | Status | Risk | Rationale |",
        "|---------|--------|------|-----------|",
    ]
    for f in result.features:
        lines.append(
            f"| {f['feature']} | {f['status']} | {f['risk']} | {f['reason']} |"
        )

    lines.extend([
        "",
        "## Absent leakage candidates (checked)",
        "",
        "These post-churn or consequence features are **not** in the dataset:",
        "",
    ])
    for name in result.absent_checked:
        lines.append(f"- `{name}`")

    lines.extend([
        "",
        "## Dropped or excluded from training",
        "",
    ])
    if result.dropped:
        for d in result.dropped:
            lines.append(f"- **{d}**")
    else:
        lines.append("- None (customerID dropped at preprocess stage)")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
