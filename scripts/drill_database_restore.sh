#!/usr/bin/env bash
set -euo pipefail

source_database="${POSTGRES_DB:-uzbekistan_os}"
database_user="${POSTGRES_USER:-uzbekistan_os}"
restore_database="${RESTORE_DATABASE:-uzbekistan_os_phase2_restore_test}"
backup_path="/tmp/uzbekistan-os-phase2-restore.dump"

if [[ ! "$source_database" =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo "source database name contains unsupported characters" >&2
  exit 2
fi
if [[ ! "$restore_database" =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo "restore database name contains unsupported characters" >&2
  exit 2
fi
if [[ "$restore_database" == "$source_database" ]]; then
  echo "restore database must differ from the source database" >&2
  exit 2
fi

if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose=(docker-compose)
else
  echo "Docker Compose is required" >&2
  exit 1
fi

postgres_exec() {
  "${compose[@]}" exec -T postgres "$@"
}

run_restore_migration() {
  POSTGRES_DB="$restore_database" "${compose[@]}" run --rm --no-deps migrate \
    python -m alembic -c alembic.ini "$@"
}

cleanup() {
  postgres_exec dropdb --username "$database_user" --if-exists "$restore_database" >/dev/null
  postgres_exec rm -f "$backup_path" >/dev/null
}
trap cleanup EXIT

cleanup
postgres_exec pg_dump \
  --username "$database_user" \
  --dbname "$source_database" \
  --format custom \
  --no-owner \
  --no-privileges \
  --file "$backup_path"
postgres_exec sha256sum "$backup_path"
postgres_exec createdb --username "$database_user" "$restore_database"
postgres_exec pg_restore \
  --username "$database_user" \
  --dbname "$restore_database" \
  --exit-on-error \
  --no-owner \
  --no-privileges \
  "$backup_path"

run_restore_migration downgrade -1
downgraded_revision="$(postgres_exec psql --username "$database_user" --dbname "$restore_database" --tuples-only --no-align --command "SELECT version_num FROM alembic_version;")"
if [[ "$downgraded_revision" != "20260731_0004" ]]; then
  echo "migration downgrade did not reach the expected previous revision" >&2
  exit 1
fi
run_restore_migration upgrade head

count_query="SELECT concat_ws('|',
  (SELECT version_num FROM alembic_version),
  (SELECT count(*) FROM geography.languages),
  (SELECT count(*) FROM geography.countries),
  (SELECT count(*) FROM knowledge.domains),
  (SELECT count(*) FROM knowledge.source_organizations),
  (SELECT count(*) FROM knowledge.sources),
  (SELECT count(*) FROM ingestion.source_snapshots),
  (SELECT count(*) FROM ingestion.crawl_jobs),
  (SELECT count(*) FROM ingestion.extraction_artifacts),
  (SELECT count(*) FROM ingestion.review_items),
  (SELECT count(*) FROM audit.events)
);"

source_counts="$(postgres_exec psql --username "$database_user" --dbname "$source_database" --tuples-only --no-align --command "$count_query")"
restore_counts="$(postgres_exec psql --username "$database_user" --dbname "$restore_database" --tuples-only --no-align --command "$count_query")"

if [[ "$source_counts" != "$restore_counts" ]]; then
  echo "restored database counts do not match the source database" >&2
  echo "source:  $source_counts" >&2
  echo "restore: $restore_counts" >&2
  exit 1
fi

view_count="$(postgres_exec psql --username "$database_user" --dbname "$restore_database" --tuples-only --no-align --command "SELECT count(*) FROM knowledge.retrievable_chunks;")"

echo "database restore drill passed"
echo "migration downgrade/upgrade drill passed"
echo "migration-and-count signature: $restore_counts"
echo "retrievable chunk count: $view_count"
