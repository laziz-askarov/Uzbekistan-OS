import json
import runpy
import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_vercel_entrypoint_exports_fastapi_application() -> None:
    module = runpy.run_path(str(REPOSITORY_ROOT / "api" / "index.py"))

    assert module["app"].title == "Uzbekistan OS API"


def test_vercel_configuration_routes_requests_to_python_entrypoint() -> None:
    config = json.loads((REPOSITORY_ROOT / "vercel.api.json").read_text(encoding="utf-8"))

    assert config["buildCommand"] == ""
    assert config["framework"] is None
    assert config["installCommand"] == ""
    assert config["functions"]["api/index.py"]["maxDuration"] == 60
    assert config["rewrites"] == [{"source": "/(.*)", "destination": "/api/index"}]


def test_vercel_project_matches_api_runtime_dependencies() -> None:
    api_project = tomllib.loads(
        (REPOSITORY_ROOT / "apps" / "api" / "pyproject.toml").read_text(encoding="utf-8")
    )
    vercel_project = tomllib.loads(
        (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    runtime_dependencies = api_project["project"]["dependencies"]
    vercel_dependencies = vercel_project["project"]["dependencies"]

    assert vercel_dependencies == runtime_dependencies
    assert vercel_project["project"]["requires-python"] == ">=3.12,<3.13"
    assert vercel_project["tool"]["vercel"]["entrypoint"] == "api.index:app"


def test_api_responses_include_security_headers(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_ALLOWED_HOSTS", "testserver")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            response = client.get("/api/v1/health")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["permissions-policy"] == (
        "camera=(), geolocation=(), microphone=()"
    )
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["strict-transport-security"] == (
        "max-age=31536000; includeSubDomains"
    )
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_untrusted_host_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("API_ALLOWED_HOSTS", "api.uzbekistanos.com")
    get_settings.cache_clear()
    try:
        with TestClient(create_app(), base_url="https://malicious.example") as client:
            response = client.get("/api/v1/health")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 400
