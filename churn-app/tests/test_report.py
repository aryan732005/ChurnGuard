"""Tests for executive report download and email."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.predictor import predictor

client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.skipif(not predictor.ready, reason="Model artifacts not loaded")
def test_executive_pdf_download():
    response = client.get("/api/executive-summary.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


@pytest.mark.skipif(not predictor.ready, reason="Model artifacts not loaded")
def test_report_send_queues_without_smtp():
    response = client.post("/api/report/send", json={"email": "test@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "message" in data


def test_report_send_invalid_email():
    response = client.post("/api/report/send", json={"email": "not-valid"})
    assert response.status_code == 422
