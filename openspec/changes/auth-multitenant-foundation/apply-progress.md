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
