# Test Plan: auth-multitenant-foundation

**Change ID:** `auth-multitenant-foundation`
**Status:** Design
**Date:** 2025-01-15

---

## 1. Test Strategy & Priorities

Per `reunionai-tdd-standards`, test priority order:

1. **Authorization** — Every endpoint enforces correct permissions
2. **Tenant Isolation** — Tenant A never accesses Tenant B (IDOR prevention)
3. **Domain Logic** — Token rotation, MFA flows, RBAC resolution
4. **API Contract** — Request/response schemas, error codes
5. **Persistence** — Migrations, soft deletes, constraints
6. **Integration** — Cross-module flows (register → login → RBAC → audit)
7. **Frontend** — Auth screens, token storage, redirects
8. **E2E** — Full user journeys

**Minimum per-PR validation (CI):**

```bash
lint → typecheck → unit → integration → authorization → tenant-isolation → build
```

---

## 2. Backend Test Structure (pytest)

### 2.1 Directory Layout

```
backend/
├── tests/
│   ├── conftest.py              # Fixtures: db, client, users, tenants, tokens
│   ├── unit/
│   │   ├── core/
│   │   │   ├── test_security.py         # JWT, Argon2id, token utils
│   │   │   ├── test_tenant_context.py   # get_tenant_id(), TenantScopedRepository
│   │   │   ├── test_rate_limit.py       # In-memory limiter logic
│   │   │   └── test_exceptions.py       # Domain exception mapping
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   │   ├── test_service.py      # Login, register, refresh, MFA logic
│   │   │   │   ├── test_repository.py   # RefreshToken, MFADevice, Session CRUD
│   │   │   │   └── test_token_rotation.py # Rotation, reuse detection, grace window
│   │   │   ├── users/
│   │   │   │   ├── test_service.py      # Profile, password, MFA device mgmt
│   │   │   │   └── test_repository.py   # User, Membership queries
│   │   │   ├── organizations/
│   │   │   │   ├── test_service.py      # Org, property, membership CRUD
│   │   │   │   └── test_repository.py   # Tenant-scoped queries
│   │   │   ├── rbac/
│   │   │   │   ├── test_service.py      # Permission resolution, role mgmt
│   │   │   │   ├── test_repository.py   # Role, permission, user_role queries
│   │   │   │   └── test_resolution.py   # Union semantics, tenant scoping
│   │   │   └── audit/
│   │   │       ├── test_service.py      # Event recording, query
│   │   │       └── test_repository.py   # Append-only enforcement
│   ├── integration/
│   │   ├── test_auth_flow.py            # Register → login → refresh → revoke
│   │   ├── test_mfa_flow.py             # Setup → verify → login challenge → disable
│   │   ├── test_rbac_flow.py            # Create role → assign perms → assign to user → resolve
│   │   ├── test_tenant_isolation.py     # IDOR tests (PRIORITY 2)
│   │   ├── test_audit_capture.py        # Middleware + explicit events
│   │   └── test_bootstrap.py            # CLI super-admin creation
│   ├── security/
│   │   ├── test_password_hashing.py     # Argon2id params, constant-time verify
│   │   ├── test_jwt_validation.py       # RS256, claims, expiry, key rotation
│   │   ├── test_refresh_token_security.py # Rotation, reuse detection, chain revocation
│   │   ├── test_mfa_enforcement.py      # Admin mandatory, challenge flow
│   │   ├── test_rate_limiting.py        # Per-IP, per-user limits
│   │   └── test_cors_headers.py         # CORS, CSP, HSTS, security headers
│   └── fixtures/
│       ├── users.py                     # UserFactory, SuperAdminFactory
│       ├── tenants.py                   # TenantFactory, MembershipFactory
│       ├── rbac.py                      # RoleFactory, PermissionFactory
│       └── tokens.py                    # TokenFactory (access, refresh, mfa)
```

### 2.2 Key Fixtures (conftest.py)

