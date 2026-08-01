from pathlib import Path

import yaml

from app.main import create_app

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / "packages/contracts/openapi.yaml"

IMPLEMENTED_OPERATIONS = {
    "/auth/me": "get",
    "/admin/reviews": "get",
    "/admin/reviews/{review_item_id}/claim": "post",
    "/admin/reviews/{review_item_id}/decision": "post",
    "/admin/artifacts/{artifact_id}/comparison": "get",
    "/admin/artifacts/{artifact_id}": "get",
    "/admin/publications": "post",
}

IMPLEMENTED_AUTHORIZATION = {
    "/auth/me": {"mode": "authenticated", "roles": []},
    "/admin/reviews": {"mode": "role-gated", "roles": ["content_reviewer", "admin"]},
    "/admin/reviews/{review_item_id}/claim": {
        "mode": "role-gated",
        "roles": ["content_reviewer", "admin"],
    },
    "/admin/reviews/{review_item_id}/decision": {
        "mode": "role-gated",
        "roles": ["content_reviewer", "admin"],
    },
    "/admin/artifacts/{artifact_id}/comparison": {
        "mode": "role-gated",
        "roles": ["content_reviewer", "admin"],
    },
    "/admin/artifacts/{artifact_id}": {
        "mode": "role-gated",
        "roles": ["content_reviewer", "admin"],
    },
    "/admin/publications": {
        "mode": "role-gated",
        "roles": ["knowledge_publisher", "admin"],
    },
}


def test_checked_in_admin_contract_matches_runtime_paths_and_security() -> None:
    with CONTRACT_PATH.open(encoding="utf-8") as stream:
        contract = yaml.safe_load(stream)
    runtime = create_app().openapi()

    for path, method in IMPLEMENTED_OPERATIONS.items():
        runtime_operation = runtime["paths"][f"/api/v1{path}"][method]
        contract_operation = contract["paths"][path][method]

        assert contract_operation["operationId"] == runtime_operation["operationId"]
        assert contract_operation["security"] == [{"BearerAuth": []}]
        assert runtime_operation["security"] == [{"BearerAuth": []}]
        assert contract_operation["x-authorization"] == IMPLEMENTED_AUTHORIZATION[path]

    assert contract["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    assert runtime["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"

    assert contract["paths"]["/ready"]["get"]["operationId"] == "getReadiness"
    assert runtime["paths"]["/api/v1/ready"]["get"]["operationId"] == "getReadiness"

    assert (
        contract["paths"]["/admin/reviews/{review_item_id}/claim"]["post"]["x-idempotency"]["mode"]
        == "deterministic-replay"
    )
    assert contract["paths"]["/admin/publications"]["post"]["x-idempotency"]["replay"] == (
        "candidate-checksum"
    )
