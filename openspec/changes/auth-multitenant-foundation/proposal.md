# SDD Proposal: auth-multitenant-foundation

**Change ID:** `auth-multitenant-foundation`
**Status:** Draft
**Date:** 2025-01-15
**Author:** gentle-meeting-documentation-agent
**Traceability:** PRD-ReunionAI.md §6, §7, §8, §9, §10, §28, §29, §30, §31, §33

---

## 1. Context

ReunionAI is a greenfield multi-tenant platform for meeting management, transcription, and documentation. The approved PRD defines a modular monolith architecture with Python/FastAPI backend, PostgreSQL persistence, and Astro/React frontend. This change establishes the foundational authentication, multi-tenancy, RBAC, and audit infrastructure upon which all subsequent features depend.

The PRD explicitly requires:

- Multi-tenant hierarchy: Platform → Organization → Properties/Groups → Users/Roles (PRD §6)
- Tenant isolation with `tenant_id` on every tenant-scoped table from day one (PRD §29, §30)
- Secure authentication: password hashing, short-lived access tokens, rotating refresh tokens, MFA/2FA, session control, rate limiting (PRD §9)
- RBAC with `resource.action` permissions, custom roles per organization, backend-enforced (PRD §8)
- Append-only audit events with actor, tenant, action, resource, resource_id, timestamp, ip, user_agent, metadata (PRD §10)
- Modular backend layout with clear module boundaries (PRD §28)
- Docker Compose baseline with frontend, backend, postgres, nginx; Redis/worker only if justified (PRD §31, AGENTS.md §3.16)

---

## 2. Problem Statement

**What pain/opportunity makes this change worth doing now:**
No executable system exists. All downstream features (meetings, recordings, transcription, OCR, documents, minutes, notifications) require a verified authentication and authorization foundation with proven tenant isolation. Without this foundation, we cannot safely build any tenant-scoped feature.

**Current-state gap:**

- No backend code, no database schema, no API, no frontend auth flows
- No tenant-context propagation mechanism
- No audit trail infrastructure
- No Docker/CI baseline

**Business risk if deferred:**
Every subsequent change would need to retrofit tenant isolation, RBAC, and audit — exponentially more expensive and error-prone. The PRD's "Correctness > Security > Tenant Isolation > Traceability" priority order (AGENTS.md §13) demands this foundation first.

---

## 3. Goals (Scope)

### 3.1 Backend — Core Modules

| Module | Responsibility |
| -------- | ---------------- |
| `auth` | Login, register, token issuance/refresh/revocation, MFA enrollment/verification, session management, rate limiting |
| `users` | User CRUD, profile, password change, MFA device management, soft-delete |
| `organizations` | Organization CRUD, property/group management, tenant membership |
| `rbac` | Permission registry (`resource.action`), role definitions, role↔permission assignments, user↔role assignments per tenant, custom roles per organization |
| `audit` | Append-only `audit_events` table, middleware to auto-record critical operations, query API for admins |

### 3.2 Cross-Cutting Infrastructure

- **FastAPI modular layout**: `app/modules/{auth,users,organizations,rbac,audit}/` with routers, services, schemas, repositories
- **Tenant-context middleware/dependency**: Extracts `tenant_id` from authenticated user's active membership; injects into request state; all tenant-scoped queries route through this
- **Alembic migrations**: Versioned, non-destructive, with `tenant_id` columns + indexes + FKs on all tenant-scoped tables
- **Environment-based config**: Pydantic Settings, `.env.example` committed, secrets never baked
- **Docker Compose baseline**: `frontend`, `backend`, `postgres`, `nginx` (dev + prod overrides); Redis and worker services commented out with justification note per AGENTS.md §3.16
- **Test configuration**: `pytest` (backend) + `vitest` (frontend) with tenant-isolation test fixtures

### 3.3 Frontend — Minimal Auth Screens

- `/login` — email/password + MFA challenge
- `/register` — organization creation + first admin user
- `/mfa/setup` — TOTP enrollment (QR code)
- `/mfa/verify` — TOTP challenge during login
- Tailwind CSS, React components, TypeScript, Astro island pattern

### 3.4 Security Requirements (Non-Negotiable)

