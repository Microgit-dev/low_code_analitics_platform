from fastapi.testclient import TestClient

from app.main import app


def test_openapi_has_report_generation_request_schema():
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200, response.text
    schemas = response.json()["components"]["schemas"]
    assert "ReportGenerationRequest" in schemas
    assert "ReportGenerationResponse" in schemas
