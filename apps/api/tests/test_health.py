import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import health as health_routes

client = TestClient(app)


def test_versioned_health_response_has_standard_envelope() -> None:
    response = client.get("/api/v1/health", headers={"x-request-id": "test-request-id"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request-id"
    assert response.json() == {
        "data": {
            "service": "api",
            "status": "ok",
            "version": "0.1.0",
            "environment": "development",
        },
        "meta": {"request_id": "test-request-id"},
    }


def test_root_health_response_is_available_for_orchestrators() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_readiness_reports_dependency_health(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        health_routes,
        "check_dependencies",
        lambda settings: {"postgresql": "ok", "redis": "ok", "object_store": "ok"},
    )

    response = client.get("/api/v1/ready", headers={"x-request-id": "ready-request"})

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "service": "api",
            "status": "ready",
            "checks": {"postgresql": "ok", "redis": "ok", "object_store": "ok"},
        },
        "meta": {"request_id": "ready-request"},
    }


def test_readiness_fails_closed_when_dependency_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        health_routes,
        "check_dependencies",
        lambda settings: {
            "postgresql": "ok",
            "redis": "unavailable",
            "object_store": "ok",
        },
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "service_not_ready",
        "message": "one or more required service dependencies are unavailable",
        "details": {
            "checks": {
                "postgresql": "ok",
                "redis": "unavailable",
                "object_store": "ok",
            }
        },
    }


def test_invalid_request_id_is_replaced() -> None:
    response = client.get("/health", headers={"x-request-id": "invalid request id"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "invalid request id"
    assert response.json()["meta"]["request_id"] == response.headers["x-request-id"]
