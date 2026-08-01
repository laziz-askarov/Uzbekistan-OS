import subprocess
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_CONFIG = ROOT / "apps/api/alembic.ini"


def test_migration_history_has_one_linear_head() -> None:
    config = Config(str(ALEMBIC_CONFIG))
    script = ScriptDirectory.from_config(config)

    assert script.get_bases() == ["20260731_0001"]
    assert script.get_heads() == ["20260731_0001"]


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


def test_foundation_downgrade_compiles_to_postgresql_sql() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ALEMBIC_CONFIG),
            "downgrade",
            "20260731_0001:base",
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
