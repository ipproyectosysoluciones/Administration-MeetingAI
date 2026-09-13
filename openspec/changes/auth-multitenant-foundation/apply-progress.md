# Apply Progress: auth-multitenant-foundation

**Change:** `auth-multitenant-foundation`
**Delivery strategy:** `ask-on-risk` → resolved by orchestrator to chained PRs (`feature-branch-chain`), 6 PRs.
**This attempt:** PR-1, work-unit slice A — **Phase 0 (scaffolding & tooling) only**.

---

## Status guard resolution

The Native SDD Status Engine reported `applyState: blocked` with reason **"design.md is missing."**
This is a filename-convention mismatch, not a substantive gap: the design content is fully present in
`architecture.md` (19 KB), `data-model.md` (25 KB), `api-contract.md` (23 KB), `test-plan.md`, and
`proposal.md` (the design phase emitted these instead of a single `design.md`). The orchestrator
explicitly directed use of `architecture.md` §2/§8/§10 and `data-model.md` §2 as design inputs.
**No substantive design deficiency exists** — proceeding under orchestrator direction.

`actionContext`: `repo-local`, `allowedEditRoots` = single workspace root, no warnings. No blockers.

## Review workload gate

`tasks.md` forecast: **400-line budget risk = High**, **Chained PRs recommended = Yes**,
**Decision needed = Yes**. Decision RESOLVED by orchestrator: chained PRs, feature-branch-chain,
6 PRs mapping to tasks.md's PR split. The full PR-1 (Phases 0–1) is ~1,100 lines and does **not** fit
the 400-line budget; this attempt delivers the cohesive Phase 0 unit (~400 hand-written lines) and
stops at the Phase 0/Phase 1 boundary.

## Completed tasks (this slice)

- [x] **TASK-001** — backend FastAPI modular layout (`app/main.py`, `app/core/config.py`, `app/modules/{auth,users,organizations,rbac,audit}`), settings via env, `/health` endpoint.
- [x] **TASK-002** — `pyproject.toml` (pytest + ruff + mypy, incl. pydantic mypy plugin), example test passes.
- [x] **TASK-003** — frontend Astro + React + TS + Tailwind scaffold, vitest config, smoke test.
- [x] **TASK-004** — `.env.example` matching `architecture.md` §10.1 (all keys).

`tasks.md` checkboxes updated to `- [x]` for TASK-001..004.

## Files changed (this slice)

Backend (`apps/backend/`):

- `pyproject.toml` — project metadata, deps, pytest/ruff/mypy config
- `app/__init__.py`, `app/main.py`, `app/core/__init__.py`, `app/core/config.py`
- `app/modules/{__init__,auth,users,organizations,rbac,audit}/__init__.py`
- `tests/conftest.py`, `tests/test_health.py`, `tests/test_config.py`

Frontend (`apps/frontend/`):

- `package.json`, `package-lock.json` (auto-generated), `astro.config.mjs`, `tsconfig.json`,
  `tailwind.config.mjs`, `vitest.config.ts`, `.gitignore`
- `src/env.d.ts`, `src/pages/index.astro`, `src/components/SmokeBadge.tsx`,
  `src/components/__tests__/smoke.test.tsx`

Root:

- `.env.example`

Docs (apply artifact):

- `openspec/changes/auth-multitenant-foundation/tasks.md` (checkbox updates)
- `openspec/changes/auth-multitenant-foundation/apply-progress.md` (this file)

## TDD cycle evidence (strict)

| Task | RED | GREEN | Runner |
| --- | --- | --- | --- |
| TASK-001 settings/health | `ModuleNotFoundError: No module named 'app'` | `4 passed` | `pytest` |
| TASK-002 tooling | (same suite green; ruff `All checks passed`, mypy `Success: no issues found in 13 source files`) | — | ruff + mypy |
| TASK-003 vitest smoke | `Failed to resolve import "../SmokeBadge"` | `1 passed` | `vitest run` |
| TASK-004 settings load | covered by `test_config.py` (defaults + env override) | `2 passed` | pytest |

Commands:

- `cd apps/backend && .venv/bin/python -m pytest -q` → `4 passed, 2 warnings`
- `cd apps/backend && .venv/bin/ruff check app tests` → `All checks passed!`
- `cd apps/backend && .venv/bin/ruff format --check app tests` → `13 files already formatted`
- `cd apps/backend && .venv/bin/mypy app tests` → `Success: no issues found in 13 source files`
- `cd apps/frontend && npx vitest run` → `1 passed (1)`
- `cd apps/frontend && npx astro build` → `1 page(s) built` (caught named-vs-default export bug, fixed)

