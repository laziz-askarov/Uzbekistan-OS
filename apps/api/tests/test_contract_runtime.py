from pathlib import Path

import yaml

from app.main import create_app

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / "packages/contracts/openapi.yaml"

IMPLEMENTED_OPERATIONS = {
    "/auth/me": "get",
    "/admin/sources": "get",
    "/admin/sources/{source_id}/uploads": "post",
    "/admin/ingestion/jobs": ("get", "post"),
    "/admin/reviews": "get",
    "/admin/reviews/{review_item_id}/claim": "post",
    "/admin/reviews/{review_item_id}/decision": "post",
    "/admin/artifacts/{artifact_id}/comparison": "get",
    "/admin/artifacts/{artifact_id}": "get",
    "/admin/publications": "post",
    "/admin/documents/{document_id}/expire": "post",
    "/admin/documents/{document_id}/reindex": "post",
}

IMPLEMENTED_AUTHORIZATION = {
    "/auth/me": {"mode": "authenticated", "roles": []},
    "/admin/sources": {"mode": "role-gated", "roles": ["admin"]},
    "/admin/sources/{source_id}/uploads": {
        "mode": "role-gated",
        "roles": ["admin"],
    },
    "/admin/ingestion/jobs": {"mode": "role-gated", "roles": ["admin"]},
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
    "/admin/documents/{document_id}/expire": {
        "mode": "role-gated",
        "roles": ["knowledge_publisher", "admin"],
    },
    "/admin/documents/{document_id}/reindex": {
        "mode": "role-gated",
        "roles": ["knowledge_publisher", "admin"],
    },
}


def test_checked_in_admin_contract_matches_runtime_paths_and_security() -> None:
    with CONTRACT_PATH.open(encoding="utf-8") as stream:
        contract = yaml.safe_load(stream)
    runtime = create_app().openapi()

    for path, configured_methods in IMPLEMENTED_OPERATIONS.items():
        methods = (
            configured_methods if isinstance(configured_methods, tuple) else (configured_methods,)
        )
        for method in methods:
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


def test_publication_contract_exposes_structured_authoring_fields() -> None:
    with CONTRACT_PATH.open(encoding="utf-8") as stream:
        contract = yaml.safe_load(stream)
    runtime = create_app().openapi()

    expected_fields = {
        "nationalities",
        "residency_statuses",
        "locations",
        "applicability_conditions",
        "requirements",
        "steps",
        "fees",
        "processing_time",
    }
    assert expected_fields <= set(
        contract["components"]["schemas"]["PublicationCandidate"]["properties"]
    )
    assert expected_fields <= set(
        runtime["components"]["schemas"]["PublicationCandidate"]["properties"]
    )


def test_planned_conversation_contract_exposes_contextual_flow_metadata() -> None:
    with CONTRACT_PATH.open(encoding="utf-8") as stream:
        contract = yaml.safe_load(stream)
    schemas = contract["components"]["schemas"]

    assert {
        "ConversationState",
        "ConversationFact",
        "ClarificationRequest",
        "GroundedAnswer",
        "EvidenceFeedback",
        "NextAction",
        "StreamContextEvent",
    } <= set(schemas)
    answer_properties = schemas["GroundedAnswer"]["properties"]
    assert {"clarification", "context_used", "limitations", "next_actions"} <= set(
        answer_properties
    )
    stream_refs = {
        item["$ref"]
        for item in contract["paths"]["/conversations/{conversationId}/messages"]["post"][
            "x-sse-events"
        ]
    }
    assert "#/components/schemas/StreamContextEvent" in stream_refs
