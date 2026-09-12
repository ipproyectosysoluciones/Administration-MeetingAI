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
