from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.database import Base

EXPECTED_SCHEMAS = {"identity", "geography", "knowledge", "ingestion", "audit"}
EXPECTED_TABLES = {
    "identity.principals",
    "identity.roles",
    "identity.principal_roles",
    "geography.languages",
    "geography.countries",
    "knowledge.domains",
    "knowledge.source_organizations",
    "knowledge.sources",
    "knowledge.documents",
    "knowledge.document_versions",
    "knowledge.document_lifecycle_events",
    "knowledge.document_sources",
    "knowledge.chunks",
    "knowledge.embeddings",
    "knowledge.index_jobs",
    "knowledge.publication_records",
    "ingestion.source_snapshots",
    "ingestion.snapshot_objects",
    "ingestion.managed_source_configs",
    "ingestion.crawl_jobs",
    "ingestion.extraction_artifacts",
    "ingestion.review_items",
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


def test_admin_managed_sources_are_bounded_audited_and_idempotent() -> None:
    sources = Base.metadata.tables["ingestion.managed_source_configs"]

    assert {
        "source_id",
        "domains",
        "languages",
        "created_by_principal_id",
        "idempotency_key",
        "request_sha256",
    } <= set(sources.c.keys())
    assert sources.c.source_id.primary_key is True
    assert sources.c.created_by_principal_id.foreign_keys
    uniques = {
        constraint.name
        for constraint in sources.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_managed_source_configs_idempotency_key" in uniques
    assert "uq_managed_source_configs_slug" in uniques


def test_extraction_artifacts_are_review_gated() -> None:
    artifacts = Base.metadata.tables["ingestion.extraction_artifacts"]
    review_items = Base.metadata.tables["ingestion.review_items"]

    assert review_items.c.extraction_artifact_id.unique is True
    review_checks = {
        constraint.name
        for constraint in review_items.constraints
        if isinstance(constraint, CheckConstraint)
    }
    artifact_checks = {
        constraint.name
        for constraint in artifacts.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_review_items_status_allowed" in review_checks
    assert "ck_review_items_priority_range" in review_checks
    assert "ck_review_items_assignment_consistent" in review_checks
    assert "ck_review_items_decision_fields_consistent" in review_checks
    assert "ck_extraction_artifacts_section_count_positive" in artifact_checks


def test_identity_roles_and_publication_lineage_are_explicit() -> None:
    principals = Base.metadata.tables["identity.principals"]
    principal_roles = Base.metadata.tables["identity.principal_roles"]
    publications = Base.metadata.tables["knowledge.publication_records"]

    assert {"provider", "subject", "status"} <= set(principals.c.keys())
    assert {"principal_id", "role_id"} == set(principal_roles.primary_key.columns.keys())
    assert publications.c.review_item_id.unique is True
    assert publications.c.document_version_id.unique is True
    assert publications.c.published_by_principal_id.foreign_keys


def test_lifecycle_and_index_jobs_encode_audit_retry_and_idempotency() -> None:
    lifecycle = Base.metadata.tables["knowledge.document_lifecycle_events"]
    jobs = Base.metadata.tables["knowledge.index_jobs"]

    assert {"document_id", "document_version_id", "actor_principal_id", "reason"} <= set(
        lifecycle.c.keys()
    )
    assert {
        "document_version_id",
        "requested_by_principal_id",
        "idempotency_key",
        "attempt_count",
        "max_attempts",
        "token_count",
        "duration_ms",
        "cost_microusd",
        "error",
        "result",
    } <= set(jobs.c.keys())
    assert any(
        isinstance(constraint, UniqueConstraint) and constraint.name == "uq_index_jobs_version_key"
        for constraint in jobs.constraints
    )