- Password hashing: Argon2id (via `passlib`)
- Access tokens: JWT, 15-min TTL, RS256, `tenant_id` + `user_id` + `permissions` claims
- Refresh tokens: Rotating, 30-day TTL, stored hashed in DB, reuse detection → revoke entire chain
- MFA: TOTP (RFC 6238), mandatory for admin roles, optional for others
- Rate limiting: Per-IP + per-user on auth endpoints (login, register, token refresh, MFA)
- CORS: Strict allowlist from config
- Security headers: CSP, HSTS, X-Frame-Options, Referrer-Policy via middleware
- IDOR prevention: Every repository query filters by `tenant_id` from context; integration tests verify Tenant A ≠ Tenant B

---

## 4. Non-Goals (Explicitly Deferred)

| Area | Deferred To |
| ------ | ------------- |
| Meetings, recordings, transcription, STT pipeline | Future change |
| OCR, documents, document versions | Future change |
| Minutes, reviews, approvals, publication lifecycle | Future change |
| Notifications, email provider, WhatsApp/Telegram | Future change |
| Search (PostgreSQL FTS / vector) | Future change |
| Admin dashboard content (org/users/roles UI beyond auth flows) | Future change |
| GraphQL API | Future change (REST only for MVP) |
| Redis-backed queues/workers | Only if justified by load; not in this change |
| Multi-jurisdiction legal rules | PRD §36 — pluggable config later |
| Electronic signature | PRD §5 — V2 |
| Mobile apps | PRD §5 — V3 |

---

## 5. Architecture

### 5.1 Module Dependency Graph (Acyclic Target)

```
app/
├── core/                    # Shared: config, security, database, exceptions, middleware
│   ├── config.py            # Pydantic Settings
│   ├── security.py          # JWT, password hashing, token utilities
│   ├── database.py          # SQLAlchemy engine, session, base
│   ├── middleware/
│   │   ├── tenant_context.py    # TenantContextMiddleware, get_tenant_id()
│   │   ├── audit_middleware.py  # Auto-audit for mutating endpoints
│   │   └── rate_limit.py        # Redis-backed (optional) or in-memory fallback
│   └── dependencies.py      # FastAPI deps: get_current_user, get_db, require_permission
├── modules/
│   ├── auth/
│   │   ├── router.py        # POST /login, /register, /refresh, /revoke, /mfa/*
│   │   ├── service.py       # Business logic
│   │   ├── schemas.py       # Pydantic request/response
│   │   ├── repository.py    # Data access
│   │   └── models.py        # SQLAlchemy: User, RefreshToken, MFADevice, Session
│   ├── users/
│   │   ├── router.py        # CRUD /me, /users/{id}
│   │   ├── service.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   └── models.py        # User (extends core), Profile
│   ├── organizations/
│   │   ├── router.py        # CRUD org, properties, memberships
│   │   ├── service.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   └── models.py        # Organization, Property, Membership
│   ├── rbac/
│   │   ├── router.py        # Permissions, roles, assignments
│   │   ├── service.py       # Permission resolution, role management
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   └── models.py        # Permission, Role, RolePermission, UserRole
│   └── audit/
│       ├── router.py        # GET /audit (admin)
│       ├── service.py
│       ├── schemas.py
│       ├── repository.py
│       └── models.py        # AuditEvent
└── main.py                  # FastAPI app factory, router inclusion
```

### 5.2 Tenant Resolution Chain (PRD §30)

```
Request → AuthMiddleware (validates JWT) → TenantContextMiddleware
    → resolves user.active_membership.tenant_id
    → stores in request.state.tenant_id
    → all repositories query with .filter(tenant_id=request.state.tenant_id)
```

**Critical invariant:** Never trust client-supplied `tenant_id`. Always derive from authenticated user's membership.

### 5.3 RBAC Permission Model

- **Permission**: `resource.action` (e.g., `meeting.create`, `minutes.approve`)
- **Role**: Named collection of permissions, scoped to organization (custom roles allowed)
- **UserRole**: Links user → role → organization (tenant)
- **Resolution**: `user.permissions = union(role.permissions for role in user.roles_in_tenant)`
- **Enforcement**: `@require_permission("meeting.create")` dependency on routers

### 5.4 Audit Event Schema

```sql
audit_events (
    id UUID PK,
    actor_user_id UUID FK → users.id,
    tenant_id UUID FK → organizations.id,
    action VARCHAR(100),           -- e.g., "user.login", "meeting.create"
    resource VARCHAR(100),         -- e.g., "meeting", "user"
    resource_id UUID,              -- nullable for collection actions
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip INET,
    user_agent TEXT,
    metadata JSONB                 -- extensible context
)
```

- Append-only: no UPDATE/DELETE via ORM; DB-level trigger or REVOKE to enforce
- Auto-populated by `AuditMiddleware` for mutating endpoints (POST/PATCH/DELETE)

