"""Unit tests for prediction form and CSV validation."""

import pandas as pd
import pytest

from app.ml.validation import validate_csv_upload, validate_prediction_input


def _valid_payload() -> dict:
    return {
        "tenure": 12,
        "MonthlyCharges": 70.0,
        "TotalCharges": 840.0,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "DSL",
        "OnlineSecurity": "No",
        "OnlineBackup": "No",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "No",
        "StreamingMovies": "No",
    }


class TestPredictionInputValidation:
    def test_valid_payload_returns_no_errors(self):
        assert validate_prediction_input(_valid_payload()) == []

    def test_tenure_out_of_range(self):
        data = _valid_payload()
        data["tenure"] = 100
        errors = validate_prediction_input(data)
        assert any("Tenure" in e for e in errors)

    def test_invalid_tenure_type(self):
        data = _valid_payload()
        data["tenure"] = "abc"
        errors = validate_prediction_input(data)
        assert any("Tenure" in e for e in errors)

    def test_monthly_charges_out_of_range(self):
        data = _valid_payload()
        data["MonthlyCharges"] = 250
        errors = validate_prediction_input(data)
        assert any("Monthly charges" in e for e in errors)

    def test_negative_total_charges(self):
        data = _valid_payload()
        data["TotalCharges"] = -1
        errors = validate_prediction_input(data)
        assert any("Total charges" in e for e in errors)

    def test_phone_service_constraint(self):
        data = _valid_payload()
        data["PhoneService"] = "No"
        data["MultipleLines"] = "Yes"
        errors = validate_prediction_input(data)
        assert any("multiple lines" in e.lower() for e in errors)

    def test_internet_service_constraint(self):
        data = _valid_payload()
        data["InternetService"] = "No"
        data["OnlineSecurity"] = "Yes"
        errors = validate_prediction_input(data)
        assert any("Online Security" in e or "internet service" in e.lower() for e in errors)


class TestCsvValidation:
    def test_empty_file(self):
        assert validate_csv_upload(None, 0) == ["The uploaded file is empty."]

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        errors = validate_csv_upload(df, 10)
        assert any("No rows" in e for e in errors)

    def test_missing_required_columns(self):
        df = pd.DataFrame({"tenure": [1], "Contract": ["Month-to-month"]})
        errors = validate_csv_upload(df, 100)
        assert any("Missing required columns" in e for e in errors)

    def test_non_numeric_column(self):
        cols = {
            "gender": ["Male"],
            "SeniorCitizen": [0],
            "Partner": ["No"],
            "Dependents": ["No"],
            "tenure": ["bad"],
            "PhoneService": ["Yes"],
            "MultipleLines": ["No"],
            "InternetService": ["DSL"],
            "OnlineSecurity": ["No"],
            "OnlineBackup": ["No"],
            "DeviceProtection": ["No"],
            "TechSupport": ["No"],
            "StreamingTV": ["No"],
            "StreamingMovies": ["No"],
            "Contract": ["Month-to-month"],
            "PaperlessBilling": ["Yes"],
            "PaymentMethod": ["Electronic check"],
            "MonthlyCharges": [70.0],
            "TotalCharges": [840.0],
        }
        df = pd.DataFrame(cols)
        errors = validate_csv_upload(df, 500)
        assert any('Column "tenure"' in e for e in errors)
