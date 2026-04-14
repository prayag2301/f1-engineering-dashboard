import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_generate_glb_success():
    response = client.post("/api/v1/models/mercedes/regenerate?season=2026")
    assert response.status_code == 200
    data = response.json()
    assert data["team_id"] == "mercedes"
    assert data["season"] == 2026
    assert data["size_bytes"] > 0
    assert data["url"] == "/api/v1/models/mercedes/latest.glb?season=2026"
    assert "generated_in_ms" in data

def test_get_glb_success():
    response = client.get("/api/v1/models/ferrari/latest.glb?season=2026")
    assert response.status_code == 200
    assert response.headers["content-type"] == "model/gltf-binary"
    assert response.headers["x-team-id"] == "ferrari"
    assert response.headers["x-season"] == "2026"
    assert len(response.content) > 0
