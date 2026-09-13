# Tasks: auth-multitenant-foundation

**Change:** `auth-multitenant-foundation`
**Delivery strategy:** `ask-on-risk`
**Commit convention:** Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`)
**TDD:** strict where runners exist (`pytest` backend, `vitest` frontend). Test first, then implement.

Sources: `proposal.md`, `specs/**/spec.md`, `architecture.md`, `data-model.md`, `api-contract.md`, `test-plan.md`.

---

## Phase 0 — Scaffolding & Tooling

- [x] **TASK-001** `chore: scaffold backend FastAPI modular layout` — `apps/backend/app/{main.py,core/,modules/{auth,users,organizations,rbac,audit}}`, settings via env, health endpoint. Tests: pytest sanity test on settings/health. (AC: architecture.md §2)
- [x] **TASK-002** `chore: configure pytest + ruff + mypy for backend` — `pyproject.toml`, fixtures, coverage. Tests: example test passes in CI-locally.
- [x] **TASK-003** `chore: scaffold frontend Astro + React + TS + Tailwind` — `apps/frontend`, vitest config. Tests: vitest smoke test. (AC: proposal §3.3)
- [x] **TASK-004** `chore: add .env.example matching architecture.md §10.1` — all keys incl. JWT keys, Argon2 params, rate-limit config. Tests: settings load validation test.

## Phase 1 — Database & Migrations

- [x] **TASK-010** `chore: set up Alembic with async engine` — non-destructive rules, rollback tested. Tests: migration upgrade/downgrade smoke test.
- [x] **TASK-011** `feat: migration 001 init_core (tenants/organizations/properties/users/memberships)` — UUID PKs, `tenant_id`, indexes, FKs per data-model.md §2.1. Tests: schema introspection asserts tenant_id + indexes exist.
- [x] **TASK-012** `feat: migration 002 auth (sessions/refresh_tokens/mfa)` — rotation chain fields (`replaced_by_token_id`), per data-model §2.2. Tests: FK + constraint checks.
- [x] **TASK-013** `feat: migration 003 rbac (roles/permissions/role_permissions/user_roles)` — unique `resource.action`, cascade rules, seeding hooks. Tests: constraint tests.
- [x] **TASK-014** `feat: migration 004 audit (audit_events append-only)` — no UPDATE/DELETE paths; actor, tenant, action, resource, resource_id, timestamp, ip, user_agent, metadata. Tests: append-only enforcement test.

## Phase 2 — Core Security Primitives

- [x] **TASK-020** `feat: password hashing service (Argon2id)` — passlib wrapper in `core/security.py`. Tests: hash/verify, wrong-password rejection, timing sanity.
- [x] **TASK-021** `feat: JWT service RS256 (15-min access tokens)` — key loading from env, claims, expiry. Tests: sign/verify, expired token rejection, wrong-key rejection.
- [x] **TASK-022** `feat: in-memory rate limiter` — per architecture §7, on auth endpoints. Tests: limit hit → 429; window reset.

## Phase 3 — Tenant Context & Authorization Primitives

- [x] **TASK-030** `feat: tenant-context dependency (resolution chain)` — user → membership → tenant → role → permission per architecture §3; never trust request-supplied `tenant_id`. Tests: unit tests of chain with fixture memberships.
- [x] **TASK-031** `feat: require_permission dependency (resource.action)` — union resolution per architecture §5.3. Tests: allowed/denied matrix incl. 401 vs 403.

## Phase 4 — Auth Module

- [x] **TASK-040** `feat: POST /auth/register (org + org-admin)` — creates organization + tenant + admin user + base roles seeding. Tests: happy path, duplicate, tenant bootstrapped correctly.
- [x] **TASK-041** `feat: POST /auth/login with MFA gate` — Argon2id verify, MFA challenge for enrolled users. Tests: bad password, MFA-required flow, audit event written.

- [ ] **TASK-042** `feat: POST /auth/refresh with rotation + reuse detection` — chain revocation on reuse per architecture §4.2. Tests: rotation, reuse → whole chain revoked (401), expired.
- [ ] **TASK-043** `feat: POST /auth/revoke + logout` — session revocation. Tests: token no longer valid.
- [ ] **TASK-044** `feat: MFA TOTP setup/verify/disable/recovery codes` — `/auth/mfa/*`. Tests: TOTP code verify, recovery code single-use, disable requires auth.
- [ ] **TASK-045** `feat: session management GET/DELETE /users/me/sessions` — list + revoke any session. Tests: revoke other session, current session flagged.
- [ ] **TASK-046** `feat: enforce mandatory MFA for admin roles` — block admin JWT issuance until MFA enrolled. Tests: admin login without MFA → setup forced.

## Phase 5 — Users Module

- [ ] **TASK-050** `feat: users CRUD + profile + password change` — tenant-scoped list/get/update, soft delete, password change with audit. Tests: self-service profile, admin user management, password change invalidates sessions.

## Phase 6 — Organizations Module

- [ ] **TASK-060** `feat: organizations + properties CRUD` — soft-delete cascade, optional property membership. Tests: org isolation, property hierarchy, membership with/without property.

## Phase 7 — RBAC Module

- [ ] **TASK-070** `feat: permission registry + base role seeding` — 10 base roles, per-org custom roles, matrices per data-model §4. Tests: seeding idempotent, custom role CRUD, immutable base roles.

## Phase 8 — Audit Module

- [ ] **TASK-080** `feat: audit service + admin query endpoint` — explicit capture on critical ops, tenant-scoped `audit.read` query. Tests: events recorded for login/permission change; never editable via API.

## Phase 9 — Tenant Isolation / IDOR Suite

- [ ] **TASK-090** `test: cross-tenant isolation suite` — two tenants A/B: every scoped endpoint returns 404 (not 403) for the other tenant's resources; JWT from A cannot read/write B. Tests: full matrix per test-plan.md.

## Phase 10 — Frontend Auth Screens

- [ ] **TASK-100** `feat: login/register/MFA screens wired to /api/v1/auth` — Astro pages + React forms, error states, MFA challenge step. Tests: vitest component tests for forms + API client.

## Phase 11 — Docker, CI & Bootstrap

- [ ] **TASK-110** `chore: docker-compose (frontend, backend, postgres, nginx)` — dev/prod split, no secrets in images. Tests: `docker compose up -d` health smoke.
- [ ] **TASK-111** `feat: super-admin bootstrap CLI` — creates first platform super-admin (Q1 decision). Tests: CLI idempotent, creates audited event.
- [ ] **TASK-112** `chore: GitHub Actions CI (lint, typecheck, unit, integration, build)` — per AGENTS.md §12 gates. Tests: pipeline green.
- [ ] **TASK-113** `docs: README quickstart + docs/architecture notes for this change` — update README if commands changed.

---

## Review Workload Forecast

- **Estimated changed lines:** ~6,000–9,000 (greenfield foundation: backend modules, migrations, tests, frontend screens, infra).
- **400-line budget risk:** High — far exceeds the review budget.
- **Chained PRs recommended:** Yes — per phase: PR-1 = Phases 0–1 (scaffold+DB), PR-2 = Phases 2–3 (security primitives + tenant context), PR-3 = Phase 4 (auth), PR-4 = Phases 5–7 (users/orgs/rbac), PR-5 = Phases 8–9 (audit + IDOR suite), PR-6 = Phases 10–11 (frontend + infra).
- **Decision needed before apply:** Yes (split into chained PRs vs `size:exception` — gated by `ask-on-risk`).