```python
# conftest.py
@pytest.fixture(scope="session")
def event_loop(): ...

@pytest.fixture(scope="function")
async def db_session(): ...  # Async session, rollback per test

@pytest.fixture
def tenant_a(db_session): ...  # Organization + memberships
@pytest.fixture
def tenant_b(db_session): ...  # Different organization

@pytest.fixture
def user_a(tenant_a): ...  # User in tenant_a with org_admin role
@pytest.fixture
def user_b(tenant_b): ...  # User in tenant_b with resident role
@pytest.fixture
def super_admin(): ...     # Platform super-admin (no tenant)

@pytest.fixture
def access_token(user_a): ...  # Valid JWT for user_a
@pytest.fixture
def refresh_token(user_a): ... # Valid refresh token cookie
@pytest.fixture
def mfa_token(user_a): ...     # MFA challenge token

@pytest.fixture
def auth_client(access_token): ...  # AsyncClient with Authorization header
@pytest.fixture
def unauth_client(): ...            # AsyncClient without auth
```

---

## 3. Test Suites by Category

### 3.1 Authorization Tests (Priority 1)

| Test | Description | Expected |
| ------ | ------------- | ---------- |
| `test_require_permission_denies_without_perm` | Call protected endpoint without required perm | 403 |
| `test_require_permission_allows_with_perm` | Call with user having perm via role | 200 |
| `test_require_permission_denies_unauthenticated` | Call without token | 401 |
| `test_super_admin_can_create_org` | POST `/organizations` as super-admin | 201 |
| `test_org_admin_cannot_create_org` | POST `/organizations` as org-admin | 403 |
| `test_user_cannot_access_admin_endpoints` | GET `/users` as resident | 403 |
| `test_self_endpoints_require_no_admin_perm` | GET/PATCH `/users/me` with basic perms | 200 |
| `test_role_permission_assign_requires_perm` | POST `/rbac/roles/{id}/permissions` without perm | 403 |
| `test_audit_read_requires_perm` | GET `/audit` without audit.read | 403 |

### 3.2 Tenant Isolation / IDOR Tests (Priority 2) — **BLOCKERS IN CI**

**Principle:** Every tenant-scoped endpoint must be tested with Tenant A user accessing Tenant B resource → 404.

| Endpoint | Cross-Tenant Test | Expected |
| ---------- | ------------------- | ---------- |
| `GET /users` | user_a lists users | Only tenant_a users |
| `GET /users/{id}` | user_a gets user_b | 404 |
| `PATCH /users/{id}` | user_a updates user_b | 404 |
| `DELETE /users/{id}` | user_a deletes user_b | 404 |
| `GET /organizations/me` | user_a gets org | tenant_a org |
| `PATCH /organizations/me` | user_a updates org | tenant_a org only |
| `GET /organizations/me/properties` | user_a lists properties | tenant_a only |
| `POST /organizations/me/properties` | user_a creates in tenant_b | 404 (not accessible) |
| `GET /organizations/me/memberships` | user_a lists memberships | tenant_a only |
| `POST /organizations/me/memberships` | user_a adds to tenant_b | 404 |
| `GET /rbac/roles` | user_a lists roles | tenant_a (base + custom) |
| `POST /rbac/roles` | user_a creates in tenant_b | 403 (not in tenant) |
| `GET /rbac/users/{id}/roles` | user_a assigns role to user_b | 404 |
| `GET /audit` | user_a queries audit | tenant_a events only |
| `GET /audit/{id}` | user_a gets tenant_b event | 404 |

**Test Template:**

```python
async def test_tenant_isolation_users_list(auth_client_a, user_b):
    # user_b exists in tenant_b
    response = await auth_client_a.get("/api/v1/users")
    assert response.status_code == 200
    user_ids = [u["id"] for u in response.json()["items"]]
    assert user_b.id not in user_ids  # Tenant B user not visible

async def test_tenant_isolation_user_detail_cross_tenant(auth_client_a, user_b):
    response = await auth_client_a.get(f"/api/v1/users/{user_b.id}")
    assert response.status_code == 404  # Not 403!
    assert response.json()["code"] == "USER_NOT_FOUND"
```

