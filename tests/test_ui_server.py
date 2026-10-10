"""Unit tests for FastAPI UI server endpoints and dashboard HTML."""

from fastapi.testclient import TestClient

from paradecomp.ui.server import app

client = TestClient(app)


def test_get_dashboard():
    response = client.get("/")
    assert response.status_code == 200
    assert "PARADECOMP TELEMETRY WORKBENCH" in response.text
    assert "scrollbar-width: thin;" in response.text
    assert "300" in response.text


def test_api_analyze():
    payload = {
        "subtasks": [
            "Optics: High-NA numerical aperture",
            "Transistors: GAA nanosheet inner spacer",
            "Packaging: Direct Cu-Cu hybrid bonding",
        ],
        "threshold": 0.65,
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "mean_orthogonality" in data
    assert "gating_verdict" in data
    assert data["gating_verdict"] == "PARALLEL_FAN_OUT"


def test_api_benchmark():
    response = client.get("/api/benchmark")
    assert response.status_code == 200
    data = response.json()
    assert data["serial_sources_pulled"] == 30
    assert data["parallel_sources_pulled"] == 300
    assert data["breadth_multiplier"] == 10.0
    assert "critic_verdict" in data


def test_api_research():
    payload = {
        "topic": "Semiconductor Fab Robotics",
        "num_facets": 3,
        "sources_per_facet": 10,
    }
    response = client.post("/api/research", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_sources_gathered"] == 30
    assert data["successful_subtasks"] == 3
