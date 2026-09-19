## Slice S1 (TASK-200/201) — merged via PR #49

- Migration 0005 (meetings + meeting_participants, FSM CHECKs, UTC timestamps, FK org/users), seeds meeting.* permissions; base-role assignments extended (super_admin, org_admin, secretary, president, board_member).
- Suite backend: 191/191 (test_migrations_0005 added; registry count updated 34→39).
- Fixes landed in slice: ruff E501 on registry test comment; format pass on touched files.

## Slice S2 (TASK-210/211) — PR #50

- Meetings module: models/schemas/service/router, FSM, tenant scoping, audit events, permission gates.
- Integration tests: 7/7 (incl. FSM + board_member 403 + cross-tenant 404); full suite: 198/198.
- Found during review of my own apply: status-only updates weren't committing (fixed pre-commit).
