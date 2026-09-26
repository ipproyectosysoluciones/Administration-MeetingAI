# Test plan — meetings-minutes

## Unit tests (`tests/unit/minutes/`)

| Test | Covers |
|---|---|
| `test_ai_provider.py` | `AISummaryProvider` protocol + `MockProvider` determinism and empty-transcript `ValueError` |
| `test_minutes_service.py` | `create_draft` (version 1 + audit, 404 on missing meeting), invalid transitions (publish/archive/approve without the right prior state → 409) |

## Integration tests (`tests/integration/minutes/`)

| Test | Covers |
|---|---|
| `test_minutes_flow.py::test_create_and_get_draft` | POST draft + GET round-trip |
| `test_minutes_flow.py::test_list_meeting_minutes` | paginated list |
| `test_minutes_flow.py::test_full_lifecycle` | draft→review→approved→published→archived |
| `test_minutes_flow.py::test_invalid_transition_409` | out-of-order transition → 409 |
| `test_minutes_flow.py::test_cross_tenant_404` | tenant B cannot read tenant A's minute (404) |

These run against the real PostgreSQL test DB (`migrated_engine`), using `register_admin` (org_admin has all four `minutes.*` permissions) and `seed_meeting`.

## Migration tests

| Test | Covers |
|---|---|
| `test_migrations.py::test_rbac_constraints_and_seed` | permission count baseline (49 after `minutes.*`) and super_admin/org_admin role-permission counts |
| `test_migrations_0009.py` | `minutes` table columns, CHECK constraints, indexes, seed idempotency |
| `test_registry.py::test_seeding_is_idempotent` | permission seed stability |

## Frontend

- `npm run build` — Astro build (7 pages incl. `/minutes`).
- `npm test` — vitest smoke + api client tests.

## Regression gate

Full backend suite is green on SQLAlchemy 2.1 (260+ tests); `ruff check` and `mypy app` clean. The RDD review of the change (lineage `review-8f564fe1b06a2710`) corrected one CRITICAL (R3-cross-tenant-meeting-create) and left 4 non-blocking advisories (see apply-progress.md).
