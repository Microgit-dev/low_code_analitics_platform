from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app.diagnostic_form_d import build_form_d_diagnostic_request
from app.main import app


def test_generate_report_form_d_payload_smoke():
    client = TestClient(app)
    payload = build_form_d_diagnostic_request()

    response = client.post("/reports/generate", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["sql"].strip()
    assert data["rows"]
    assert data["html"].strip()
    assert "<table" in data["html"].lower()

    template = BeautifulSoup(payload["template_html"], "lxml")
    result = BeautifulSoup(data["html"], "lxml")
    assert len(result.select("td[rowspan], th[rowspan]")) >= len(template.select("td[rowspan], th[rowspan]"))
    assert len(result.select("td[colspan], th[colspan]")) >= len(template.select("td[colspan], th[colspan]"))
    assert all(node.get_text(" ", strip=True) for node in result.select(".line"))
    assert all(node.get_text(" ", strip=True) for node in result.select(".inline-line"))
    assert all(node.get_text(" ", strip=True) for node in result.select(".total-line"))
    assert "{{owner_name}}" in data["html"]
    assert "{{report_period}}" in data["html"]
    assert "{{total_length_km}}" in data["html"]
    assert "{{total_length_m}}" in data["html"]
    assert "{{road_name}}" in data["html"]
    assert "{{accident_count}}" in data["html"]
    assert data["debug_info"]["stub_mode"] is True
