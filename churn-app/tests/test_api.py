"""Integration tests for the prediction API."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.predictor import predictor

client = TestClient(app, raise_server_exceptions=False)

VALID_BODY = {
    "gender": "Male",
    "SeniorCitizen": 0,
    "Partner": "No",
    "Dependents": "No",
    "tenure": 12,
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "Fiber optic",
    "OnlineSecurity": "No",
    "OnlineBackup": "No",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 70.0,
    "TotalCharges": 840.0,
}


@pytest.mark.skipif(not predictor.ready, reason="Model artifacts not loaded")
def test_predict_success():
    response = client.post("/api/predict", json=VALID_BODY)
    assert response.status_code == 200
    data = response.json()
    assert "churn_probability" in data
    assert data["prediction"] in ("Churn", "Retained")
    assert data["risk_level"] in ("Low", "Medium", "High")
    assert 0 <= data["churn_probability"] <= 100


def test_predict_validation_error():
    body = {**VALID_BODY, "tenure": 999}
    response = client.post("/api/predict", json=body)
    assert response.status_code == 422


def test_predict_business_rule_rejected():
    body = {
        **VALID_BODY,
        "PhoneService": "No",
        "MultipleLines": "Yes",
        "tenure": 12,
    }
    response = client.post("/api/predict", json=body)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "errors" in detail
    assert len(detail["errors"]) >= 1


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