## Deviations from design

1. **`design.md` naming**: design content lives in `architecture.md`/`data-model.md`/`api-contract.md`
   (see status guard resolution). No content deviation.
2. **`.env.example` placement**: written at repo root (docker-compose context + both backend/frontend
   vars) per `architecture.md` §10.1. `Settings.env_file` remains `.env` (relative); services inject
   env vars in docker-compose.
3. **mypy requires `plugins = ["pydantic.mypy"]`** to recognize pydantic-settings `_env_file` kwarg.
4. `bootstrap_superadmin_password` default `changeme` retained to match §10.1 exactly (real value
   always supplied via env).

## Remaining tasks (next slices — NOT in this attempt)

- [ ] **TASK-010** `chore: set up Alembic with async engine` — non-destructive rules, rollback tested.
- [ ] **TASK-011** `feat: migration 001 init_core (tenants/organizations/properties/users/memberships)`
- [ ] **TASK-012** `feat: migration 002 auth (sessions/refresh_tokens/mfa)`
- [ ] **TASK-013** `feat: migration 003 rbac (roles/permissions/role_permissions/user_roles)`
- [ ] **TASK-014** `feat: migration 004 audit (audit_events append-only)`
- [ ] TASK-020 … TASK-113 (Phases 2–11 per `tasks.md`)

## Workload / PR boundary

- PR-1 = Phases 0–1 (per `tasks.md`). This attempt = **Phase 0 only** (~400 hand-written lines,
  excluding auto-generated `package-lock.json`). Phase 1 (migrations, ~540+ lines) is the next slice.
- Chained PR strategy: `feature-branch-chain`. Tracker `feature/auth-multitenant-foundation`,
  child `feature/auth-multitenant-foundation-pr1`.
- No `size:exception` claimed; the boundary is an honest cohesive split (Phase 0 is self-contained).

---

## PR-1, work-unit slice B — Phase 1 (database & migrations): TASK-010..014

**Branch:** `feature/auth-multitenant-foundation-pr1` (continued from slice A).

### Status guard

Same resolved guard as slice A: the design content lives in `architecture.md` + `data-model.md`
(+ `api-contract.md`/`test-plan.md`) rather than a single `design.md`, so the "design.md missing"
blocker is a filename mismatch, not a gap. `actionContext` is `repo-local` with the single
workspace root as the sole edit root and no warnings. Proceeding under orchestrator direction.

### Completed tasks (this slice)

- [x] **TASK-010** — Alembic async setup: `alembic.ini`, `alembic/env.py` (async engine via
  `run_sync`), `alembic/script.py.mako`, and `app/core/database.py` (async engine + session +
  `DeclarativeBase` with a naming convention). Non-destructive; upgrade/downgrade smoke-tested.
- [x] **TASK-011** — migration `0001_init_core`: users/organizations/properties/memberships.
- [x] **TASK-012** — migration `0002_auth`: refresh_tokens/mfa_devices/sessions (rotation chain FK).
- [x] **TASK-013** — migration `0003_rbac`: permissions/roles/role_permissions/user_roles + seed.
- [x] **TASK-014** — migration `0004_audit`: audit_events + append-only trigger.

`tasks.md` checkboxes updated to `- [x]` for TASK-010..014.

### Files changed (this slice)

Backend (`apps/backend/`):

- `pyproject.toml` — added `sqlalchemy[asyncio]`, `asyncpg`, `greenlet` (runtime), `alembic` (dev),
  and `[tool.ruff.lint.isort] known-first-party = ["app"]` (the `alembic/` dir name would otherwise
  be misclassified by isort).
- `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako` — Alembic async scaffolding.
- `alembic/versions/0001_init_core.py` .. `0004_audit.py` — the four migrations.
- `app/core/database.py` — async engine/session/Base + naming convention.
- `tests/conftest.py` — `alembic_cfg` + `migrated_engine` fixtures (targets a Docker PostgreSQL).
- `tests/test_migrations.py` — smoke + introspection + append-only tests.

Docs (apply artifacts):

- `openspec/changes/auth-multitenant-foundation/tasks.md` (checkbox updates)
- `openspec/changes/auth-multitenant-foundation/apply-progress.md` (this file)

### TDD cycle evidence (strict)

Runner: `cd apps/backend && .venv/bin/python -m pytest` against a Docker PostgreSQL
(`postgres:16-alpine`, `postgresql+asyncpg://reunionai:reunionai@localhost:5433/reunionai`).

