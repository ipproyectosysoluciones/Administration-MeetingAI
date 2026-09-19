## Slice S1 (TASK-200/201) — merged via PR #49

- Migration 0005 (meetings + meeting_participants, FSM CHECKs, UTC timestamps, FK org/users), seeds meeting.* permissions; base-role assignments extended (super_admin, org_admin, secretary, president, board_member).
- Suite backend: 191/191 (test_migrations_0005 added; registry count updated 34→39).
- Fixes landed in slice: ruff E501 on registry test comment; format pass on touched files.

## Slice S2 (TASK-210/211) — PR #50

- Meetings module: models/schemas/service/router, FSM, tenant scoping, audit events, permission gates.
- Integration tests: 7/7 (incl. FSM + board_member 403 + cross-tenant 404); full suite: 198/198.
- Found during review of my own apply: status-only updates weren't committing (fixed pre-commit).

## Slice S3 (TASK-220/221) — PR #51

- participants_service + participants_router; internal/external channels with CHECK constraint + RBAC meeting.participant_manage (403), duplicate 409, cross-tenant 404 via tenancy of parent meeting. Suite backend 205/205.

## TASK-240/241/242 — aislamiento + docs + cierre

- Extendida la suite de aislamiento con 6 casos para meetings/participants (#54).
- `docs/architecture/meetings-crud.md` documenta el módulo (FSM, participantes, aislamiento).
- Suite final: backend 214/214 ✔ ruff/format ✔ mypy ✔; frontend 17/17 ✔ tsc ✔ build ✔.
- El cambio `meetings-crud` queda completo. Seguimiento: `meetings-recording-upload`.
