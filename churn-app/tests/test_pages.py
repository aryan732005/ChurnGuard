"""Page route regression tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_experiments_page_returns_200():
    response = client.get("/experiments")
    assert response.status_code == 200
    assert "Experiments" in response.text
    assert "expTable" in response.text
    assert "expLoading" in response.text


def test_experiments_api_empty_state_structure():
    response = client.get("/api/experiments?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert "count" in data
    assert "page" in data
    assert "total_pages" in data
    assert isinstance(data["runs"], list)


def test_landing_has_business_value_and_calculator():
    response = client.get("/")
    assert response.status_code == 200
    assert "valueTranslation" in response.text
    assert "Impact calculator" in response.text
    assert "prototype" not in response.text.lower()
    assert "in development" not in response.text.lower()


def test_about_no_prototype_badge():
    response = client.get("/about")
    assert response.status_code == 200
    assert "Telco" in response.text or "telco" in response.text.lower()
    assert "prototype" not in response.text.lower()


def test_retrain_page_loads():
    response = client.get("/retrain")
    assert response.status_code == 200
    assert "Retrain simulation" in response.text
    assert "adminUser" in response.text


def test_docs_page_not_swagger():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "API reference" in response.text
    assert "swagger-ui" not in response.text.lower()


def test_interest_invalid_email_rejected():
    response = client.post("/api/interest", json={"email": "not-an-email", "message": "hi"})
    assert response.status_code == 422