| Task | RED | GREEN | Runner |
| --- | --- | --- | --- |
| 010 smoke | `AssertionError: {'alembic_version'} == set()` | `test_migrations_upgrade_downgrade_smoke PASSED` | pytest |
| 011 schema absent | `sqlalchemy.exc.NoSuchTableError` (tables not yet created) | `test_core_tenant_columns_and_fks PASSED` | pytest |
| 012 chain FK | `NoSuchTableError: refresh_tokens` | `test_refresh_token_chain_self_fk PASSED` | pytest |
| 013 seed broken | `INSERT has more target columns than expressions` (missing `is_system`) | `test_rbac_constraints_and_seed PASSED` | `alembic upgrade` + pytest |
| 014 append-only | (empty schema, no trigger) | `test_audit_schema_and_append_only PASSED` | pytest |

Commands (final green):

- `alembic -x db_url=... upgrade head` → `Running upgrade 0001→0002→0003→0004` (clean)
- `.venv/bin/python -m pytest -q` → `9 passed` (2 Phase-0 + 5 migration + 2 config)
- `.venv/bin/ruff check app/ alembic/ tests/` → `All checks passed!`
- `.venv/bin/mypy app alembic tests` → `Success: no issues found in 20 source files`

### Deviations from design

1. **"tenants" in TASK-011 title**: there is **no** separate `tenants` table. `data-model.md` §2.1
   defines migration 001 as `users/organizations/properties/memberships`, and `organizations.id`
   **is** the tenant root (`tenant_id`/`organization_id` FKs reference `organizations.id`).
2. **Append-only via DB trigger** (`trg_audit_events_append_only`, BEFORE UPDATE OR DELETE),
   instead of `data-model.md` §2.4's `REVOKE UPDATE, DELETE` (which needs an app role that does not
   exist until the infra slice). The trigger is role-independent and testable; a future `REVOKE`
   can coexist with it.
3. **Test backend = PostgreSQL** (not SQLite): the schema uses `INET`, `JSONB`, `TIMESTAMPTZ`,
   `gen_random_uuid()`, and partial indexes, which SQLite does not support. Documented choice per
   the task instruction.
4. **Extensions** (`pgcrypto`, `uuid-ossp`) are created `IF NOT EXISTS` but **not** dropped on
   downgrade (cluster-level shared objects; dropping could affect unrelated databases).
5. **`alembic/` directory naming** collides with the installed `alembic` package for ruff's isort;
   resolved via `known-first-party = ["app"]` (no real import shadowing — verified `alembic.__file__`
   resolves to site-packages).

### Remaining tasks (next slices — NOT this attempt)

- [ ] TASK-020 password hashing service (Argon2id)
- [ ] TASK-021 JWT service RS256
- [ ] TASK-022 in-memory rate limiter
- [ ] TASK-030 tenant-context dependency
- [ ] TASK-031 require_permission dependency
- [ ] TASK-040..046 auth module (register/login/refresh/revoke/MFA/sessions/mandatory-MFA)
- [ ] TASK-050 users CRUD + profile + password change
- [ ] TASK-060 organizations + properties CRUD
- [ ] TASK-070 permission registry + base role seeding
- [ ] TASK-080 audit service + admin query endpoint
- [ ] TASK-090 cross-tenant isolation suite
- [ ] TASK-100 frontend auth screens
- [ ] TASK-110..113 docker, CI, bootstrap CLI, docs

### Workload / PR boundary

- **Actual changed lines (slice B): ~1,045** across migrations/infra/tests (plus `pyproject.toml`
  +7 and `tests/conftest.py` +35). This **exceeds the 400-line budget ~2.5×**.
- **Why it cannot split cleanly:** migrations 001→004 form a hard dependency chain (004's audit FKs
  reference 001's tables; 003's seed needs 001+002), and 003's seed is atomic data
  (34 permissions + 10 roles + their role→permission mappings).
- **Recommendation:** `size:exception` for the migration slice — per the chained-PR guidance,
  "migration diff cannot split cleanly → ask maintainer for `size:exception`". ~450 of those lines
  are declarative DDL + seed data (low cognitive load), not logic. If an exception is unacceptable,
  the next-best split is `001+002` (~408 lines) vs `003+004` (~368 lines) at the 002/003 boundary.
- **No `size:exception` is inferred** (it requires explicit maintainer acceptance); this is reported,
  not claimed.

---

## PR-2, work-unit slice — Phases 2–3 (security primitives + tenant context): TASK-020..031

**Branch:** `feature/auth-multitenant-foundation-pr2` (created from pr1 per feature-branch-chain).

