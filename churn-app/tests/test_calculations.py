"""Unit tests for business calculation logic."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.business import roi_estimate
from app.ml.predictor import predictor

client = TestClient(app, raise_server_exceptions=False)


def test_roi_estimate_basic():
    result = roi_estimate(
        at_risk_count=100,
        avg_monthly_revenue=70.0,
        retention_offer_cost=15.0,
        customer_lifetime_months=24.0,
        success_rate_pct=25.0,
    )
    assert result["estimated_retained"] == 25.0
    assert result["gross_revenue_saved"] == 25.0 * 70.0 * 24.0
    assert result["total_offer_cost"] == 100 * 15.0
    assert result["net_savings"] == result["gross_revenue_saved"] - result["total_offer_cost"]


def test_roi_estimate_zero_at_risk():
    result = roi_estimate(0, 70.0, 15.0, 24.0, 25.0)
    assert result["estimated_retained"] == 0
    assert result["net_savings"] == 0


@pytest.mark.skipif(not predictor.ready, reason="Model artifacts not loaded")
def test_business_impact_from_stats():
    impact = predictor.business_impact(10.0)
    assert impact["customer_count"] > 0
    assert impact["total_customers"] > 0
    assert impact["monthly_revenue_at_risk"] > 0
    assert impact["is_production_data"] is False


@pytest.mark.skipif(not predictor.ready, reason="Model artifacts not loaded")
def test_impact_calculator_api():
    response = client.post(
        "/api/impact-calculator",
        json={
            "avg_monthly_revenue": 70.0,
            "retention_capacity": 50,
            "top_pct": 10.0,
            "success_rate_pct": 25.0,
            "lifetime_months": 24.0,
            "offer_cost": 15.0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "actionable_customers" in data
    assert "net_savings" in data
    assert data["actionable_customers"] <= 50