---

## 6. Data Changes

### 6.1 Core Tables (Alembic Migration Sequence)

| Migration | Tables | Key Columns |
| ----------- | -------- | ------------- |
| `001_init_core` | `users`, `organizations`, `properties`, `memberships` | `tenant_id` on all except `users` (global); `memberships` links user↔org↔property |
| `002_auth` | `refresh_tokens`, `mfa_devices`, `sessions` | `user_id` FK, `token_hash`, `expires_at`, `revoked_at`, `replaced_by_token_id` (rotation chain) |
| `003_rbac` | `permissions`, `roles`, `role_permissions`, `user_roles` | `organization_id` (tenant) on roles; composite PKs on join tables |
| `004_audit` | `audit_events` | `actor_user_id`, `tenant_id`, `action`, `resource`, `resource_id`, `ip`, `user_agent`, `metadata` |

### 6.2 Indexing Strategy

- `users`: unique index on `email` (global), index on `is_active`
- `memberships`: unique on `(user_id, organization_id)`, index on `organization_id`, `property_id`
- `refresh_tokens`: index on `user_id`, `expires_at`, `revoked_at`; unique on `token_hash`
- `mfa_devices`: unique on `(user_id, name)` for named devices
- `roles`: unique on `(organization_id, name)`
- `user_roles`: unique on `(user_id, role_id, organization_id)`
- `audit_events`: index on `(tenant_id, timestamp DESC)`, `(actor_user_id, timestamp DESC)`, `(resource, resource_id)`

### 6.3 Soft Delete Policy

- `users`: soft delete (`deleted_at`) only — audit trail requires actor reference
- `organizations`, `properties`: soft delete with cascade to memberships
- `refresh_tokens`, `mfa_devices`, `sessions`: hard delete on revocation/expiry (no audit value post-revocation)
- `audit_events`: **never deleted**

---

## 7. API Changes (REST `/api/v1/`)

### 7.1 Auth Module

| Method | Path | Auth | Permission | Description |
| -------- | ------ | ------ | ------------ | ------------- |
| POST | `/auth/register` | None | — | Create org + first admin user; returns access+refresh tokens |
| POST | `/auth/login` | None | — | Email/password → access+refresh; triggers MFA challenge if enabled |
| POST | `/auth/refresh` | Refresh token | — | Rotate refresh token; detect reuse → revoke chain |
| POST | `/auth/revoke` | Access token | — | Revoke current refresh token (logout) |
| POST | `/auth/mfa/setup` | Access token | `user.mfa.manage` | Return TOTP secret + QR code |
| POST | `/auth/mfa/verify` | Access token | `user.mfa.manage` | Verify TOTP code, enable MFA |
| POST | `/auth/mfa/disable` | Access token | `user.mfa.manage` | Disable MFA (requires password confirm) |
| POST | `/auth/mfa/challenge` | Partial token (post-login) | — | Verify TOTP during login flow |

### 7.2 Users Module

| Method | Path | Auth | Permission | Description |
| -------- | ------ | ------ | ------------ | ------------- |
| GET | `/users/me` | Access token | — | Current user profile + permissions |
| PATCH | `/users/me` | Access token | `user.update` | Update profile (name, avatar) |
| POST | `/users/me/password` | Access token | `user.password.change` | Change password (current + new) |
| GET | `/users/me/sessions` | Access token | `user.session.read` | List active sessions |
| DELETE | `/users/me/sessions/{id}` | Access token | `user.session.revoke` | Revoke specific session |
| GET | `/users` | Access token | `user.read` | List users in tenant (admin) |
| GET | `/users/{id}` | Access token | `user.read` | Get user in tenant |
| PATCH | `/users/{id}` | Access token | `user.update` | Update user (admin) |
| DELETE | `/users/{id}` | Access token | `user.delete` | Soft-delete user |

### 7.3 Organizations Module

| Method | Path | Auth | Permission | Description |
| -------- | ------ | ------ | ------------ | ------------- |
| POST | `/organizations` | Access token | `organization.create` | Create organization (super-admin only) |
| GET | `/organizations/me` | Access token | `organization.read` | Current user's organization |
| PATCH | `/organizations/me` | Access token | `organization.update` | Update org settings |
| GET | `/organizations/me/properties` | Access token | `property.read` | List properties/groups |
| POST | `/organizations/me/properties` | Access token | `property.create` | Create property/group |
| PATCH | `/organizations/me/properties/{id}` | Access token | `property.update` | Update property |
| DELETE | `/organizations/me/properties/{id}` | Access token | `property.delete` | Delete property |
| GET | `/organizations/me/memberships` | Access token | `membership.read` | List members |
| POST | `/organizations/me/memberships` | Access token | `membership.create` | Invite/add member |
| PATCH | `/organizations/me/memberships/{id}` | Access token | `membership.update` | Update member role/property |
| DELETE | `/organizations/me/memberships/{id}` | Access token | `membership.delete` | Remove member |

