# -*- coding: utf-8 -*-
"""The legacy project-margin upper-bound API must stay retired."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
URL = "/api/项目毛利"


def test_legacy_project_margin_endpoint_is_gone():
    response = client.get(URL)
    assert response.status_code == 410
    body = response.json()
    assert "/public-api/项目成本" in body["detail"]
    assert "成本完整性闭合后" in body["detail"]
    assert "项目" not in body