### Status guard

Same resolved guard as prior slices: the "design.md missing" blocker is a filename mismatch —
design content lives in `architecture.md`/`data-model.md`/`api-contract.md`/`test-plan.md`,
referenced explicitly by the orchestrator (§3/§4/§5/§7, api-contract §1, test-plan). No
substantive design gap. `actionContext` is `repo-local`, single workspace root, no warnings.

### Completed tasks (this slice)

- [x] **TASK-020** — `PasswordHasher` (Argon2id) in `core/security.py`.
- [x] **TASK-021** — `JWTService` (RS256, 15-min) in `core/security.py` + `core/exceptions.py`.
- [x] **TASK-022** — `InMemoryRateLimiter` (sliding window) in `core/middleware/rate_limit.py`.
- [x] **TASK-030** — `Membership` + `resolve_active_membership` (resolution chain) in `core/dependencies.py`.
- [x] **TASK-031** — `Role`/`resolve_permissions`/`AuthContext`/`require_permission` (401 vs 403) in `core/dependencies.py`.

`tasks.md` checkboxes updated to `- [x]` for TASK-020..031.

### Files changed (this slice)

Backend (`apps/backend/`):

- `app/core/security.py` — `PasswordHasher` (Argon2id) + `JWTService` (RS256).
- `app/core/exceptions.py` — token/auth domain errors (`InvalidTokenError`, `ExpiredTokenError`,
  `AuthenticationError`, `AuthorizationError`, `TenantResolutionError`, `TokenError`, `SecurityError`).
- `app/core/dependencies.py` — `Membership`, `resolve_active_membership`, `Role`,
  `resolve_permissions`, `AuthContext`, `AuthorizationResolver` protocol, `require_permission`.
- `app/core/middleware/__init__.py`, `app/core/middleware/rate_limit.py` — in-memory limiter.
- `pyproject.toml` — deps `argon2-cffi`, `PyJWT`, `cryptography`.
- `tests/conftest.py` — `generate_rsa_keypair` + `rsa_keys`/`rsa_keys_other` session fixtures.
- `tests/unit/core/test_security.py` (TASK-020/021), `test_rate_limit.py` (022),
  `test_tenant_context.py` (030), `test_require_permission.py` (031).

### TDD cycle evidence (strict)

Runner: `cd apps/backend && .venv/bin/python -m pytest`.

| Task | RED | GREEN | Runner |
| --- | --- | --- | --- |
| 020 | `ModuleNotFoundError: No module named 'app.core.security'` | `8 passed` | pytest |
| 021 | `ModuleNotFoundError: app.core.exceptions` / `no attribute JWTService` | `15 passed` | pytest |
| 022 | `import-not-found: app.core.middleware.rate_limit` | `5 passed` | pytest |
| 030 | `import-not-found: app.core.dependencies` | `6 passed` | pytest |
| 031 | `attr-defined: no AuthContext` | `8 passed` (43 total full suite) | pytest |

Commands (final green):

- `.venv/bin/python -m pytest -q` → `43 passed` (incl. Phase 0/1 migration tests against Docker postgres).
- `.venv/bin/ruff check app/ tests/` → `All checks passed!`
- `.venv/bin/ruff format --check app/ tests/` → `24 files already formatted`
- `.venv/bin/mypy app tests` → `Success: no issues found in 24 source files`

### Deviations from design

1. **`argon2-cffi` instead of `passlib[argon2]`**: `architecture.md` §4.3 says "passlib[argon2]", but
   passlib 1.7.4 is unmaintained since 2020 and its `argon2` handler is broken with modern
   `argon2-cffi` (>=21.3). `argon2-cffi`'s `PasswordHasher` is Argon2id by default with params
   matching §4.3 exactly (memory=65536, time=3, parallelism=4, hash_len=32, salt_len=16). Chosen per
   Correctness > Security priority (AGENTS.md §13); documented in the `PasswordHasher` docstring.
2. **`get_tenant_id` home**: §2.1 lists `get_tenant_id()` under `core/middleware/tenant_context.py`
   but §3.2 places it in `core/dependencies.py`. Resolution primitives live in `core/dependencies.py`
   (matching §3.2 + §2.2 "cross-module calls go through core.dependencies"). The middleware that
   populates `request.state.tenant_id` (§3.1) is a route-layer concern deferred to PR-3+.
