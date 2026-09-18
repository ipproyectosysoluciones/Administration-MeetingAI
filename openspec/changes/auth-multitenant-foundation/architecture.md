# Architecture Design: auth-multitenant-foundation

**Change ID:** `auth-multitenant-foundation`
**Status:** Design
**Date:** 2025-01-15

---

## 1. Context & Decisions Summary

This document records the architectural decisions for the authentication, multi-tenancy, RBAC, and audit foundation. All decisions trace to the proposal, specs, and PRD-ReunionAI.md. Trade-offs are noted inline per openspec rules.

---

## 2. Module Layout & Dependency Graph

### 2.1 Directory Structure

```
app/
├── core/                          # Shared infrastructure (no module deps)
│   ├── config.py                  # Pydantic Settings, .env loading
│   ├── security.py                # JWT (RS256), Argon2id, token utilities
│   ├── database.py                # SQLAlchemy engine, session, declarative base
│   ├── exceptions.py              # Domain exceptions (AuthError, TenantError, ...)
│   ├── middleware/
│   │   ├── tenant_context.py      # TenantContextMiddleware, get_tenant_id() dep
│   │   ├── audit_middleware.py    # Auto-audit for mutating endpoints
│   │   ├── rate_limit.py          # In-memory rate limiter (no Redis)
│   │   └── security_headers.py    # CSP, HSTS, X-Frame-Options, Referrer-Policy
│   └── dependencies.py            # FastAPI deps: get_current_user, get_db, require_permission
├── modules/                       # Feature modules (acyclic deps only)
│   ├── auth/
│   │   ├── router.py              # POST /login, /register, /refresh, /revoke, /mfa/*
│   │   ├── service.py             # Auth business logic
│   │   ├── schemas.py             # Pydantic request/response models
│   │   ├── repository.py          # Data access for User, RefreshToken, MFADevice, Session
│   │   └── models.py              # SQLAlchemy models
│   ├── users/
│   │   ├── router.py              # CRUD /me, /users/{id}
│   │   ├── service.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   └── models.py              # User, Profile (extends core User)
│   ├── organizations/
│   │   ├── router.py              # CRUD org, properties, memberships
│   │   ├── service.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   └── models.py              # Organization, Property, Membership
│   ├── rbac/
│   │   ├── router.py              # Permissions, roles, assignments
│   │   ├── service.py             # Permission resolution, role management
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   └── models.py              # Permission, Role, RolePermission, UserRole
│   └── audit/
│       ├── router.py              # GET /audit (admin)
│       ├── service.py
│       ├── schemas.py
│       ├── repository.py
│       └── models.py              # AuditEvent
├── main.py                        # FastAPI app factory, router inclusion
└── cli/
    └── bootstrap_superadmin.py    # Idempotent Super Admin creation script
```

### 2.2 Module Dependency Graph (Acyclic)

```
core (no deps)
    ↑
    ├── auth         → depends on: core, users (models), rbac (permission check), audit (event emission)
    ├── users        → depends on: core, organizations (membership), rbac (permission check), audit
    ├── organizations → depends on: core, users (membership target), rbac, audit
    ├── rbac         → depends on: core, organizations (tenant scope), audit
    └── audit        → depends on: core (only)
```

**Critical invariant:** No module imports another module's router or service directly. Cross-module calls go through `core.dependencies` (e.g., `require_permission`) or explicit service imports that respect the DAG above. `rbac` is a leaf for permission checks; `audit` is a sink.

### 2.3 Trade-off: Service-Layer Enforcement Over RLS

**Decision:** Tenant enforcement at service/repository layer (mandatory). PostgreSQL RLS deferred to a future change as defense-in-depth.

**Rationale:**

- Service-layer enforcement is explicit, testable, portable, and works with any SQL backend.
- RLS adds operational complexity (policy maintenance, `SET LOCAL` context, migration ordering) without additional security if the application layer is correct.
- RLS can be added later without schema changes (policies reference `current_setting('app.current_tenant_id')`).

