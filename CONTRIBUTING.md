# Contributing

## Branches and reviews

- Create focused branches from `staging`; promote reviewed releases from `staging` to `main`.
- Keep commits scoped and use an imperative Conventional Commit subject such as `feat(api): add readiness checks`.
- Pull requests require the checks in `.github/workflows/ci.yml` and review from the owners in `.github/CODEOWNERS`.
- Never commit `.env` files, access tokens, private keys, production data, source-response bodies, or generated build output.

## Required validation

From the repository root:

```bash
pnpm install --frozen-lockfile
pnpm format:check
pnpm lint
pnpm typecheck
pnpm build
pnpm audit --audit-level=high

apps/api/.venv/bin/python -m ruff format --check apps/api scripts/validate_contracts.py
apps/api/.venv/bin/python -m ruff check apps/api scripts/validate_contracts.py
apps/api/.venv/bin/python -m pytest apps/api/tests
apps/api/.venv/bin/python scripts/validate_contracts.py
apps/api/.venv/bin/python -m pip install --upgrade pip==26.2
apps/api/.venv/bin/python -m pip_audit --skip-editable
```

Contract changes must update the checked-in OpenAPI or JSON Schema, runtime models, fixtures, and contract tests together. Database changes require a new Alembic revision plus forward and downgrade compilation tests.

## Security reports

Do not open a public issue for a suspected vulnerability or leaked credential. Follow [SECURITY.md](./SECURITY.md).