### 3.3 Domain Logic Tests (Priority 3)

#### Auth Module

| Test | Description |
| ------ | ------------- |
| `test_register_creates_org_user_membership` | Full registration flow |
| `test_register_rejects_duplicate_email` | 409 on existing email |
| `test_register_cannot_create_super_admin` | Role forced to org_admin |
| `test_login_returns_tokens_no_mfa` | Standard login flow |
| `test_login_returns_mfa_challenge_when_enabled` | MFA user gets mfa_token |
| `test_login_rejects_wrong_password` | 401 INVALID_CREDENTIALS |
| `test_login_rejects_inactive_user` | 403 USER_INACTIVE |
| `test_login_blocks_admin_without_mfa` | 403 MFA_REQUIRED_FOR_ROLE |
| `test_refresh_rotates_token` | New access + refresh, old revoked |
| `test_refresh_reuse_detected_revokes_chain` | Replay old token → 401 REFRESH_TOKEN_REUSE_DETECTED |
| `test_refresh_grace_window_allows_legitimate_successor` | Concurrent refresh within 30s |
| `test_refresh_expired_token_rejected` | 401 INVALID_REFRESH_TOKEN |
| `test_revoke_invalidates_refresh_token` | Subsequent refresh fails |
| `test_mfa_setup_returns_secret_and_qr` | Valid otpauth URI |
| `test_mfa_verify_enables_mfa` | mfa_enabled=True after verify |
| `test_mfa_challenge_issues_full_tokens` | Correct code → access+refresh |
| `test_mfa_disable_requires_password` | Wrong password → 400 |
| `test_mfa_disable_clears_secret` | mfa_enabled=False, secret cleared |

#### RBAC Module

| Test | Description |
| ------ | ------------- |
| `test_permission_registry_contains_all_seeded` | 35+ permissions |
| `test_base_roles_seeded_immutable` | 10 roles, is_system=True, is_deletable=False |
| `test_custom_role_creation_scoped_to_tenant` | org_id set, not visible cross-tenant |
| `test_custom_role_deletion_allowed` | Only custom roles deletable |
| `test_role_permission_assignment` | Add/remove perms works |
| `test_user_role_assignment_scoped_to_tenant` | user_roles.organization_id = tenant |
| `test_permission_resolution_union` | Two roles → union of perms |
| `test_permission_resolution_tenant_scoped` | Role in tenant_b not included for tenant_a |
| `test_super_admin_has_wildcard_permissions` | Resolves all permissions |
| `test_org_admin_permissions_match_matrix` | Exact perm set from data-model.md |

#### Organizations Module

| Test | Description |
| ------ | ------------- |
| `test_self_service_register_creates_org` | Via /auth/register |
| `test_super_admin_can_create_additional_org` | POST /organizations |
| `test_org_soft_delete_cascades_memberships` | deleted_at set on memberships |
| `test_property_crud_tenant_scoped` | All property ops filtered by tenant |
| `test_membership_property_optional` | property_id nullable |
| `test_membership_unique_per_user_org` | Duplicate → 409 |

#### Audit Module

| Test | Description |
| ------ | ------------- |
| `test_audit_event_schema_complete` | All required fields present |
| `test_audit_append_only_no_update_delete` | ORM methods absent, DB revoke |
| `test_middleware_captures_mutating_requests` | POST/PATCH/DELETE → audit event |
| `test_explicit_capture_login_logout` | Login/logout events recorded |
| `test_audit_query_tenant_scoped` | Only tenant events returned |
| `test_audit_filters_work` | action, resource, date_from, actor |
| `test_audit_pagination` | page, page_size, total, pages |

---

### 3.4 API Contract Tests (Priority 4)

- Request validation (Pydantic) → 422 VALIDATION_ERROR
- Response shape matches api-contract.md
- Error codes match reference table
- Pagination format consistent
- UUID format lowercase with hyphens
- Timestamps ISO 8601 UTC

---

### 3.5 Persistence Tests (Priority 5)