**Cost:** More boilerplate in repositories. Mitigated by a `TenantScopedRepository` base class.

---

## 3. Tenant Context Resolution

### 3.1 Resolution Chain

```
Request
  → AuthMiddleware (validates JWT, extracts user_id)
  → TenantContextMiddleware
      → calls UserRepository.get_active_membership(user_id)
      → resolves membership.organization_id as tenant_id
      → stores in request.state.tenant_id
  → Route handler
      → repositories use get_tenant_id() dependency
      → all queries filter by tenant_id
```

### 3.2 Key Implementation Points

- **`get_tenant_id()` dependency** (in `core/dependencies.py`): Single source of truth. Raises `TenantError` if no active membership.
- **`TenantScopedRepository` base class**: All tenant-scoped repositories inherit; `query()` method auto-injects `.filter(tenant_id=get_tenant_id())`.
- **Never trust client `tenant_id`**: No endpoint accepts `tenant_id` as parameter; derived solely from membership.

### 3.3 Active Membership Definition

A user may have multiple memberships. The "active" membership is:

1. Explicitly set via `POST /users/me/active-membership` (future), OR
2. The most recent membership by `created_at` where `organization.deleted_at IS NULL` AND `membership.deleted_at IS NULL`.

For MVP, rule (2) applies. The bootstrap Super Admin has a platform-level membership (`organization_id = NULL` sentinel) — handled specially in `get_tenant_id()`.

---

## 4. Authentication & Token Strategy

### 4.1 Access Tokens

- **Algorithm:** RS256 (asymmetric). Keys: `JWT_PRIVATE_KEY` (PEM), `JWT_PUBLIC_KEY` (PEM) from env.
- **TTL:** 15 minutes (`JWT_ACCESS_TTL_MINUTES=15`).
- **Claims:** `sub` (user_id), `tid` (tenant_id), `perm` (permission strings array), `iat`, `exp`, `jti`.
- **Validation:** `require_permission` dependency decodes with public key, verifies `exp`, checks `perm` claim contains required permission, re-resolves from DB for authoritative check on sensitive endpoints.

**Trade-off:** Short TTL + permission claim in token reduces DB hits for authorization but risks stale permissions. Mitigation: re-resolve on `user.role.*`, `role.permission.*`, `organization.*` mutations (audit events trigger cache invalidation — future). For MVP, permission claim is a hint; `require_permission` always re-resolves from DB.

### 4.2 Refresh Tokens

