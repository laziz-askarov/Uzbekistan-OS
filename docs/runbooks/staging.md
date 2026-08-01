# Staging deployment runbook

## Architecture

Every successful `staging` CI run can build immutable API, worker, and web images tagged with the commit SHA, publish them to GHCR, deploy them to a Docker Compose host, and run external liveness, readiness, and web smoke checks. A failed external smoke test automatically invokes the previous image-set rollback.

The staging registry is intentionally empty and cannot authorize production crawling. PostgreSQL, Redis, and MinIO use persistent Docker volumes. Bind ports default to `127.0.0.1`; terminate TLS in a host-managed reverse proxy and expose only the public web and API origins.

## One-time host preparation

1. Provision a dedicated Linux host with Docker Engine, Docker Compose v2, OpenSSH, and `curl`.
2. Create a least-privilege deployment user that can run Docker and write only `/opt/uzbekistan-os`.
3. Authenticate Docker to `ghcr.io` with a read-only package token for this repository.
4. Copy `infra/staging/.env.example` to `/opt/uzbekistan-os/.env`, replace every placeholder, URL-encode the database password inside `DATABASE_URL`, and set mode `0600`.
5. Configure a TLS reverse proxy from the staging web origin to `127.0.0.1:3000` and from the staging API origin to `127.0.0.1:8000`.
6. Record the host's SSH public key in the deployment user's `authorized_keys` and capture the host key with `ssh-keyscan` over a trusted channel.

Do not place production credentials, production source registries, or user data on this host.

## GitHub configuration

Create a protected GitHub environment named `staging`. Require approval if desired, and add:

| Kind | Name | Value |
|---|---|---|
| Repository variable | `STAGING_ENABLED` | `true` only after host preparation |
| Environment variable | `STAGING_ROOT` | `/opt/uzbekistan-os` |
| Environment variable | `STAGING_WEB_URL` | Public HTTPS web origin |
| Environment variable | `STAGING_API_URL` | Public HTTPS API origin |
| Environment secret | `STAGING_HOST` | SSH hostname or address |
| Environment secret | `STAGING_USER` | Dedicated deployment user |
| Environment secret | `STAGING_SSH_PRIVATE_KEY` | Deployment private key |
| Environment secret | `STAGING_SSH_KNOWN_HOSTS` | Pinned host-key line |

Protect `main` and `staging` with required CI checks and CODEOWNERS review. Never store the host `.env` contents in GitHub variables, workflow artifacts, or repository files.

## Deployment and smoke test

Push to `staging`. The CI workflow runs the reusable `.github/workflows/staging.yml` deployment job only after its web, API, and infrastructure jobs succeed. The deployment publishes commit-SHA images and invokes `scripts/deploy_staging.sh`. The remote deployment:

1. pulls the immutable image set;
2. starts PostgreSQL, Redis, and MinIO;
3. applies forward migrations;
4. provisions the evidence bucket;
5. synchronizes the empty staging registry;
6. starts API, worker, scheduler, and web services;
7. waits for dependency-aware API readiness.

The workflow then runs `scripts/smoke_staging.sh` against the public HTTPS origins. A passing API response requires PostgreSQL, Redis, and the evidence bucket to report `ok`.

## Rollback

If the external smoke test fails, the workflow automatically activates `.release.previous.env`. To roll back manually on the host:

```bash
sudo -u uzbekistan-os env STAGING_ROOT=/opt/uzbekistan-os \
  /opt/uzbekistan-os/deploy_staging.sh rollback
```

Database migrations are forward-only during application rollback. Every staging migration must remain backward-compatible with the previous application image; a destructive schema rollback requires a separately reviewed database procedure.

## Exit-gate record

Record the workflow URL, deployed commit, web/API origins, smoke-test result, rollback test result, operator, and timestamp in the release issue. Phase 1 is not operationally complete until one real deployment and rollback have passed on the configured staging host.