3. **Model boundary documented, not implemented**: the DB-backed `AuthorizationResolver` (real
   `memberships`/`user_roles`/`role_permissions` queries) is deferred to the users/rbac repositories
   (PR-4/5); this slice ships the pure resolution functions + a `Protocol` seam, tested with
   in-memory fakes (`FakeResolver`/`NoMembershipResolver`) — a "lightweight fake where the contract
   allows" per the slice instruction. The ORM models are intentionally not created here to keep the
   PR boundary clean.
4. **`require_permission` re-resolves, never trusts `perm` claim** (§4.1): the JWT `perm` is a hint;
   authorization always comes from the resolver's union.

### Workload / PR boundary

- **Actual changed lines: 902 insertions, 0 deletions** (11 files). **~2.25× the 400-line budget.**
- **Honesty check:** no padding, no skipped tests — each task is a cohesive unit with real tests.
- **Natural split (already committed discretely):**
  - **TASK-020..022** = security primitives + rate limiter (`security.py` + `exceptions.py` +
    `middleware/rate_limit.py` + `security`/`rate_limit` tests + `pyproject` + `conftest`) ≈ 496 lines.
  - **TASK-030..031** = tenant context + require_permission (`dependencies.py` +
    `tenant_context`/`require_permission` tests) ≈ 406 lines.
  - Each per-task commit is individually ≤ ~283 lines; the parent's "TASK-020..022 vs TASK-030..031"
    split maps cleanly to two reviewable PRs if the 400-line budget is enforced strictly.
- **No `size:exception` claimed** (requires explicit maintainer acceptance). This is reported, not
  inferred — the orchestrator/maintainer should decide whether to (a) accept 902 lines as one PR-2,
  or (b) split into PR-2a (020..022) and PR-2b (030..031).

### Remaining tasks (next slices — NOT in this attempt)

- [ ] TASK-040..046 auth module (register/login/refresh/revoke/MFA/sessions/mandatory-MFA)
- [ ] TASK-050 users CRUD + profile + password change
- [ ] TASK-060 organizations + properties CRUD
- [ ] TASK-070 permission registry + base role seeding
- [ ] TASK-080 audit service + admin query endpoint
- [ ] TASK-090 cross-tenant isolation suite
- [ ] TASK-100 frontend auth screens
- [ ] TASK-110..113 docker, CI, bootstrap CLI, docs

---

## PR-3, work-unit slice A (PR-3a) — Phase 4 auth endpoints: TASK-040..043

**Branch:** `feature/auth-multitenant-foundation-pr3a` (from pr2b, feature-branch-chain).

### Status guard

Same resolved guard as prior slices: the "design.md missing" blocker is a filename mismatch —
design content lives in `architecture.md`/`api-contract.md`/`data-model.md`/`test-plan.md`, referenced
explicitly by the orchestrator (§2-§4/§8.2, api-contract §2.1-2.4, data-model §4). No substantive design
gap. `actionContext` is `repo-local`, single workspace root, no warnings.

### Completed tasks (this slice)

- [x] **TASK-040** — `POST /auth/register`: creates organization (tenant root) + org-admin user +
  membership + `org_admin` user_role, issues tokens. Tests: happy path, tenant bootstrapped, duplicate
  409, org-admin forced (no super-admin), 422.
- [x] **TASK-041** — `POST /auth/login`: Argon2id verify, issues RS256 access + rotating refresh, MFA
  hook (`mfa_required` when `mfa_enabled`), audit event. Tests: happy path, bad password 401, inactive
  403, MFA-required, audit written.
- [x] **TASK-042** — `POST /auth/refresh`: rotation + reuse detection → whole chain revoked (§4.2);
  grace window. Tests: rotation, reuse → sibling revoked (401), grace window, expiry.
- [x] **TASK-043** — `POST /auth/revoke` + logout: revokes current refresh token, audit event. Tests:
  revoke → refresh fails, requires auth, audit written.

`tasks.md` checkboxes updated to `- [x]` for TASK-040..043.

### Key finding: no ORM models existed before this slice

Phase 1 (PR-1) produced only Alembic migrations (raw DDL), **not** SQLAlchemy ORM models (PR-2's
apply-progress documented "The ORM models are intentionally not created here"). register/login/refresh/
revoke cannot run without mapped models, so this slice necessarily introduced the models the repos wire
to — users/organizations/properties/memberships/refresh_tokens/sessions/permissions/roles/
role_permissions/user_roles/audit_events — plus the DB-backed `DBAuthorizationResolver`. This is a hidden
prerequisite (~420 lines across 7 model files + resolver) that landed in PR-3a because no earlier slice
created it.

### Files changed (this slice)

Backend (`apps/backend/`):

