# ROADMAP

> Estado al 2026-10-14: **MVP cerrado** — todos los issues y PRs resueltos y mergeados a `develop`.
> Conversión: pytest 283/283 · frontend tsc + vitest + build limpios.
> Proceso: un commit por proceso (Convencional Commits), issue por tarea, PRs de ~400 líneas; si un frente supera ese límite se divide en PRs encadenadas.

## Done

| Phase | Content | Ranges |
|-------|---------|--------|
| Auth multi-tenant foundation | auth, users, organizations, rbac, audit, login UI | PRs #37–45, issue n/a |
| Meetings CRUD | meetings + participants + FSM + portal | PRs #49–55, issue archived |
| Recordings upload | upload/download/list, jobs queue | PRs #57–63, issue #56 closed |
| Meetings transcription | PR #66→#81 migration+worker+read API | issues #64, #74–78 closed |
| Release chain | SemVer rc + GHCR publish on tags | PRs #65, #69, #83–85 |
| Meetings minutes (actas) | MIN-100..105: migration, service, REST, portal UI, AISummaryProvider wired | issues #95–106, #110, PRs #90–104 |
| Backend scaffold extra | modules documents/OCR/AI/jobs/notifications + password reset + minutes versioning | issue #122 closed |
| Frontend scaffold | UI kit, layouts, portal + admin pages | issue #121 closed |
| Global API gaps | global minutes/recordings/transcriptions endpoints + DELETE minutes | PR #165, issue #119 closed |
| Minutes race condition | versioning sin race (flush antes de delete) | PR #164, issue #115 closed |
| Real AI provider | OpenAI-compatible provider para generación de actas | PR #166, issue #118 closed |
| Frontend typecheck | ~200 errores tsc eliminados + vitest + build en CI | PRs #158–159, issue #117 closed |
| Transcription E2E | smoke E2E con Whisper real sobre PG migrado | commit d157be9, issue #120 closed |

## Next — Post-MVP (issues por crear al publicar este roadmap)

1. **Pipeline OCR** (PRD §16–18): `OCRProvider` port + Tesseract/OCRmyPDF, `documents` + `ocr_jobs`, virus/malware scan, quality check, corrección humana, versionado documental (el original nunca se sobrescribe), workers separables. Base: scaffolds `ocr/` y `documents/`.
2. **Búsqueda transversal** (PRD §23): full-text search PostgreSQL sobre reuniones, actas, documentos, transcripciones, participantes, acuerdos y tareas. GraphQL opcional solo para consultas complejas (§25). Búsqueda semántica/vectorial queda para fase posterior.
3. **Módulo de notificaciones** (PRD §19–20, §27): `NotificationProvider` port + `EmailProvider` MVP (invitaciones, recuperación, actas publicadas, documentos disponibles, solicitudes de revisión, aprobación, alertas), envío asíncrono con jobs reintentables.
4. **Módulo de administración** (PRD §22): dashboards (general + admin), gestión de organizaciones, usuarios, roles, permisos, configuración y auditoría con `tenant_id` obligatorio.

## Next — Higiene técnica

- Limpiar **133 errores ruff** y **46 errores mypy** preexistentes en áreas no tocadas por el MVP (deuda registrada al cierre). Activar enforcement en CI al llegar a cero.

## Later

- OCR OCRmyPDF pipeline completo sobre lotes + workers separados dedicados si la carga lo requiere (PRD §31).
- Búsqueda semántica/vectorial (PRD §23).
- Proveedores de notificación adicionales: WhatsApp, Telegram (PRD §19).
- Observabilidad avanzada: OpenTelemetry/Prometheus/Grafana (PRD §34).
- Módulos de jurisdicción configurables empezando por Colombia (PRD §36).
- Migración de storage local a S3-compatible sin rediseño de dominio (PRD §18).

## Incidents resolved

- SQLAlchemy 2.1 upstream breaking the mypy in organizations/users services — mitigated by `sqlalchemy>=2.0` unpin with `Row` aliasing fix (PR #82, issue #79 closed, SA 2.1 suite 260 green).
