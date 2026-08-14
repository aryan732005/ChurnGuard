"""Business-facing retention recommendations and ROI helpers."""

from __future__ import annotations

FEATURE_ACTIONS = {
    "contract_month": "Offer contract discount or upgrade to a one/two-year plan",
    "contract_one": "Propose two-year loyalty pricing before renewal window",
    "contract_two": "Schedule renewal check-in and bundle add-on services",
    "tenure": "Proactive onboarding and early-tenure engagement outreach",
    "monthlycharges": "Review billing and offer loyalty pricing or plan adjustment",
    "internet fiber": "Bundle tech support or online security for fiber customers",
    "internet dsl": "Upsell speed/security package to improve perceived value",
    "payment electronic": "Incentivize switch to automatic bank/card payment",
    "payment mailed": "Convert to paperless auto-pay with a small credit",
    "onlinesecurity": "Offer discounted online security or device protection bundle",
    "techsupport": "Proactive support outreach and dedicated help session",
    "paperlessbilling": "Engagement touchpoint — confirm satisfaction with digital billing",
    "streaming": "Bundle streaming with support/security to increase stickiness",
    "partner": "Family/household retention offer for single-account customers",
    "dependents": "Multi-line household plan review",
    "seniorcitizen": "Senior-focused support and simplified billing review",
}

DEFAULT_ACTION = "Proactive retention outreach — schedule account review call"


def _normalize_feature(name: str) -> str:
    return name.lower().replace("_", " ").replace("-", " ")


def recommended_action(top_factors: list[dict]) -> str:
    """Map top SHAP/coefficient factor to a retention play."""
    if not top_factors:
        return DEFAULT_ACTION

    for factor in top_factors:
        feat = _normalize_feature(factor.get("feature", ""))
        for key, action in FEATURE_ACTIONS.items():
            if key.replace(" ", "") in feat.replace(" ", ""):
                return action

    top = top_factors[0].get("feature", "risk signals")
    return f"Address primary driver ({top}) with targeted retention offer"


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
