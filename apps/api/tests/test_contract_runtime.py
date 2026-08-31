from pathlib import Path

import yaml

from app.main import create_app

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = ROOT / "packages/contracts/openapi.yaml"

IMPLEMENTED_OPERATIONS = {
    "/auth/me": "get",
    "/assistant/answer": "post",
    "/admin/sources": ("get", "post"),
    "/admin/sources/{source_id}/uploads": "post",
    "/admin/ingestion/jobs": ("get", "post"),
    "/admin/ingestion/topics": "get",
    "/admin/reviews": "get",
    "/admin/reviews/{review_item_id}/claim": "post",
    "/admin/reviews/{review_item_id}/decision": "post",
    "/admin/artifacts/{artifact_id}/comparison": "get",
    "/admin/artifacts/{artifact_id}": "get",
    "/admin/publications": "post",
    "/admin/documents/{document_id}/expire": "post",
    "/admin/documents/{document_id}/reindex": "post",
    "/admin/content/authors": ("get", "post"),
    "/admin/content/posts": ("get", "post"),
    "/admin/content/posts/{post_id}/revisions": "post",
    "/admin/content/revisions/{revision_id}": ("get", "put"),
    "/admin/content/revisions/{revision_id}/submit": "post",
    "/admin/content/revisions/{revision_id}/decision": "post",
    "/admin/content/revisions/{revision_id}/publish": "post",
    "/content/posts": "get",
    "/content/posts/{slug}": "get",
}

IMPLEMENTED_AUTHORIZATION = {
    "/auth/me": {"mode": "authenticated", "roles": []},
    "/assistant/answer": {"mode": "authenticated", "roles": []},
    "/admin/sources": {"mode": "role-gated", "roles": ["admin"]},
    "/admin/sources/{source_id}/uploads": {
        "mode": "role-gated",
        "roles": ["admin"],
    },
    "/admin/ingestion/jobs": {"mode": "role-gated", "roles": ["admin"]},
    "/admin/ingestion/topics": {"mode": "role-gated", "roles": ["admin"]},
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
    "/admin/content/authors": {
        "get": {
            "mode": "role-gated",
            "roles": ["content_author", "content_reviewer", "knowledge_publisher", "admin"],
        },
        "post": {"mode": "role-gated", "roles": ["content_author", "admin"]},
    },
    "/admin/content/posts": {
        "get": {
            "mode": "role-gated",
            "roles": ["content_author", "content_reviewer", "knowledge_publisher", "admin"],
        },
        "post": {"mode": "role-gated", "roles": ["content_author", "admin"]},
    },
    "/admin/content/posts/{post_id}/revisions": {
        "mode": "role-gated",
        "roles": ["content_author", "admin"],
    },
    "/admin/content/revisions/{revision_id}": {
        "get": {
            "mode": "role-gated",
            "roles": ["content_author", "content_reviewer", "knowledge_publisher", "admin"],
        },
        "put": {"mode": "role-gated", "roles": ["content_author", "admin"]},
    },
    "/admin/content/revisions/{revision_id}/submit": {
        "mode": "role-gated",
        "roles": ["content_author", "admin"],
    },
    "/admin/content/revisions/{revision_id}/decision": {
        "mode": "role-gated",
        "roles": ["content_reviewer", "admin"],
    },
    "/admin/content/revisions/{revision_id}/publish": {
        "mode": "role-gated",
        "roles": ["knowledge_publisher", "admin"],
    },
    "/content/posts": {"mode": "public"},
    "/content/posts/{slug}": {"mode": "public"},
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
            authorization = IMPLEMENTED_AUTHORIZATION[path]
            expected_authorization = authorization.get(method, authorization)
            expected_security = (
                [] if expected_authorization["mode"] == "public" else [{"BearerAuth": []}]
            )
            assert contract_operation["security"] == expected_security
            assert runtime_operation.get("security", []) == expected_security
            assert contract_operation["x-authorization"] == expected_authorization

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
    assert (
        "effective_until" in contract["components"]["schemas"]["PublicationCandidate"]["required"]
    )
    assert "effective_until" in runtime["components"]["schemas"]["PublicationCandidate"]["required"]


def test_grounded_assistant_contract_exposes_evidence_and_fail_closed_metadata() -> None:
    with CONTRACT_PATH.open(encoding="utf-8") as stream:
        contract = yaml.safe_load(stream)
    runtime = create_app().openapi()

    for schema in (
        "AssistantAnswerRequest",
        "AssistantAnswerData",
        "EvidencePack",
        "EvidenceItem",
        "CitationReference",
    ):
        assert schema in contract["components"]["schemas"]
        assert schema in runtime["components"]["schemas"]
    assert contract["paths"]["/assistant/answer"]["post"]["x-authorization"] == {
        "mode": "authenticated",
        "roles": [],
    }


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