### 7.4 RBAC Module

| Method | Path | Auth | Permission | Description |
| -------- | ------ | ------ | ------------ | ------------- |
| GET | `/rbac/permissions` | Access token | `permission.read` | List all permissions |
| GET | `/rbac/roles` | Access token | `role.read` | List roles in tenant |
| POST | `/rbac/roles` | Access token | `role.create` | Create custom role |
| PATCH | `/rbac/roles/{id}` | Access token | `role.update` | Update role (name, permissions) |
| DELETE | `/rbac/roles/{id}` | Access token | `role.delete` | Delete custom role (not system roles) |
| POST | `/rbac/roles/{id}/permissions` | Access token | `role.permission.assign` | Assign permission to role |
| DELETE | `/rbac/roles/{id}/permissions/{perm_id}` | Access token | `role.permission.revoke` | Revoke permission from role |
| POST | `/rbac/users/{user_id}/roles` | Access token | `user.role.assign` | Assign role to user in tenant |
| DELETE | `/rbac/users/{user_id}/roles/{role_id}` | Access token | `user.role.revoke` | Revoke role from user |

### 7.5 Audit Module

| Method | Path | Auth | Permission | Description |
|--------|------|------|------------|-------------|
| GET | `/audit` | Access token | `audit.read` | Paginated, filterable audit log (tenant-scoped) |
| GET | `/audit/{id}` | Access token | `audit.read` | Single event detail |

---

## 8. Security Design Decisions

| Decision | Rationale | Trade-off |
| ---------- | ----------- | ----------- |
| **Service-layer tenant enforcement** (not RLS only) | Explicit, testable, portable; RLS as defense-in-depth later | More code than pure RLS |
| **Rotating refresh tokens with reuse detection** | Prevents token theft replay; OWASP recommended | Slightly more complex token storage |
| **Argon2id for passwords** | Memory-hard, future-proof, recommended by OWASP | Requires `passlib[argon2]`; slower than bcrypt (intentional) |
| **JWT RS256 with short TTL** | Stateless verification, key rotation possible, limits blast radius | Requires key management (JWKS endpoint later) |
| **Tenant context via middleware + dependency** | Centralized, hard to bypass, testable via override | Must ensure all code paths use dependency |
| **Audit middleware auto-capture** | Guarantees coverage for mutating endpoints | May over-capture; filter noise in query API |
| **Redis optional for rate limiting** | AGENTS.md §3.16: "Do not introduce Redis without concrete need" | In-memory fallback less accurate under scale; acceptable for MVP |

---

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
| ------ | ------------ | -------- | ------------ |
| **Tenant_id propagation bugs** | High | Critical (data leak) | 1. Centralized `get_tenant_id()` dependency; 2. Repository base class enforces filter; 3. IDOR integration tests for every module; 4. Code review checklist item |
| **Refresh token rotation edge cases** (concurrent requests, network failure) | Medium | High (account lockout / security gap) | 1. `replaced_by_token_id` chain tracking; 2. Grace window (30s) for concurrent refresh; 3. Comprehensive unit tests for race conditions |
| **RLS vs service-layer enforcement confusion** | Medium | Medium | Document decision in ADR; use service-layer as primary, RLS as future defense-in-depth only |
| **MFA enrollment UX complexity** | Low | Medium | TOTP only for MVP; QR + backup codes; clear error messages |
| **Migration rollback complexity** | Low | High | All migrations non-destructive; down migrations provided; test rollback in CI |
| **Redis dependency creep** | Medium | Low (architectural drift) | Explicit justification required in PR; commented-out in compose with note |

---

## 10. Success Criteria (Acceptance)

### 10.1 Functional

- [ ] `POST /auth/register` creates org + admin user + membership; returns valid tokens
- [ ] `POST /auth/login` → access token (15m) + refresh token (30d); MFA challenge flow works
- [ ] `POST /auth/refresh` rotates refresh token; reuse detection revokes chain
- [ ] `GET /users/me` returns user with resolved permissions for current tenant
- [ ] RBAC: custom role creation, permission assignment, user-role assignment all work
- [ ] Tenant isolation: Tenant A user cannot read Tenant B users/organizations/audit events
- [ ] Audit events recorded for: login, logout, password change, MFA enable/disable, user CRUD, org CRUD, role/permission changes
- [ ] Frontend: login → MFA (if enabled) → dashboard redirect; register creates org + logs in