- `app/modules/{users,organizations,audit,rbac,auth}/**` — `users/models.py` (User),
  `organizations/models.py` (Organization, Property, Membership), `auth/models.py` (RefreshToken,
  Session), `rbac/models.py` (Permission, Role, RolePermission, UserRole), `audit/models.py` (AuditEvent).
- `app/modules/rbac/resolver.py` — `resolve_auth_context` + `DBAuthorizationResolver` (real DB-backed
  `AuthorizationResolver`, reuses `resolve_active_membership`/`resolve_permissions`).
- `app/modules/auth/{schemas,service,router}.py` — request/response models, `AuthService`, the 4 routes.
- `app/core/exceptions.py` — added `APIError` (status + machine-readable `code`).
- `app/core/dependencies.py` — `get_db`, `require_auth`, `_resolve_authenticated` (shared by deps).
- `app/main.py` — `create_app(settings, session_factory)` injectable, wires state + `APIError` handler.
- `tests/integration/{,auth}/__init__.py`, `tests/integration/auth/{conftest,test_register,test_login,
  test_refresh,test_revoke}.py`.

Docs:

- `openspec/changes/auth-multitenant-foundation/tasks.md` (checkbox updates)
- `openspec/changes/auth-multitenant-foundation/apply-progress.md` (this file)

### TDD cycle evidence (strict)

Runner: `cd apps/backend && .venv/bin/python -m pytest` against Docker PostgreSQL
(`reunionai-test-pg`, `postgresql+asyncpg://reunionai:reunionai@localhost:5433/reunionai`).

Register/login/refresh/revoke share one `AuthService`/router module, so the RED phase concentrated in the
module scaffolding (TASK-040); later tasks verified GREEN-first, and TASK-042's reuse test caught a real
bug (genuine RED→GREEN).

