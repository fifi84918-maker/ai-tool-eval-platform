"""Tests for GET /api/v1/ingest/runs endpoint."""

import json
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.db import save_ingest_run, clear_ingest_runs
from datetime import datetime, timezone

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_runs():
    clear_ingest_runs()
    yield
    clear_ingest_runs()


def test_ingest_runs_empty():
    """GET /api/v1/ingest/runs returns empty list when no runs exist."""
    response = client.get("/api/v1/ingest/runs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_ingest_runs_returns_records():
    """GET /api/v1/ingest/runs returns saved ingest runs."""
    now = datetime.now(timezone.utc).isoformat()
    save_ingest_run({
        "run_id": "run-abc123",
        "query": "pdf skill",
        "started_at": now,
        "finished_at": now,
        "discovered": 5,
        "acquired": 4,
        "reviewed": 3,
        "quarantined": 1,
        "runnable": 3,
        "errors": [{"source": "bad/repo", "error": "timeout"}],
    })

    response = client.get("/api/v1/ingest/runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

    run = data[0]
    assert run["run_id"] == "run-abc123"
    assert run["query"] == "pdf skill"
    assert run["discovered"] == 5
    assert run["acquired"] == 4
    assert run["reviewed"] == 3
    assert run["quarantined"] == 1
    assert run["runnable"] == 3
    assert run["error_count"] == 1  # derived from len(errors)
    assert "started_at" in run


def test_ingest_runs_limit_param():
    """GET /api/v1/ingest/runs?limit=2 returns at most 2 records."""
    now = datetime.now(timezone.utc).isoformat()
    for i in range(5):
        save_ingest_run({
            "run_id": f"run-{i:03}",
            "query": f"query-{i}",
            "started_at": now,
            "discovered": i,
            "acquired": 0,
            "reviewed": 0,
            "quarantined": 0,
            "runnable": 0,
            "errors": [],
        })

    response = client.get("/api/v1/ingest/runs?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 2


def test_ingest_runs_structure():
    """Each run record has all required fields."""
    now = datetime.now(timezone.utc).isoformat()
    save_ingest_run({
        "run_id": "run-struct",
        "query": "test",
        "started_at": now,
        "errors": [],
    })

    response = client.get("/api/v1/ingest/runs")
    assert response.status_code == 200
    run = response.json()[0]

    required = {"run_id", "query", "started_at", "discovered", "acquired",
                "reviewed", "quarantined", "runnable", "error_count"}
    for field in required:
        assert field in run, f"Missing field: {field}"
