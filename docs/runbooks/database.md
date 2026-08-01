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

Restore only into an empty, isolated database:

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

Production RPO, RTO, retention, and backup frequency remain blocked on D-010.

