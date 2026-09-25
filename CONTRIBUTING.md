# Contributing

## Branch model

`fix/*` / `feature/*` / `docs/*` → merge to `develop` → promote to `main`. All merges require CI green; branch protection enforces this on both.

## Commits

Conventional Commits only: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `style`, `ci` — e.g. `feat(meetings): add recorder upload`.

## Backend (apps/backend)

- Tests: `cd apps/backend && TEST_DATABASE_URL=postgresql+asyncpg://reunionai:reunionai@localhost:5433/reunionai .venv/bin/pytest -q`
- Lint/type: `.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app`

## Frontend (apps/frontend)

- Tests: `cd apps/frontend && pnpm test`

## Review policy

Native review runs per candidate. Advisory findings are informational and funnelled into issue follow-ups (see issue #80). Only BLOCKING/CRITICAL findings require a bounded correction round.

## Issue labels

`bug`, `enhancement`, `documentation`, `good first issue`, `help wanted`.