| Test | Description |
| ------ | ------------- |
| `test_migrations_apply_cleanly` | `alembic upgrade head` on empty DB |
| `test_migrations_rollback` | `alembic downgrade -1` each migration |
| `test_soft_delete_preserves_fk` | User soft-deleted → audit events intact |
| `test_unique_constraints` | Email, slug, role names, memberships |
| `test_cascade_deletes` | Org delete → properties, memberships |
| `test_refresh_token_chain_integrity` | replaced_by_token_id FK works |
| `test_uuid_v7_or_fallback` | PKs are UUIDs, v7 if available |

---

### 3.6 Integration Tests (Priority 6)

| Test | Flow |
| ------ | ------ |
| `test_full_registration_to_dashboard` | Register → login → /users/me → permissions |
| `test_mfa_full_lifecycle` | Setup → verify → login challenge → disable |
| `test_rbac_full_lifecycle` | Create role → assign perms → assign to user → resolve |
| `test_org_admin_manages_members` | Invite → assign role → update property → remove |
| `test_audit_captures_all_critical_ops` | Login, user CRUD, role changes, org changes |

---

### 3.7 Security Tests (Dedicated Suite)

| Test | Description |
| ------ | ------------- |
| `test_argon2id_parameters` | memory=65536, time=3, parallelism=4 |
| `test_password_never_in_logs` | No plaintext in test logs |
| `test_jwt_rs256_verification` | Public key verifies, tampered fails |
| `test_jwt_claims_present` | sub, tid, perm, iat, exp, jti |
| `test_jwt_expired_rejected` | 401 after 15 min |
| `test_refresh_token_hashed_storage` | Only hash in DB, never plaintext |
| `test_refresh_token_chain_revocation` | Reuse → all chain revoked |
| `test_mfa_totp_rfc6238` | SHA-1, 30s step, 6 digits |
| `test_admin_mfa_mandatory` | Super Admin, Org Admin, Property Admin |
| `test_rate_limit_ip` | 5 login/min/IP → 429 |
| `test_rate_limit_user` | 20 login/min/user → 429 |
| `test_cors_strict_allowlist` | Origin not in list → blocked |
| `test_security_headers_present` | CSP, HSTS, X-Frame-Options, Referrer-Policy |

---

## 4. Frontend Test Structure (vitest + Playwright)

### 4.1 Unit/Component Tests (vitest)

```
frontend/
├── tests/
│   ├── unit/
│   │   ├── components/
│   │   │   ├── LoginForm.test.tsx
│   │   │   ├── RegisterForm.test.tsx
│   │   │   ├── MfaSetup.test.tsx
│   │   │   └── MfaVerify.test.tsx
│   │   ├── hooks/
│   │   │   └── useAuth.test.ts
│   │   └── utils/
│   │       └── apiClient.test.ts
│   ├── e2e/
│   │   ├── auth-flow.spec.ts      # Playwright: register → login → dashboard
│   │   ├── mfa-flow.spec.ts       # Playwright: setup → verify → login challenge
│   │   └── session-mgmt.spec.ts   # Playwright: list/revoke sessions
```

**Key Component Tests:**

- `LoginForm`: Submits to `/api/v1/auth/login`, handles MFA redirect, shows errors
- `RegisterForm`: Validates org+user fields, submits to `/api/v1/auth/register`, auto-login
- `MfaSetup`: Renders QR (via `qrcode.react`), submits code to `/auth/mfa/verify`
- `MfaVerify`: Submits code to `/auth/mfa/challenge`, redirects on success
- `useAuth`: Manages access token (memory), refresh token (cookie), auto-refresh

### 4.2 E2E Tests (Playwright)

| Test | Flow |
| ------ | ------ |
| `auth-flow.spec.ts` | Visit `/register` → fill form → redirect to `/dashboard` → verify user menu |
| `mfa-flow.spec.ts` | Login → `/mfa/setup` → scan QR → enter code → verify → logout → login with MFA |
| `session-mgmt.spec.ts` | Login on 2 browsers → list sessions → revoke one → verify other stays |

---

## 5. Test Commands

