from json import load
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "packages/knowledge/schemas/knowledge-document.schema.json"
FIXTURE_PATH = ROOT / "packages/knowledge/examples/minimal-immigration-document.json"
OPENAPI_PATH = ROOT / "packages/contracts/openapi.yaml"
SOURCE_REGISTRY_SCHEMA_PATH = ROOT / "data/sources/source-registry.schema.json"
SOURCE_REGISTRY_PATH = ROOT / "data/sources/registry.development.json"


def read_json(path: Path) -> object:
    with path.open(encoding="utf-8") as stream:
        return load(stream)


def validate_knowledge_fixture() -> None:
    schema = read_json(SCHEMA_PATH)
    fixture = read_json(FIXTURE_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(fixture)


def validate_openapi_skeleton() -> None:
    with OPENAPI_PATH.open(encoding="utf-8") as stream:
        contract = yaml.safe_load(stream)

    if contract.get("openapi") != "3.1.0":
        raise ValueError("OpenAPI contract must use version 3.1.0")
    if not contract.get("paths"):
        raise ValueError("OpenAPI contract must define at least one path")
    if not contract.get("components", {}).get("schemas"):
        raise ValueError("OpenAPI contract must define component schemas")


def validate_source_registry() -> None:
    schema = read_json(SOURCE_REGISTRY_SCHEMA_PATH)
    registry = read_json(SOURCE_REGISTRY_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(registry)

    sources = registry["sources"]
    for field in ("id", "slug", "url"):
        values = [source[field] for source in sources]
        if len(values) != len(set(values)):
            raise ValueError(f"Source registry contains duplicate {field} values")


if __name__ == "__main__":
    validate_knowledge_fixture()
    validate_openapi_skeleton()
    validate_source_registry()
    print("Contracts validated successfully.")
