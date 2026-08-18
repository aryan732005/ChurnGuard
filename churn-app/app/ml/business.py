"""Business-facing retention recommendations and ROI helpers."""

from __future__ import annotations

FEATURE_ACTIONS = [
    ("contract month to month", "Offer loyalty discount or upgrade from month-to-month plan"),
    ("contract_x_electronic", "Convert to auto-pay and offer a contract incentive"),
    ("tenure short", "Early-tenure engagement and onboarding check-in"),
    ("tenure long", "Schedule renewal review before contract end"),
    ("charge delta", "Review billing anomalies and offer a plan adjustment"),
    ("avg charge per month", "Review billing and usage-based plan options"),
    ("monthlycharges", "Review billing and offer loyalty pricing"),
    ("electronic check", "Incentivize switch to automatic bank/card payment"),
    ("mailed check", "Convert to paperless auto-pay with a small credit"),
    ("paperlessbilling", "Confirm satisfaction with digital billing"),
    ("internet fiber", "Bundle tech support or online security for fiber customers"),
    ("internet dsl", "Upsell speed or security package to improve value"),
    ("onlinesecurity", "Offer discounted online security bundle"),
    ("techsupport", "Proactive support outreach and dedicated help session"),
    ("streaming", "Bundle streaming with support to increase stickiness"),
    ("service count", "Cross-sell complementary services to deepen engagement"),
    ("seniorcitizen", "Senior-focused support and simplified billing review"),
    ("partner", "Household or multi-line retention offer"),
    ("dependents", "Multi-line household plan review"),
    ("is auto pay", "Encourage automatic payment with a loyalty credit"),
]

DEFAULT_ACTION = "Proactive retention outreach — schedule account review call"
MONITOR_ACTION = "Monitor quarterly — no immediate outreach"


def _normalize_feature(name: str) -> str:
    return name.lower().replace("_", " ").replace("-", " ")


def recommended_action(top_factors: list[dict], *, predicted_churn: bool = True) -> str:
    """Map top churn-increasing factors to a retention play."""
    if not predicted_churn:
        return MONITOR_ACTION
    if not top_factors:
        return DEFAULT_ACTION

    for factor in top_factors:
        feat = _normalize_feature(factor.get("feature", ""))
        for key, action in FEATURE_ACTIONS:
            if key.replace(" ", "") in feat.replace(" ", ""):
                return action

    top = top_factors[0].get("feature", "risk signals")
    return f"Address primary driver ({top}) with a targeted retention offer"


def roi_estimate(
    at_risk_count: int,
    avg_monthly_revenue: float,
    retention_offer_cost: float,
    customer_lifetime_months: float,
    success_rate_pct: float,
) -> dict:
    """Simple ROI: savings from retained customers minus offer cost."""
    rate = max(0.0, min(100.0, success_rate_pct)) / 100.0
    retained = at_risk_count * rate
    gross_saved = retained * avg_monthly_revenue * customer_lifetime_months
    total_offer_cost = at_risk_count * retention_offer_cost
    net = gross_saved - total_offer_cost

    return {
        "at_risk_count": at_risk_count,
        "estimated_retained": round(retained, 1),
        "gross_revenue_saved": round(gross_saved, 2),
        "total_offer_cost": round(total_offer_cost, 2),
        "net_savings": round(net, 2),
        "roi_pct": round((net / total_offer_cost * 100) if total_offer_cost else 0, 1),
    }
