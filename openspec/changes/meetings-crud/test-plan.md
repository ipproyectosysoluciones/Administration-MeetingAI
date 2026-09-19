# Test plan — meetings-crud

Conventions: strict TDD (RED → GREEN → REFACTOR), evidence = commit sequence with failing then passing runs. Conftest patterns mirror `tests/integration/organizations/` (session_factory, register_admin, create_member style helpers).

## Layers

**Unit (service-level, pure):** status FSM transitions (allowed/blocked), slug/title validation, timezone conversion (America/Bogota → UTC), permission predicates. Minimum: 12 tests.

**Integration (API + Postgres test container):**
- CRUD: create 201 + audit, read own (list + detail), update, cancel; filters (`status`, `date_from/to`, `q`), pagination, 422 validations. Min: 18 tests.
- Participants: internal add/remove (incl. duplicate 409), external email add/remove, 404 cross-tenant. Min: 8 tests.
- RBAC: every endpoint × {meeting.read/create/update/cancel/participant_manage} absent → 403; unauthenticated → 401. Min: 12 tests.
- Isolation extension: tenant B cannot see/act on tenant A meetings or participants (404 only) — extends `tests/integration/isolation/`. Min: 6 tests.

**Frontend (vitest + jsdom):** list/detail/create-form render + validation + API client paths, error envelope display. Min: 10 tests.

## Totals

Backend ≥ 56 new tests + frontend 10. Full-suite gate: existing 188 backend tests must stay green.

## Production slice map (400-line budget)

S1: migrations + models + permission seeds.  S2: meetings service + router + schemas.  S3: participants service + router.  S4: frontend pages/components + API client.  Test files accompany their slice.