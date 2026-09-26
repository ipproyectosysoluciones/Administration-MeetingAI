# Apply progress — meetings-minutes

Change: `meetings-minutes` (SDD). Estado: **implementado y mergeado a develop** en slices M1–M6.

## TDD Cycle Evidence

| Slice | Task | RED | GREEN | PR | RDD |
| --- | --- | --- | --- | --- | --- |
| M1 | MIN-100 migration 0009 + seeds | colección falla sin archivo | test_migrations_0009 pasa | #97 | — |
| M2 | MIN-101 AI provider port | ImportError sin módulo | 3/3 unit | #98 | — |
| M3 | MIN-102 model + service | — | unit transiciones (8 passed) | #100 | — |
| M4 | MIN-103 REST + schemas | endpoints 404 | 5 integration + 7 unit | #102 | — |
| M5 | MIN-104 frontend | — | build 7 páginas + vitest 17 | #104 | — |
| M6 | MIN-fix cross-tenant create | test 404 falla | 13 passed (unit+integration) | #105 | review-8f564fe1b06a2710 |

## RDD review

El cambio acumulado (19 archivos, 1334 líneas, tier medium, lens `review-reliability`) cerró **aprobado** en `review-8f564fe1b06a2710` con:

- **1 CRITICAL corregido** (`R3-cross-tenant-meeting-create`): `create_draft` no validaba que `meeting_id` pertenece al tenant. Corregido en M6 (validación de Meeting → 404 controlado) y validado por targeted validator.
- **4 advisories no bloqueantes** (follow-ups, nunca re-ejecutar review por ellos):
  - `R3-append-only-not-implemented` (WARNING) — el docstring "append-only" es engañoso; el status muta in-place (solo el audit es append-only).
  - `R3-audit-test-does-not-assert` (WARNING) — el test no asevera el evento de auditoría.
  - `R3-empty-title` (SUGGESTION) — `title` vacío no validado.
  - `R3-version-race` (WARNING) — `version = max+1` tiene condición de carrera.

## Notas de proceso

- Desviación documentada: canal de subagentes inestable; slices M1–M5 implementadas inline con autorización del owner y TDD orquestado por el padre (same as meetings-transcription).
- Incidente de CI: baseline de permisos (45→49) y `DateTime(timezone=True)` corregidos en M3/M4 tras fallas de integración reales (naive datetime vs TIMESTAMPTZ).
- Issues: #94, #99, #101, #103 cerradas por sus PRs; #106 (recreación de estos artefactos) cerrada por este cambio.
- Follow-ups abiertos: MIN-105 (cablear `AISummaryProvider.summarize()` al draft), 4 advisories R3, issues de transcription #90/#91/#92.
