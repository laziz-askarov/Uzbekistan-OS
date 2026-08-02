from copy import deepcopy
from json import load
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "packages/knowledge/schemas/knowledge-document.schema.json"
FIXTURE_PATH = ROOT / "packages/knowledge/examples/minimal-immigration-document.json"
OPENAPI_PATH = ROOT / "packages/contracts/openapi.yaml"
SOURCE_REGISTRY_SCHEMA_PATH = ROOT / "data/sources/source-registry.schema.json"
SOURCE_REGISTRY_PATHS = sorted((ROOT / "data/sources").glob("registry.*.json"))
EXTRACTION_SCHEMA_PATH = ROOT / "packages/knowledge/schemas/extraction-artifact.schema.json"
EXTRACTION_FIXTURE_PATH = ROOT / "packages/knowledge/examples/minimal-extraction-artifact.json"
DOMAIN_FIXTURE_PATH = ROOT / "packages/knowledge/examples/domain-extension-fixtures.json"
DOMAIN_SCHEMA_PATHS = {
    domain: ROOT / f"packages/knowledge/schemas/{domain}-document.schema.json"
    for domain in (
        "immigration",
        "tourism",
        "business-registration",
        "healthcare",
        "everyday-living",
    )
}
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
MUTATING_METHODS = {"post", "put", "patch", "delete"}
AUTHORIZATION_MODES = {"public", "optional-principal", "authenticated", "role-gated"}
REQUIRED_SSE_EVENTS = {"start", "chunk", "citation", "workflow", "done", "error"}
PHASE_TWO_PATHS = {
    "/health",
    "/ready",
    "/auth/guest",
    "/auth/register",
    "/auth/login",
    "/auth/refresh",
    "/auth/logout",
    "/auth/me",
    "/profile",
    "/conversations",
    "/conversations/{conversationId}",
    "/conversations/{conversationId}/messages",
    "/knowledge/search",
    "/knowledge/{documentId}",
    "/knowledge/{documentId}/sources",
    "/workflows",
    "/workflows/{workflowId}",
    "/workflows/{workflowId}/progress",
    "/feedback",
    "/admin/sources",
    "/admin/ingestion/jobs",
    "/admin/reviews",
    "/admin/reviews/{review_item_id}/claim",
    "/admin/reviews/{review_item_id}/decision",
    "/admin/artifacts/{artifact_id}",
    "/admin/artifacts/{artifact_id}/comparison",
    "/admin/publications",
}


def read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as stream:
        return load(stream)


def iter_local_references(value: object):
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/"):
            yield reference
        for child in value.values():
            yield from iter_local_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_local_references(child)


def resolve_local_reference(document: dict[str, object], reference: str) -> object:
    current: object = document
    for component in reference.removeprefix("#/").split("/"):
        if not isinstance(current, dict) or component not in current:
            raise ValueError(f"OpenAPI contract contains an unresolved reference: {reference}")
        current = current[component]
    return current


def validate_knowledge_fixture() -> None:
    schema = read_json(SCHEMA_PATH)
    fixture = read_json(FIXTURE_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(fixture)


def validate_domain_extension_fixtures() -> None:
    base_schema = read_json(SCHEMA_PATH)
    base_fixture = read_json(FIXTURE_PATH)
    domain_fixtures = read_json(DOMAIN_FIXTURE_PATH)
    if not isinstance(base_schema, dict) or not isinstance(base_fixture, dict):
        raise ValueError("Knowledge schema and fixture must be JSON objects")
    if not isinstance(domain_fixtures, dict):
        raise ValueError("Domain extension fixtures must be a JSON object")

    registry = Registry().with_resource(base_schema["$id"], Resource.from_contents(base_schema))
    for domain, schema_path in DOMAIN_SCHEMA_PATHS.items():
        schema = read_json(schema_path)
        if not isinstance(schema, dict):
            raise ValueError(f"Domain schema must be a JSON object: {schema_path}")
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )

        fixture_set = domain_fixtures.get(domain)
        if not isinstance(fixture_set, dict):
            raise ValueError(f"Domain fixtures are missing for {domain}")

        valid_fixture = deepcopy(base_fixture)
        valid_fixture["domain"] = domain
        valid_fixture["slug"] = f"example-{domain}-document"
        valid_fixture["domain_data"] = fixture_set["valid"]
        validator.validate(valid_fixture)

        invalid_fixture = deepcopy(valid_fixture)
        invalid_fixture["domain_data"] = fixture_set["invalid"]
        try:
            validator.validate(invalid_fixture)
        except ValidationError:
            pass
        else:
            raise ValueError(f"Invalid {domain} fixture unexpectedly passed validation")


