from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.database import Base

EXPECTED_SCHEMAS = {"geography", "knowledge", "ingestion", "audit"}
EXPECTED_TABLES = {
    "geography.languages",
    "geography.countries",
    "knowledge.domains",
    "knowledge.source_organizations",
    "knowledge.sources",
    "knowledge.documents",
    "knowledge.document_versions",
    "knowledge.document_sources",
    "knowledge.chunks",
    "knowledge.embeddings",
    "ingestion.source_snapshots",
    "ingestion.crawl_jobs",
    "audit.events",
}


def test_foundation_metadata_contains_expected_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES
    assert {table.schema for table in Base.metadata.tables.values()} == EXPECTED_SCHEMAS


def test_every_table_has_a_primary_key() -> None:
    for table in Base.metadata.tables.values():
        assert table.primary_key.columns, f"{table.fullname} is missing a primary key"


def test_document_publication_and_version_constraints_are_declared() -> None:
    documents = Base.metadata.tables["knowledge.documents"]
    versions = Base.metadata.tables["knowledge.document_versions"]

    document_checks = {
        constraint.name
        for constraint in documents.constraints
        if isinstance(constraint, CheckConstraint)
    }
    version_checks = {
        constraint.name
        for constraint in versions.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_documents_status_allowed" in document_checks
    assert "ck_document_versions_effective_date_order" in version_checks
    assert "ck_document_versions_version_numbers_nonnegative" in version_checks


def test_current_version_foreign_key_is_deferred_to_break_the_creation_cycle() -> None:
    documents = Base.metadata.tables["knowledge.documents"]
    current_version_fk = next(
        constraint
        for constraint in documents.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and constraint.name == "fk_documents_current_version_id_document_versions"
    )

    assert current_version_fk.use_alter is True
    assert current_version_fk.ondelete == "SET NULL"


def test_embeddings_are_model_keyed_without_a_premature_fixed_dimension() -> None:
    embeddings = Base.metadata.tables["knowledge.embeddings"]
    vector_type = embeddings.c.vector.type

    assert getattr(vector_type, "dim", None) is None


def test_ingestion_jobs_encode_idempotency_retry_and_lineage() -> None:
    jobs = Base.metadata.tables["ingestion.crawl_jobs"]
    snapshots = Base.metadata.tables["ingestion.source_snapshots"]

    assert {
        "source_snapshot_id",
        "idempotency_key",
        "attempt_count",
        "max_attempts",
        "error",
        "result",
    } <= set(jobs.c.keys())
    assert {"normalized_sha256", "byte_size"} <= set(snapshots.c.keys())

    job_checks = {
        constraint.name
        for constraint in jobs.constraints
        if isinstance(constraint, CheckConstraint)
    }
    job_uniques = {
        constraint.name
        for constraint in jobs.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    snapshot_uniques = {
        constraint.name
        for constraint in snapshots.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "ck_crawl_jobs_status_allowed" in job_checks
    assert "ck_crawl_jobs_attempt_count_range" in job_checks
    assert "ck_crawl_jobs_max_attempts_positive" in job_checks
    assert "uq_crawl_jobs_source_key" in job_uniques
    assert "uq_source_snapshots_source_sha256" in snapshot_uniques