- **Storage:** `refresh_tokens` table with `token_hash` (Argon2id), `user_id`, `expires_at` (30 days), `revoked_at`, `replaced_by_token_id` (self-referential FK for rotation chain).
- **Rotation:** On `POST /auth/refresh`, verify presented token hash, check not revoked/expired, create new token, update old token's `replaced_by_token_id` and `revoked_at = now()`.
- **Reuse Detection:** If presented token has `revoked_at` set OR `replaced_by_token_id` set → revoke entire chain (recursive update all tokens in chain `revoked_at = now()`), return 401.
- **Grace Window:** 30 seconds (`REFRESH_GRACE_SECONDS=30`). If a token was replaced within grace window, allow the legitimate successor (detected by `replaced_by_token_id` pointing to a token whose `created_at` is within grace window of the presented token's `created_at`).

**Trade-off:** DB round-trip on every refresh. Acceptable for MVP scale; Redis-backed token blocklist is the migration path.

### 4.3 Password Hashing

- **Algorithm:** Argon2id via `passlib[argon2]`.
- **Parameters:** `memory_cost=65536` (64 MB), `time_cost=3`, `parallelism=4`, `hash_len=32`, `salt_len=16`.
- **Rationale:** OWASP-recommended memory-hard function; parameters tuned for ~100ms verification on modern CPU.

### 4.4 MFA (TOTP)

- **Standard:** RFC 6238, SHA-1, 30-second step, 6 digits.
- **Enrollment:** `POST /auth/mfa/setup` → returns `secret` (base32) and `otpauth://` URI for QR.
- **Verification:** `POST /auth/mfa/verify` with TOTP code → enables `mfa_enabled=True` on user.
- **Login Challenge:** MFA-enabled users receive `mfa_required: true` + `mfa_token` (short-lived JWT, 5 min) on login; must call `POST /auth/mfa/challenge` with code to get full tokens.
- **Disable:** `POST /auth/mfa/disable` requires current password + `user.mfa.manage`.
- **Mandatory for Admins:** `UserService.require_mfa_for_role()` checks if user holds Super Admin, Organization Admin, or Property Admin in current tenant → blocks login if MFA not enabled.

**Trade-off:** TOTP only (no WebAuthn/push). Simpler implementation, broader device support. WebAuthn deferred.

---

## 5. RBAC Design

### 5.1 Permission Format

`resource.action` (e.g., `meeting.create`, `minutes.approve`, `user.read`, `organization.update`).

### 5.2 Role Types

| Role | Scope | Mutability |
| ------ | ------- | ------------ |
| Super Admin | Platform (global) | Immutable, seeded |
| Organization Admin | Tenant (org) | Immutable, seeded |
| Property Admin | Tenant (org + property) | Immutable, seeded |
| President | Tenant | Immutable, seeded |
| Secretary | Tenant | Immutable, seeded |
| Board Member | Tenant | Immutable, seeded |
| Reviewer | Tenant | Immutable, seeded |
| Co-owner | Tenant | Immutable, seeded |
| Resident | Tenant | Immutable, seeded |
| Guest | Tenant | Immutable, seeded |
| Custom | Tenant (org) | CRUD by `role.*` perms |

### 5.3 Resolution Algorithm

```python
def resolve_permissions(user_id: UUID, tenant_id: UUID) -> Set[str]:
    roles = UserRoleRepository.get_roles_for_user_in_tenant(user_id, tenant_id)
    perms = set()
    for role in roles:
        perms.update(RolePermissionRepository.get_permissions_for_role(role.id))
    return perms
```

- **Union semantics:** Permissions are additive; no deny rules.
- **Tenant-scoped:** Only roles where `UserRole.organization_id == tenant_id` (or `role.organization_id == tenant_id` for custom roles).
- **Caching:** **None for MVP**. Resolution runs on every `require_permission` call. Documented migration path: Redis cache with TTL + invalidation on role/permission mutations.

### 5.4 Base Role Seeding

- **Migration `003_rbac`**: Inserts 10 base roles + permission registry + role-permission assignments.
- **Super Admin**: Platform-scoped (`organization_id IS NULL`), all permissions (`*`).
- **Organization Admin**: Tenant-scoped, permissions for org/user/role/property/membership/audit management.
- **Property Admin**: Tenant-scoped, scoped to property via membership `property_id`.

Permission matrices documented in `data-model.md` §6.

---

## 6. Audit Design

### 6.1 Event Capture Strategy

**Hybrid approach:**

- **Middleware (auto-capture):** `AuditMiddleware` wraps all mutating routes (POST/PATCH/DELETE). Extracts actor, tenant, action (from route), resource, resource_id (from path/body), ip, user_agent. Writes `AuditEvent` asynchronously via background task.
- **Explicit service calls:** For critical operations not hitting a mutating route (e.g., token refresh, MFA challenge, login success/failure), services call `AuditService.record()` directly.

**Trade-off:** Middleware guarantees coverage but captures noise (failed validations). Explicit calls are precise but require discipline. Hybrid balances both. Async write via `BackgroundTasks` avoids latency; failure to write audit does not roll back the primary operation (audit is best-effort but logged).

### 6.2 Append-Only Enforcement

- **ORM:** No `update()`/`delete()` methods on `AuditEventRepository`.
- **DB:** Migration adds `REVOKE UPDATE, DELETE ON audit_events FROM app_role;` (PostgreSQL).
- **Application:** `AuditEvent` model has no setters for mutable fields.

---

## 7. Rate Limiting (No Redis)

### 7.1 In-Memory Design

- **Store:** `dict[tuple[scope, key], deque[timestamp]]` in `core/middleware/rate_limit.py`.
- **Scopes:** `ip`, `user`.
- **Windows:** Sliding window (deque pruned on each check).
- **Limits (configurable via env):**
  - `RATE_LIMIT_LOGIN_IP=5/min`, `RATE_LIMIT_LOGIN_USER=20/min`
  - `RATE_LIMIT_REGISTER_IP=3/min`
  - `RATE_LIMIT_REFRESH_IP=30/min`, `RATE_LIMIT_REFRESH_USER=60/min`
  - `RATE_LIMIT_MFA_IP=10/min`, `RATE_LIMIT_MFA_USER=20/min`

### 7.2 Migration Path to Redis

When multi-worker deployment is needed:

1. Replace `InMemoryRateLimiter` with `RedisRateLimiter` implementing same interface.
2. Use `INCR` + `EXPIRE` for fixed windows or sorted sets for sliding windows.
3. Configuration flag `RATE_LIMIT_BACKEND=redis` switches implementation.
4. No API contract change.

---

## 8. Database & Migrations

### 8.1 Alembic Strategy

- **4 initial migrations** (see `data-model.md` for SQL):
  1. `001_init_core`: users, organizations, properties, memberships
  2. `002_auth`: refresh_tokens, mfa_devices, sessions
  3. `003_rbac`: permissions, roles, role_permissions, user_roles
  4. `004_audit`: audit_events
- **Naming:** `YYYYMMDD_HHMMSS_descriptive_name.py`
- **Non-destructive rules:**
  - No `DROP COLUMN`, `DROP TABLE`, `ALTER COLUMN ... DROP NOT NULL` in up migrations.
  - Down migrations provided and tested in CI.
  - Soft-delete columns (`deleted_at`) added in same migration as table.
- **PK Choice:** UUID v7 (`uuid_generate_v7()` via `uuid-ossp` or `gen_random_uuid()` + timestamp component) for all tables. `uuid4` acceptable if v7 extension unavailable; v7 preferred for index locality.

### 8.2 Seeding

- **Base roles/permissions:** Seeded in `003_rbac` migration (idempotent `INSERT ... ON CONFLICT DO NOTHING`).
- **Super Admin:** Created only via CLI bootstrap script (`app/cli/bootstrap_superadmin.py`), not migration. Script reads `BOOTSTRAP_SUPERADMIN_EMAIL`, `BOOTSTRAP_SUPERADMIN_PASSWORD` from env.

---

## 9. Frontend Auth Screens

### 9.1 Routes & Components

| Route | Component | Description |
| ------- | ----------- | ------------- |
| `/login` | `LoginPage` | Email/password form → on success, if MFA required redirect to `/mfa/verify` else `/dashboard` |
| `/register` | `RegisterPage` | Org name + admin user form → calls `/auth/register` → auto-login |
| `/mfa/setup` | `MfaSetupPage` | QR code + TOTP input → calls `/auth/mfa/setup` then `/auth/mfa/verify` |
| `/mfa/verify` | `MfaVerifyPage` | TOTP input during login flow → calls `/auth/mfa/challenge` |

### 9.2 API Integration

- All calls to `/api/v1/auth/*` via typed `apiClient` (generated from OpenAPI or manual).
- Access token stored in memory (React state), refresh token in `httpOnly` cookie (set by backend on login/refresh).
- `authContext` provides `user`, `permissions`, `login()`, `logout()`, `refresh()`.

---

## 10. Configuration & Docker

### 10.1 Environment Variables (`.env.example`)

```env
# Core
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/reunionai
JWT_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...
JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----\n...
JWT_ACCESS_TTL_MINUTES=15
REFRESH_TTL_DAYS=30
REFRESH_GRACE_SECONDS=30
ARGON2_MEMORY_COST=65536
ARGON2_TIME_COST=3
ARGON2_PARALLELISM=4

# Rate limiting
RATE_LIMIT_LOGIN_IP=5
RATE_LIMIT_LOGIN_USER=20
RATE_LIMIT_REGISTER_IP=3
RATE_LIMIT_REFRESH_IP=30
RATE_LIMIT_REFRESH_USER=60
RATE_LIMIT_MFA_IP=10
RATE_LIMIT_MFA_USER=20

# CORS
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:4321

# Bootstrap
BOOTSTRAP_SUPERADMIN_EMAIL=admin@reunionai.local
BOOTSTRAP_SUPERADMIN_PASSWORD=changeme

# Frontend
FRONTEND_URL=http://localhost:4321
```

### 10.2 Docker Compose

- **`docker-compose.yml`**: Production baseline (frontend, backend, postgres, nginx).
- **`docker-compose.dev.yml`**: Overrides with volumes, debug ports, `SEED_DEMO=true`.
- **Redis & Worker:** Commented out with `# TODO: Enable when justified per AGENTS.md §3.16`.

---

## 11. Security Headers & CORS

- **CSP:** `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'`
- **HSTS:** `max-age=31536000; includeSubDomains; preload` (prod only)
- **X-Frame-Options:** `DENY`
- **Referrer-Policy:** `strict-origin-when-cross-origin`
- **CORS:** Strict allowlist from `CORS_ALLOW_ORIGINS`; credentials allowed.

---

## 12. Open Decisions Resolved

| # | Decision | Trade-off Note |
| --- | ---------- | ---------------- |
| 1 | JWT RS256 15m + rotating 30d refresh, reuse detection, DB storage | DB round-trip on refresh; Redis blocklist is migration path |
| 2 | Argon2id: memory=64MB, time=3, parallelism=4 | ~100ms verify; tune if latency budget exceeded |
| 3 | TOTP only, mandatory for 3 admin roles, recovery codes not in MVP | Simpler; WebAuthn/recovery codes deferred |
| 4 | Service-layer tenant enforcement (mandatory), RLS deferred | More code now; RLS adds defense-in-depth later without schema change |
| 5 | In-memory rate limiting, documented Redis migration | Inaccurate under multi-worker; acceptable for MVP single-worker |
| 6 | 4 Alembic migrations, non-destructive, UUID v7 PKs | v7 needs extension; fallback to uuid4 documented |
| 7 | `app/modules/{auth,users,orgs,rbac,audit}/{router,service,repo,schemas,models}` + `core/` | Acyclic DAG enforced; cross-module via deps only |
| 8 | Permission union across roles in active tenant; no caching for MVP | Extra DB query per authz; cache + invalidation is documented migration |
| 9 | Hybrid audit: middleware (auto) + explicit service calls; async write | Best-effort audit; primary op never blocked by audit failure |
| 10 | 10 base roles seeded in migration 003; matrices in data-model.md | Immutable by tenants; custom roles per org |
| 11 | 4 frontend auth screens wired to `/api/v1/auth`; refresh token in httpOnly cookie | Cookie-based refresh avoids token in localStorage |
| 12 | CLI bootstrap script for first Super Admin (idempotent, env-driven) | No self-service Super Admin creation possible |

---

## 13. Risks & Mitigations (Recap)

| Risk | Mitigation |
| ------ | ------------ |
| Tenant_id propagation bugs | Centralized `get_tenant_id()`, `TenantScopedRepository` base, IDOR tests per endpoint |
| Refresh token rotation races | Grace window, chain tracking, comprehensive unit tests |
| RLS vs service-layer confusion | ADR documenting decision; service-layer primary |
| MFA UX complexity | TOTP only for MVP; clear error messages |
| Migration rollback | All migrations have `downgrade()`; tested in CI |
| Redis dependency creep | Explicit justification required in PR; commented in compose |

---

## 14. Acceptance Criteria (from Proposal §10)

All functional, security, infrastructure, and documentation criteria from proposal §10 are the definition of done for this change.
