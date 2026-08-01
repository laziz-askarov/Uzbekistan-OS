# Security policy

## Reporting

Report suspected vulnerabilities privately through GitHub's repository security advisory feature. Do not include real credentials, personal data, government-source response bodies, or exploit details in public issues.

## Secrets and environments

- Commit only safe development defaults in `.env.example`; local `.env` files stay ignored.
- Store GitHub deployment credentials in the protected `staging` environment and runtime secrets in the staging host's root-owned `/opt/uzbekistan-os/.env` file.
- Use distinct PostgreSQL, object-store, and SSH credentials for each environment. Rotate a credential immediately if it appears in logs, commits, artifacts, or review comments.
- Production content and credentials are prohibited in development fixtures.
- Dependency audits fail CI for known high-severity JavaScript issues and any known Python vulnerability.

Supported-version and incident-response commitments will be added before public beta when production ownership and reliability targets are approved.
