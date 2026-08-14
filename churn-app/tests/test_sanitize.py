"""Tests for input sanitization."""

from app.ml.sanitize import sanitize_prediction_payload


def test_rejects_extra_fields():
    data = {"tenure": 12, "MonthlyCharges": 70.0, "evil_field": "x", "PhoneService": "Yes",
            "MultipleLines": "No", "InternetService": "DSL", "TotalCharges": 840.0}
    clean, errors = sanitize_prediction_payload(data)
    assert any("Unexpected fields" in e for e in errors)
    assert "evil_field" not in clean


def test_sanitizes_control_chars():
    data = {
        "tenure": 12, "MonthlyCharges": 70.0, "TotalCharges": 840.0,
        "PhoneService": "Yes", "MultipleLines": "No", "InternetService": "DSL",
        "Contract": "Month-to-month\x00", "PaymentMethod": "Electronic check",
        "gender": "Male", "Partner": "No", "Dependents": "No",
        "OnlineSecurity": "No", "OnlineBackup": "No", "DeviceProtection": "No",
        "TechSupport": "No", "StreamingTV": "No", "StreamingMovies": "No",
        "PaperlessBilling": "Yes", "SeniorCitizen": 0,
    }
    clean, errors = sanitize_prediction_payload(data)
    assert errors == []
    assert "\x00" not in clean["Contract"]
