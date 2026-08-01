# Database runbook

## Local configuration

The API reads `DATABASE_URL`. The development default points to PostgreSQL on `localhost:5432`; Docker Compose overrides the hostname to `postgres`.

## Migration commands

From the repository root with the API virtual environment active:

```bash
python -m alembic -c apps/api/alembic.ini current
python -m alembic -c apps/api/alembic.ini upgrade head
python -m alembic -c apps/api/alembic.ini downgrade -1
```

Compile migrations without connecting to a database:

```bash
python -m alembic -c apps/api/alembic.ini upgrade head --sql
```

Never edit an applied migration. Add a new revision and test both upgrade and downgrade paths.

## Backup

Create a compressed, portable logical backup:

```bash
pg_dump --format=custom --no-owner --no-privileges --file=uzbekistan-os.dump "$DATABASE_URL"
```

Record the application version, migration head, backup timestamp, database engine version, and checksum beside the backup artifact. Encrypt backups at rest and keep them outside the application container.

## Restore drill

For the local Compose stack, run the repository-owned drill:

```bash
scripts/drill_database_restore.sh
```

The script creates only the isolated
`uzbekistan_os_phase2_restore_test` database, compares the migration head and
critical table counts, queries the retrieval-eligibility view, and removes the
temporary database and backup when it exits. Override the target only with a
validated disposable database name through `RESTORE_DATABASE`.

For a manually managed environment, restore only into an empty, isolated
database using the following procedure:

```bash
createdb uzbekistan_os_restore_test
pg_restore --exit-on-error --no-owner --no-privileges --dbname=uzbekistan_os_restore_test uzbekistan-os.dump
```

After restoration:

1. Confirm the Alembic head matches the release being tested.
2. Count documents, versions, chunks, sources, snapshots, and audit events against the source database.
3. Verify the `knowledge.retrievable_chunks` view excludes draft, expired, superseded, and future-effective records.
4. Run API integration and retrieval smoke tests.
5. Destroy the isolated restore database after recording the drill result.

ADR 0016 sets the MVP PostgreSQL target at a one-hour RPO and four-hour RTO using
managed point-in-time recovery with a seven-day PITR window and 30-day daily-backup
retention. Exercise this database restore monthly and the full service recovery
quarterly. Evidence objects have a 24-hour RPO and eight-hour RTO with versioning,
checksum inventory, and publication blocked until restored evidence verifies.

## Validation record

The local Compose drill passed on 2026-08-01 against PostgreSQL 17 at migration
`20260731_0005`. It restored the development fixture database into
`uzbekistan_os_phase2_restore_test`, matched the migration/table-count signature,
queried `knowledge.retrievable_chunks`, downgraded to `20260731_0004`, upgraded
back to head, and removed the disposable database and backup.
