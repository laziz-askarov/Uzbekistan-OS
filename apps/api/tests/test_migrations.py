import subprocess
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG = ROOT / "apps/api/alembic.ini"
SUPABASE_ALEMBIC_SECURITY_MIGRATION = (
    ROOT / "supabase/migrations/202608260012_secure_alembic_version.sql"
)
SUPABASE_EDITORIAL_CONTENT_MIGRATION = (
    ROOT / "supabase/migrations/202608310013_editorial_content.sql"
)
SUPABASE_EDITORIAL_RAG_MIGRATION = ROOT / "supabase/migrations/202608310014_editorial_rag.sql"


def test_migration_history_has_one_linear_head() -> None:
    config = Config(str(ALEMBIC_CONFIG))
    script = ScriptDirectory.from_config(config)

    assert script.get_bases() == ["20260731_0001"]
    assert script.get_heads() == ["20260831_0011"]


def test_foundation_migration_compiles_to_postgresql_sql() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ALEMBIC_CONFIG),
            "upgrade",
            "head",
            "--sql",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    sql = result.stdout
    assert 'CREATE EXTENSION IF NOT EXISTS "vector"' in sql
    assert 'CREATE SCHEMA IF NOT EXISTS "knowledge"' in sql
    assert "CREATE TABLE knowledge.document_versions" in sql
    assert "CREATE VIEW knowledge.retrievable_chunks" in sql
    assert "d.status = 'published'" in sql
    assert "v.effective_from <= CURRENT_DATE" in sql
    assert "00000000-0000-0000-0000-000000001005" in sql
    assert "idempotency_key VARCHAR(128)" in sql
    assert "retry_scheduled" in sql
    assert "dead_lettered" in sql
    assert "CREATE TABLE ingestion.extraction_artifacts" in sql
    assert "CREATE TABLE ingestion.review_items" in sql
    assert "CREATE TRIGGER trg_audit_events_immutable" in sql
    assert "ck_review_items_decision_fields_consistent" in sql
    assert "CREATE TABLE identity.principals" in sql
    assert "knowledge_publisher" in sql
    assert "content_author" in sql
    assert "CREATE TABLE knowledge.publication_records" in sql
    assert "CREATE TABLE knowledge.document_lifecycle_events" in sql
    assert "CREATE TABLE knowledge.index_jobs" in sql
    assert "CREATE TABLE ingestion.snapshot_objects" in sql
    assert "CREATE TABLE ingestion.managed_source_configs" in sql
    assert "SET trust_tier = 1" in sql
    assert 'CREATE SCHEMA IF NOT EXISTS "content"' in sql
    assert "CREATE TABLE content.posts" in sql
    assert "CREATE TABLE content.post_versions" in sql
    assert "CREATE TABLE content.post_sources" in sql
    assert "CREATE TABLE content.publication_records" in sql
    assert "CREATE TABLE content.rag_chunks" in sql
    assert "include_in_rag BOOLEAN DEFAULT false NOT NULL" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "'anon', 'authenticated', 'service_role'" in sql
    assert "ALTER DEFAULT PRIVILEGES IN SCHEMA content" in sql
    assert "trg_content_post_versions_guard" in sql
    assert "SET search_path = ''" in sql
    assert "non-draft content revisions cannot be edited" in sql
    assert "cost_microusd INTEGER" in sql


def test_foundation_downgrade_compiles_to_postgresql_sql() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ALEMBIC_CONFIG),
            "downgrade",
            "20260831_0010:base",
            "--sql",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    sql = result.stdout
    assert 'DROP SCHEMA IF EXISTS "knowledge" CASCADE' in sql
    assert 'DROP EXTENSION IF EXISTS "vector"' in sql
    assert "DROP TABLE knowledge.index_jobs" in sql
    assert "DROP TABLE knowledge.document_lifecycle_events" in sql
    assert "DROP TABLE ingestion.snapshot_objects" in sql
    assert "DROP TABLE ingestion.managed_source_configs" in sql
    assert "DROP TABLE content.post_versions" in sql
    assert 'DROP SCHEMA IF EXISTS "content"' in sql


def test_supabase_migration_ledger_is_not_exposed_to_client_roles() -> None:
    sql = SUPABASE_ALEMBIC_SECURITY_MIGRATION.read_text(encoding="utf-8").lower()

    assert "alter table public.alembic_version enable row level security" in sql
    assert "revoke all privileges on table public.alembic_version" in sql
    assert "from public, anon, authenticated, service_role" in sql
    assert "create policy" not in sql


def test_editorial_content_has_a_sql_editor_safe_companion_migration() -> None:
    sql = SUPABASE_EDITORIAL_CONTENT_MIGRATION.read_text(encoding="utf-8").lower()

    assert sql.startswith("-- secure, versioned editorial content foundation.")
    assert "begin;" in sql
    assert sql.rstrip().endswith("commit;")
    assert "expected alembic revision 20260825_0009" in sql
    assert "create schema if not exists content" in sql
    assert "create table content.posts" in sql
    assert "create table content.post_versions" in sql
    assert "create table content.post_sources" in sql
    assert "create table content.publication_records" in sql
    assert "create trigger trg_content_post_versions_guard" in sql
    assert "set search_path = ''" in sql
    assert sql.count("enable row level security") == 7
    assert "array['anon', 'authenticated', 'service_role']" in sql
    assert "alter default privileges in schema content" in sql
    assert "set version_num = '20260831_0010'" in sql
    assert "create policy" not in sql


def test_editorial_rag_has_a_sql_editor_safe_companion_migration() -> None:
    sql = SUPABASE_EDITORIAL_RAG_MIGRATION.read_text(encoding="utf-8").lower()

    assert sql.startswith("-- opt-in editorial content retrieval")
    assert "begin;" in sql
    assert sql.rstrip().endswith("commit;")
    assert "expected alembic revision 20260831_0010" in sql
    assert "add column include_in_rag boolean default false not null" in sql
    assert "create table content.rag_chunks" in sql
    assert "alter table content.rag_chunks enable row level security" in sql
    assert "create trigger trg_content_post_versions_rag_guard" in sql
    assert "set search_path = ''" in sql
    assert "array['anon', 'authenticated', 'service_role']" in sql
    assert "set version_num = '20260831_0011'" in sql
    assert "create policy" not in sql