def validate_openapi_skeleton() -> None:
    with OPENAPI_PATH.open(encoding="utf-8") as stream:
        contract = yaml.safe_load(stream)

    if contract.get("openapi") != "3.1.0":
        raise ValueError("OpenAPI contract must use version 3.1.0")
    if not contract.get("paths"):
        raise ValueError("OpenAPI contract must define at least one path")
    if not contract.get("components", {}).get("schemas"):
        raise ValueError("OpenAPI contract must define component schemas")
    if not PHASE_TWO_PATHS.issubset(contract["paths"]):
        missing_paths = sorted(PHASE_TWO_PATHS.difference(contract["paths"]))
        raise ValueError(f"OpenAPI contract is missing Phase 2 paths: {missing_paths}")
    if "BearerAuth" not in contract.get("components", {}).get("securitySchemes", {}):
        raise ValueError("OpenAPI contract must define BearerAuth")

    parameters = contract["components"].get("parameters", {})
    for parameter_name in ("Cursor", "Limit", "IdempotencyKey"):
        if parameter_name not in parameters:
            raise ValueError(f"OpenAPI contract is missing shared {parameter_name} parameter")

    operation_ids: set[str] = set()
    for path, path_item in contract["paths"].items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue

            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                raise ValueError(f"{method.upper()} {path} is missing operationId")
            if operation_id in operation_ids:
                raise ValueError(f"OpenAPI contract contains duplicate operationId: {operation_id}")
            operation_ids.add(operation_id)

            authorization = operation.get("x-authorization")
            if not isinstance(authorization, dict):
                raise ValueError(f"{method.upper()} {path} is missing x-authorization")
            mode = authorization.get("mode")
            if mode not in AUTHORIZATION_MODES:
                raise ValueError(f"{method.upper()} {path} has an invalid authorization mode")

            roles = authorization.get("roles")
            if mode == "role-gated" and (not isinstance(roles, list) or not roles):
                raise ValueError(f"{method.upper()} {path} must declare at least one role")
            if mode in {"authenticated", "role-gated"} and operation.get("security") != [
                {"BearerAuth": []}
            ]:
                raise ValueError(f"{method.upper()} {path} must use BearerAuth")

            if method in MUTATING_METHODS and not isinstance(operation.get("x-idempotency"), dict):
                raise ValueError(f"{method.upper()} {path} is missing x-idempotency")

            refs = {
                parameter.get("$ref")
                for parameter in operation.get("parameters", [])
                if isinstance(parameter, dict)
            }
            if (
                "#/components/parameters/Cursor" in refs
                and "#/components/parameters/Limit" not in refs
            ):
                raise ValueError(f"{method.upper()} {path} uses Cursor without Limit")
            if (
                operation.get("x-idempotency", {}).get("mode") == "caller-key"
                and "#/components/parameters/IdempotencyKey" not in refs
            ):
                raise ValueError(f"{method.upper()} {path} must accept Idempotency-Key")

    message_operation = contract["paths"]["/conversations/{conversationId}/messages"]["post"]
    declared_sse_events = {
        event["$ref"].removeprefix("#/components/schemas/Stream").removesuffix("Event").lower()
        for event in message_operation.get("x-sse-events", [])
    }
    if declared_sse_events != REQUIRED_SSE_EVENTS:
        raise ValueError("Chat stream must declare the complete application-owned SSE event set")

    for reference in iter_local_references(contract):
        resolve_local_reference(contract, reference)


def validate_source_registry() -> None:
    schema = read_json(SOURCE_REGISTRY_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    if not SOURCE_REGISTRY_PATHS:
        raise ValueError("At least one environment source registry is required")
    for path in SOURCE_REGISTRY_PATHS:
        registry = read_json(path)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(registry)
        environment = registry["environment"]
        proposed = path.name.endswith(".proposed.json")
        expected_name = (
            f"registry.{environment}.proposed.json"
            if proposed
            else f"registry.{environment}.json"
        )
        if path.name != expected_name:
            raise ValueError(f"Source registry filename does not match environment: {path}")

        sources = registry["sources"]
        if proposed:
            for source in sources:
                fail_closed = (
                    source["status"] == "draft"
                    and source["crawl_policy"] == "pending_review"
                    and source["production_eligible"] is False
                    and source["owner"] is None
                    and source["reviewed_at"] is None
                    and source["schedule"] is None
                )
                if not fail_closed:
                    raise ValueError(f"Proposed source must remain fail-closed: {source['slug']}")
        organizations: dict[str, object] = {}
        for source in sources:
            organization = source["organization"]
            organization_id = organization["id"]
            existing = organizations.setdefault(organization_id, organization)
            if existing != organization:
                raise ValueError(
                    "Source registry reuses an organization ID with conflicting metadata: "
                    f"{organization_id}"
                )
        for field in ("id", "slug", "url"):
            values = [source[field] for source in sources]
            if len(values) != len(set(values)):
                raise ValueError(f"Source registry contains duplicate {field} values")


def validate_extraction_fixture() -> None:
    schema = read_json(EXTRACTION_SCHEMA_PATH)
    fixture = read_json(EXTRACTION_FIXTURE_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(fixture)


if __name__ == "__main__":
    validate_knowledge_fixture()
    validate_domain_extension_fixtures()
    validate_openapi_skeleton()
    validate_source_registry()
    validate_extraction_fixture()
    print("Contracts validated successfully.")
