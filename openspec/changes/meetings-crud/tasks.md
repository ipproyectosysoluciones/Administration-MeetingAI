# Tasks — meetings-crud

Conventional commits; slice budget ≤400 production lines each (test-plan.md). Backend work runs against Docker Postgres (:5433) with `.venv/bin/python -m pytest`; frontend tests via `pnpm vitest run`; gates ruff + mypy + tsc before every commit.

## Slice S1 — Data foundation

- [x] **TASK-200** `feat: migration 005 meetings + meeting_participants` — UUID PKs, tenant_id NOT NULL + indexes ((tenant_id,date), (tenant_id,status)), status CHECK (scheduled/in_progress/finished/cancelled) + soft delete on meetings, participant role enum (organizer/presenter/attendee), FK user_id nullable (external invitees). Tests: migration smoke + schema introspection + append-only/downs smoke.
- [x] **TASK-201** `feat: seed meeting.* permissions + base-role mapping` — meeting.read/create/update/cancel/participant_manage per spec matrix; idempotent seeding. Tests: permission registry integration test extended.

## Slice S2 — Meetings service + API

- [x] **TASK-210** `feat: meetings service core` — create/get/list/paginate with filters (status/date_from/date_to/q), timezone conversion America/Bogota↔UTC, FSM transitions scheduled→in_progress→finished→cancelled with 422 on invalid, audit event on every mutation. Tests: unit (12+) + integration CRUD (18+).
- [x] **TASK-211** `feat: meetings REST router` — POST/GET list/GET detail/PATCH/POST /{id}/cancel with require_permission per api-contract; request/response schemas Pydantic; tenant injection via auth context (never client). Tests: 401/403/404/422 wire tests; cross-tenant 404 case (extends isolation suite).

## Slice S3 — Participants service + API

- [x] **TASK-220** `feat: meeting participants service` — add internal user (validates user in same tenant, role), add external email, remove, list; duplicate guard 409; audit events. Tests: unit + integration (8+).
- [x] **TASK-221** `feat: participants REST router` — POST/DELETE/GET under /api/v1/meetings/{id}/participants with meeting.participant_manage. Tests: permission matrix + cross-tenant 404.

## Slice S4 — Frontend (portal)

- [x] **TASK-230** `feat: meetings list page` — Astro page + React list component, filters UI, status badge, error state, empty state. Tests: vitest render + interactions.
- [x] **TASK-231** `feat: meeting create/edit form` — React form with validation (date/time split, modality enum, participants UI with internal picker + external email add), server-error envelope display. Tests: vitest component tests incl. API-error mapping.
- [x] **TASK-232** `feat: meeting detail page` — status badge/time formatting (America/Bogota), participants manager, cancel action with confirm. Tests: vitest.

## Phase final

- [x] **TASK-240** `test: extend cross-tenant isolation suite with meetings + participants matrix` — REQUIRES suite ≥6 new cases in tests/integration/isolation.
- [x] **TASK-241** `docs: update architecture notes + api-contract references` — README snippet if any command changed.
- [ ] **TASK-242** `chore: review-readiness pass` — ruff + mypy + full pytest + vitest + tsc; verify apply-progress.md entries; close issue #48 on merge.

## Review Workload Forecast

| Slice | Est. production lines | Risk | Strategy |
|---|---|---|---|
| S1 | ≤180 | low | single PR |
| S2 | ≤380 | medium (core size) | single PR |
| S3 | ≤250 | low | single PR |
| S4 | ≤400 | medium (3 archivos) | single PR |
| Final | ≤80 | low | single PR |

Delivery: `ask-on-risk` — if any slice exceeds budget, split before PR.
