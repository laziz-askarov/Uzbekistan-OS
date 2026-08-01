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

    assert contract["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    assert runtime["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"

    assert contract["paths"]["/ready"]["get"]["operationId"] == "getReadiness"
    assert runtime["paths"]["/api/v1/ready"]["get"]["operationId"] == "getReadiness"
