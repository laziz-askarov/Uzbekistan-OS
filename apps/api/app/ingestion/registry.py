from pathlib import Path

from app.ingestion.models import SourceRegistry


def load_source_registry(path: Path) -> SourceRegistry:
    return SourceRegistry.model_validate_json(path.read_text(encoding="utf-8"))