### 10.2 Security

- [ ] All auth endpoints rate-limited (5 req/min/IP, 20 req/min/user)
- [ ] Passwords hashed with Argon2id (verified via test)
- [ ] JWT tokens RS256, `tenant_id` claim present, validated on every request
- [ ] CORS allowlist enforced; security headers present
- [ ] IDOR test suite: 100% coverage on tenant-scoped endpoints (automated in CI)

### 10.3 Infrastructure

- [ ] `docker compose up -d` brings up frontend, backend, postgres, nginx (dev + prod)
- [ ] Alembic migrations apply cleanly; `alembic downgrade base` rolls back
- [ ] `pytest` runs unit + integration tests; `vitest` runs frontend tests
- [ ] CI pipeline: lint → type-check → unit → integration → security scan → build

### 10.4 Documentation

- [ ] OpenAPI spec generated from FastAPI (`/openapi.json`)
- [ ] Architecture decision records (ADRs) for: tenant enforcement strategy, token rotation, MFA choice
- [ ] `.env.example` with all required variables documented
- [ ] README with local dev quickstart

---

## 11. Migration Strategy

1. **Fresh deploy only** — greenfield, no data migration needed
2. **Alembic baseline** — `alembic upgrade head` on empty DB
3. **Seed script** — optional dev seed for super-admin + demo org (behind `SEED_DEMO=true`)
4. **No destructive operations** — all migrations additive; down migrations tested

---

## 12. Rollback Plan

| Component | Rollback Action |
| ----------- | ----------------- |
| Backend code | `git revert` + redeploy; stateless |
| Database | `alembic downgrade -1` per migration (all have `downgrade()`); test in CI |
| Docker | `docker compose down -v` (dev); blue/green for prod (future) |
| Config | `.env` changes are additive; remove vars to disable features |

---

## 13. Deliverables Checklist

- [ ] `openspec/changes/auth-multitenant-foundation/proposal.md` (this file)
- [ ] `openspec/changes/auth-multitenant-foundation/architecture.md` (detailed design)
- [ ] `openspec/changes/auth-multitenant-foundation/data-model.md` (ERD + migration SQL)
- [ ] `openspec/changes/auth-multitenant-foundation/api-contract.md` (OpenAPI snippets)
- [ ] `openspec/changes/auth-multitenant-foundation/test-plan.md` (IDOR, RBAC, token rotation scenarios)
- [ ] Implementation: backend modules, frontend auth screens, Docker, CI, tests
- [ ] ADRs in `docs/architecture/adrs/`

---

## 14. Skill Resolution

- `reunionai-sdd-workflow`: Loaded (spec-driven workflow)
- `reunionai-multitenant-security`: Loaded (security contract)
- Resolution: `paths-injected`

---

## 15. Proposal Question Round — RESOLVED

All questions below were answered by the product owner. Decisions are recorded here and encoded in the delta specs under `openspec/changes/auth-multitenant-foundation/specs/`.

### Q1: Super-admin vs Organization Admin Boundaries — RESOLVED

**Decision:** Self-service `register` creates an organization + its Organization Admin (scoped to the new org). The first platform Super Admin is created via a CLI bootstrap script (idempotent, config-driven).

### Q2: Membership Model — Property/Group Required? — RESOLVED

**Decision:** Property/group membership is OPTIONAL. Users may be direct organization members; `memberships.property_id` is nullable. The active tenant derives from the organization; property scope is preserved when present.

### Q3: MFA Mandatory for Which Roles? — RESOLVED

**Decision:** MFA is mandatory for admin roles (Super Admin, Organization Admin, Property Admin) and optional for all other roles in this change. Organization-level MFA policy is deferred to a later change.

### Q4: Session/Device Management Scope — RESOLVED

**Decision:** Users can list and revoke ALL their sessions across devices (`GET /users/me/sessions` + per-session revoke), Google-style.

### Q5: Rate Limiting Storage — In-Memory Acceptable for MVP? — RESOLVED

**Decision:** In-memory rate limiting for MVP; no Redis in this change. Documented migration path to Redis for multi-worker deployment.

---

**Next Step:** Proceed to the Architecture phase.
