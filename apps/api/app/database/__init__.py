"""Database metadata, models, and session helpers."""

from app.database.base import Base
from app.database.models.audit import AuditEvent
from app.database.models.geography import Country, Language
from app.database.models.identity import Principal, PrincipalRole, Role
from app.database.models.ingestion import (
    CrawlJob,
    ExtractionArtifact,
    ReviewItem,
    SourceSnapshot,
)
from app.database.models.knowledge import (
    Chunk,
    Document,
    DocumentSource,
    DocumentVersion,
    Domain,
    Embedding,
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
    "DocumentSource",
    "DocumentVersion",
    "Domain",
    "Embedding",
    "ExtractionArtifact",
    "Language",
    "Principal",
    "PrincipalRole",
    "PublicationRecord",
    "ReviewItem",
    "Role",
    "Source",
    "SourceOrganization",
    "SourceSnapshot",
]
