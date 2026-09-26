# Tasks — meetings-minutes

| Task | Slice | Tipo | Alcance | Gates |
|---|---|---|---|---|
| ~~MIN-100~~ | M1 | feat | migration 0009 `minutes` + `minutes.*` permission seeds | tests_migrations_0009 |
| ~~MIN-101~~ | M2 | feat | `AISummaryProvider` protocol + `MockProvider` (unit) | unit |
| ~~MIN-102~~ | M3 | feat | `Minute` model + `MinutesService` (lifecycle + audit) | unit |
| ~~MIN-103~~ | M4 | feat | REST router + schemas + service list pagination + integration | integration |
| ~~MIN-104~~ | M5 | feat | frontend portal (client + MinutesPanel + página) | build + vitest |
| ~~MIN-fix~~ | M6 | fix | validar meeting en `create_draft` (RDD R3-cross-tenant-meeting-create) | unit + integration |

Convenciones: TDD estricto (RED → GREEN → REFACTOR); cada slice ≤400 líneas de producción; Conventional Commits; PR cierra su issue; no merge si CI no está green.
