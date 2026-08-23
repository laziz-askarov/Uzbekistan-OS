"""Database metadata, models, and session helpers."""

from app.database.base import Base
from app.database.models.audit import AuditEvent
from app.database.models.geography import Country, Language
from app.database.models.identity import Principal, PrincipalRole, Role
from app.database.models.ingestion import (
    CrawlJob,
    ExtractionArtifact,
    ManagedSourceConfig,
    ReviewItem,
    SnapshotObject,
    SourceSnapshot,
)
from app.database.models.knowledge import (
    Chunk,
    Document,
    DocumentLifecycleEvent,
    DocumentSource,
    DocumentVersion,
    Domain,
    Embedding,
    IndexJob,
    PublicationRecord,
    Source,
    SourceOrganization,
)

__all__ = [
    "AuditEvent",
    "Base",
    "Chunk",
    "Country",
    "CrawlJob",
    "Document",
    "DocumentLifecycleEvent",
    "DocumentSource",
    "DocumentVersion",
    "Domain",
    "Embedding",
    "ExtractionArtifact",
    "IndexJob",
    "Language",
    "ManagedSourceConfig",
    "Principal",
    "PrincipalRole",
    "PublicationRecord",
    "ReviewItem",
    "Role",
    "SnapshotObject",
    "Source",
    "SourceOrganization",
    "SourceSnapshot",
]
