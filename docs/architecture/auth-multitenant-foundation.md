# Architecture notes — auth-multitenant-foundation

MVP change delivering the authenticated, tenant-isolated foundation of ReunionAI.

## Modules delivered

| Module | Surface | Notes |
| --- | --- | --- |
| auth | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/revoke`, `/auth/mfa/*`, `/users/me/sessions` | RS256 access (15 min), rotating refresh tokens with reuse detection, TOTP MFA mandatory for admin roles |
| users | `/users`, `/users/me`, password change | Tenant-scoped CRUD, soft delete, audit on password change |
| organizations | `/organizations`, `/organizations/me/properties`, `/organizations/me/memberships` | Soft-delete cascade; org deletion is super-admin only |
| rbac | `/rbac/permissions`, `/rbac/roles`, assignments | Permission registry + base roles + per-org custom roles; cross-tenant 404 |
| audit | `/audit`, `/audit/{id}` | Append-only (DB trigger), `audit.read` guard, paginated + filtered |

## Security invariants

- Tenant context is resolved server-side from the JWT membership chain; client-supplied `tenant_id` is never trusted.
- Cross-tenant access returns **404** (never 403) on every tenant-scoped endpoint, enforced by `tests/integration/isolation/`.
- Audit events are immutable: no UPDATE/DELETE API paths and a Postgres trigger enforces it at the DB level.
- Rate limiting (in-memory sliding window) on auth/MFA endpoints.

## Infra

- `docker compose up -d`: postgres + backend (migrations run at startup) + frontend-nginx (static + `/api` proxy). Prod overrides in `docker-compose.prod.yml`.
- Bootstrap: `python -m app.cli bootstrap-superadmin` creates the first platform super-admin (idempotent, audited).
- CI: `.github/workflows/ci.yml` — ruff/format/mypy/pytest + vitest/tsc/astro build, actions pinned to SHAs.

## Deferred

- STT/OCR/minutes modules, GraphQL, Redis/worker (no consumer yet), email notifications.