| Task | RED | GREEN | Runner |
| --- | --- | --- | --- |
| 040 register | `create_app() unexpected kwarg settings/session_factory` + `ModuleNotFoundError` for models | `5 passed` | pytest |
| 041 login | (endpoint scaffolded in 040 commit) | `5 passed` | pytest |
| 042 refresh | reuse test failed: sibling `assert 200 == 401` (chain revocation wasn't committed) | `4 passed` after fix | pytest |
| 043 revoke | (endpoint scaffolded in 040 commit) | `3 passed` | pytest |

Final commands (green):

- `.venv/bin/python -m pytest -q` → `60 passed` (43 prior + 5 register + 5 login + 4 refresh + 3 revoke)
- `.venv/bin/ruff check app/ tests/ alembic/` → `All checks passed!`
- `.venv/bin/ruff format --check app/ tests/ alembic/` → `45 files already formatted`
- `.venv/bin/mypy app tests alembic` → `Success: no issues found in 45 source files`

### Deviations from design

1. **Refresh token `token_hash` = SHA-256, not Argon2id.** architecture §4.2 labels the stored digest
   "Argon2id", but a salted, non-deterministic Argon2id hash cannot serve as a lookup key on
   `ux_refresh_tokens_token_hash` (unique). A SHA-256 digest of a 256-bit opaque token is the correct
   lookup-able form (the token is high-entropy, unlike a password). Documented in `auth/models.py`.
2. **Revoke uses `require_auth()` (self-service), not `require_permission("auth.revoke")`.** The
   `auth.revoke` permission is absent from every base role matrix (including `org_admin`), so gating on
   it would make logout impossible for all registered users. Logout is inherently self-scoped (only the
   caller's own cookie token is revocable) — authentication is sufficient.
3. **ORM models omit `server_default`** (use Python-side `default=` only). Alembic owns the DDL;
   hand-written migrations already carry the `server_default`s. Python defaults keep ids/timestamps
   available without a refresh round-trip.
4. **`audit_events.metadata` mapped to `metadata_json`** — the column name `metadata` collides with
   `DeclarativeBase.metadata`.
5. **Refresh per-user rate limit deferred** — refresh rate-limiting is IP-only in this slice (the per-user
   key requires decoding the refresh token first); login/register use IP + user limits per §7.1.
6. **Refresh grace-window semantics**: within `REFRESH_GRACE_SECONDS` of a rotation, a replay is treated
   as a legitimate concurrent refresh and the live leaf is rotated (not revoked); outside the window the
   chain is revoked and 401 `REFRESH_TOKEN_REUSE_DETECTED` returned.

### Workload / PR boundary

- **Actual changed lines: 1,552 insertions / 22 deletions (~1,574 lines)** — **~3.9× the 400-line budget.**
- **Why it cannot split cleanly:** the ORM models + resolver (~420 lines) are a hard prerequisite for any
  auth endpoint and belong to no earlier committed slice (Phase 1 shipped migrations only). The four
  endpoints share one `AuthService` (340 lines) + router and are the orchestrator's explicit PR-3a unit.
  No cohesive sub-split brings the slice under 400 lines without leaving register/login/refresh/revoke
  half-broken.
- **No `size:exception` inferred** (requires explicit maintainer acceptance). This is reported, not
  claimed. Per-task commits are already discrete (34d4f6c register, 5dc8e1c login, e686101 refresh,
  e2f774e revoke, af6f2c8 style) — each ≤ ~460 lines if a strict split is required elsewhere.

### Remaining tasks (next slices — NOT in this attempt)

- [ ] TASK-044 MFA TOTP setup/verify/disable/recovery codes (`/auth/mfa/*`)
- [ ] TASK-045 session management GET/DELETE `/users/me/sessions`
- [ ] TASK-046 mandatory MFA for admin roles
- [ ] TASK-050 users CRUD + profile + password change
- [ ] TASK-060 organizations + properties CRUD
- [ ] TASK-070 permission registry + base role seeding (CRUD layer; seed data already in migration 003)
- [ ] TASK-080 audit service + admin query endpoint
- [ ] TASK-090 cross-tenant isolation suite
- [ ] TASK-100 frontend auth screens
- [ ] TASK-110..113 docker, CI, bootstrap CLI, docs

---

## PR-3, work-unit slice B (PR-3b) — Phase 4 auth, TASK-044 (MFA TOTP + recovery codes)

**Branch:** `feature/auth-multitenant-foundation-pr3b` (from pr3a, feature-branch-chain).

### Status guard

Same resolved guard as prior slices: the "design.md missing" blocker is a filename mismatch —
design content lives in `architecture.md` §4.4 / `api-contract.md` §2.5–2.8 / `data-model.md` §2.2 /
`specs/auth/spec.md` / `test-plan.md`, referenced explicitly by the orchestrator. No substantive
design gap. `actionContext` is `repo-local`, single workspace root, no warnings.

### Completed tasks (this slice)

- [x] **TASK-044** — MFA TOTP endpoints `/auth/mfa/setup`, `/auth/mfa/verify`, `/auth/mfa/disable`,
  `/auth/mfa/challenge`, single-use recovery codes, and completion of the PR-3a login MFA hook into a
  real short-lived `mfa_token`.

`tasks.md` checkbox updated to `- [x]` for TASK-044.

### Files changed (this slice)

Backend (`apps/backend/`):

- `app/core/security.py` — `TOTP` (RFC 6238, stdlib hmac/hashlib) + `JWTService.create_mfa_token` /
  `decode_mfa_token` (5-min `mfa: true` token); `decode_access_token` now rejects `mfa: true` tokens.
  Narrowed `_load_private_key`/`_load_public_key` return types to `RSAPrivateKey`/`RSAPublicKey`
  (fixes a latent PyJWT type-stub warning on the existing `create_access_token`/`decode_access_token`).
- `app/modules/auth/models.py` — `MFADevice` ORM model (maps existing migration `0002_auth`).
- `app/modules/auth/schemas.py` — `MfaSetupResponse`, `MfaVerifyRequest`, `MfaDisableRequest`,
  `MfaChallengeRequest`, `MfaStatusResponse`.
- `app/modules/auth/service.py` — `MFAPending`/`MfaSetupResult`, recovery-code helpers, and methods
  `setup_mfa`, `verify_mfa`, `disable_mfa`, `complete_mfa_login`, `_verify_mfa_code`; `login` now
  returns `MFAPending(mfa_token=…)` instead of `None` when MFA is enabled.
- `app/modules/auth/router.py` — four `/auth/mfa/*` routes (setup/verify/disable self-service under
  `require_auth`; challenge under the bearer `mfa_token`), `_bearer_token` helper, login returns the
  `mfa_token`.
- `tests/integration/auth/test_mfa.py` — 8 integration tests (setup, verify reject/enable, challenge
  full-token + wrong-code, recovery single-use, disable password/require-auth, setup-already-enabled).

Docs (apply artifacts):

- `openspec/changes/auth-multitenant-foundation/tasks.md` (TASK-044 checkbox)
- `openspec/changes/auth-multitenant-foundation/apply-progress.md` (this file)

### TDD cycle evidence (strict)

Runner: `cd apps/backend && .venv/bin/python -m pytest` against Docker PostgreSQL
(`reunionai-test-pg`, `postgresql+asyncpg://reunionai:reunionai@localhost:5433/reunionai`).

| Phase | Evidence | Result |
| --- | --- | --- |
| RED | `ImportError: cannot import name 'TOTP' from 'app.core.security'` (endpoint/TOTP absent) | collection error |
| GREEN | `pytest tests/integration/auth/test_mfa.py -q` after TOTP + models + service + router | `5 passed` |
| TRIANGULATE | added wrong-challenge-code, setup-already-enabled, require-auth tests | `8 passed` |
| REFACTOR | `ruff format` + `ruff check --fix` (import order, blank lines); mypy clean | all clean |

Commands (final green):

- `.venv/bin/python -m pytest -q` → `68 passed` (60 prior + 8 MFA)
- `.venv/bin/ruff check app/ tests/` → `All checks passed!`
- `.venv/bin/ruff format --check app/ tests/` → `41 files already formatted`
- `.venv/bin/mypy app tests` → `Success: no issues found in 41 source files`

### Deviations from design

1. **`design.md` naming** — same resolved mismatch as prior slices (content in architecture/api-contract/
   data-model).
2. **MFA endpoints gated on `require_auth()`, not `require_permission("auth.mfa.manage")`.** The seeded
   permission is `auth.mfa.manage` (data-model §4 / migration 003) but it is **not** granted to any base
   role — including `org_admin` — so gating all four endpoints on it would make MFA enrollment impossible
   for every user. MFA is inherently self-scoped (the caller's own account), mirroring PR-3a's
   `auth.revoke` deviation. Note: spec.md says `user.mfa.manage` while api-contract/data-model say
   `auth.mfa.manage` — an existing naming inconsistency; TASK-070 (permission registry/base-role seeding)
   should reconcile it.
3. **Recovery codes storage.** No dedicated `recovery_codes` column/table exists, and this slice adds no
   migration (PR-1 owns DDL). Recovery codes are persisted one `mfa_devices` row each — `name=
   "recovery-code-<i>"`, `secret_encrypted` = SHA-256 digest of the code — consumed by deleting the row
   on use (single-use). `architecture.md` §8.2 lists "recovery codes not in MVP", but `api-contract.md`
   §2.5 (`backup_codes`) + TASK-044 + orchestrator scope require them; implemented explicitly.
4. **TOTP secret at rest is plaintext base32** in `users.mfa_secret` (architecture §4.4), not the
   `mfa_devices.secret_encrypted` encrypted form implied by the column name (that column stores the
   recovery-code *hashes* here). Matches the already-migrated `users.mfa_secret VARCHAR` column.
5. **TOTP implemented on the stdlib** (`hmac`/`hashlib`/`struct`) rather than a third-party provider, per
   AGENTS.md §5 "interchangeable provider interfaces"; `verify` uses a ±1-step window for clock drift.
6. **`mfa_token` is a 5-minute JWT with `mfa: true`**; `decode_access_token` rejects `mfa: true` and
   `decode_mfa_token` requires it, so the half-authenticated challenge token cannot satisfy
   `require_auth`.

### Workload / PR boundary

- **Actual changed lines: 425 insertions / 19 deletions (5 tracked files) + 198 lines new test file ≈ 642
  changed lines — ~1.6× the 400-line budget.**
- **Honesty check:** no padding; the four endpoints + recovery codes + TOTP + the `mfa_token` handoff form
  one cohesive enrollment/challenge unit — splitting setup/verify from challenge/disable would leave the
  login→challenge flow broken (challenge depends on both the `mfa_token` issued at login and the recovery
  codes minted at setup). A strict sub-split would be `setup+verify` (~endpoint pair) vs `disable+
  challenge+recovery`, but neither lands independently by itself.
- **No `size:exception` claimed** (requires explicit maintainer acceptance) — reported, not inferred.
  Per-file: `security.py` +127/-1, `service.py` +167/-2, `router.py` +102/-6, `models.py` +25/-1,
  `schemas.py` +23, `test_mfa.py` +198 (new).

### Remaining tasks (next slices — NOT in this attempt)

- [ ] TASK-045 session management GET/DELETE `/users/me/sessions`
- [ ] TASK-046 mandatory MFA for admin roles
- [ ] TASK-050 users CRUD + profile + password change
- [ ] TASK-060 organizations + properties CRUD
- [ ] TASK-070 permission registry + base role seeding
- [ ] TASK-080 audit service + admin query endpoint
- [ ] TASK-090 cross-tenant isolation suite
- [ ] TASK-100 frontend auth screens
- [ ] TASK-110..113 docker, CI, bootstrap CLI, docs
