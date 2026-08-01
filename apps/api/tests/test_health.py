from fastapi.testclient import TestClient

from app.main import app

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