### 5.1 Backend (pytest)

```bash
# All tests
cd backend && pytest -v

# By category
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/security/ -v

# Specific suites
pytest tests/integration/test_tenant_isolation.py -v  # IDOR tests
pytest tests/security/ -v                             # Security tests

# With coverage
pytest --cov=app --cov-report=term-missing --cov-fail-under=80

# Parallel
pytest -n auto
```

### 5.2 Frontend (vitest + Playwright)

```bash
# Unit tests
cd frontend && npm run test          # vitest

# E2E tests
cd frontend && npm run test:e2e      # playwright

# All frontend tests
cd frontend && npm run test:all
```

### 5.3 CI Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - name: Install deps
        run: pip install -e ".[dev]"
      - name: Start postgres
        run: docker compose -f docker-compose.ci.yml up -d postgres
      - name: Run migrations
        run: alembic upgrade head
      - name: Lint
        run: ruff check .
      - name: Type check
        run: mypy app
      - name: Unit tests
        run: pytest tests/unit/ -v
      - name: Integration tests
        run: pytest tests/integration/ -v
      - name: Authorization tests
        run: pytest tests/ -k "authorization" -v
      - name: Tenant isolation tests
        run: pytest tests/integration/test_tenant_isolation.py -v
      - name: Security tests
        run: pytest tests/security/ -v
      - name: Build
        run: docker build -t reunionai-backend .

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node
        uses: actions/setup-node@v4
        with: { node-version: '20' }
      - name: Install deps
        run: npm ci
      - name: Lint
        run: npm run lint
      - name: Type check
        run: npm run typecheck
      - name: Unit tests
        run: npm run test
      - name: E2E tests
        run: npm run test:e2e
      - name: Build
        run: npm run build
```

---

## 6. Test Data & Factories

### 6.1 User Factory

```python
# tests/fixtures/users.py
class UserFactory:
    @staticmethod
    async def create(db, email, password, tenant=None, roles=None, mfa_enabled=False, is_super_admin=False):
        # Hash password, create user, membership, user_roles
        ...

    @staticmethod
    def super_admin(db): ...
    @staticmethod
    def org_admin(db, tenant): ...
    @staticmethod
    def resident(db, tenant): ...
```

### 6.2 Token Factory

```python
# tests/fixtures/tokens.py
class TokenFactory:
    @staticmethod
    def access_token(user, tenant_id, permissions, private_key): ...
    @staticmethod
    def refresh_token(user, db): ...  # Creates DB record, returns plaintext
    @staticmethod
    def mfa_token(user): ...          # 5-min TTL
```

---

## 7. Coverage Targets

| Area | Target |
| ------ | -------- |
| Authorization logic | 100% |
| Tenant isolation (IDOR) | 100% (every endpoint) |
| Token rotation/reuse | 100% |
| MFA flows | 100% |
| RBAC resolution | 100% |
| Audit capture | 90% |
| General domain logic | 85% |
| Overall | 80% minimum |

---

## 8. Test Execution Gates

| Gate | Command | Must Pass |
| ------ | --------- | ----------- |
| Pre-commit | `ruff check . && mypy app && pytest tests/unit/ -x` | Yes |
| PR Validation | Full CI pipeline | Yes |
| Merge to develop | All CI green + coverage ≥ 80% | Yes |
| Release candidate | All tests + manual security review | Yes |

---

## 9. Regression Prevention

- **IDOR tests:** Generated parametrically for every tenant-scoped endpoint. Adding new endpoint → add IDOR test.
- **Permission matrix tests:** Base role permissions verified against data-model.md matrices.
- **Token rotation:** Property-based tests for race conditions (hypothesis).
- **Migrations:** `alembic downgrade base && alembic upgrade head` in CI on every PR.

---

## 10. Future Test Extensions

- **Load testing:** Locust scripts for auth endpoints (post-MVP)
- **Chaos testing:** Network partitions during refresh rotation
- **Penetration testing:** OWASP Top 10 automated scans (CI integration)
- **Accessibility:** axe-core in Playwright for auth screens
