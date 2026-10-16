# Design — pipeline-ocr

SDD sections per `reunionai-sdd-workflow`: Context / Problem / Goals / Non-goals live in proposal.md. This file covers Architecture, Security, Testing, Migration, Rollback, Acceptance Criteria. Data changes in data-model.md; API changes in api-contract.md; behavioral requirements in specs/ocr-pipeline/spec.md.

## PRD contracts (verbatim anchors)

- §16 formats: *"PDF. JPG. JPEG. PNG. TIFF."*
- §16 pipeline: *"Upload → Virus/Malware Scan → Document Validation → OCR → Text Extraction → Quality Check → Human Correction → Processed Document"*
- §16 provider interface: *"OCRProvider ├── process() ├── extract_text() └── confidence()"*, *"Implementación inicial: Tesseract. OCRmyPDF."*
- §17: *"Nunca se deberá sobrescribir silenciosamente el documento original."*; traceability fields: *"original, ocr_result, corrected_text, final_document, versions, audit_history"*
- §18: *"storage/tenants/{tenant_id}/ … documents/ …"* and *"El sistema deberá poder migrar posteriormente hacia S3-compatible storage sin rediseñar el dominio."*
- §27: OCR listed under async tasks; states *"queued, processing, completed, failed, cancelled"*.

## Architecture

### Module layout (extends existing — nothing redesigned)

```
app/modules/documents/         # EXISTS: models, service (CRUD+versioning+upload), router, schemas, providers
app/modules/ocr/
  providers.py                 # EXTEND: OCRProvider port + OCRResult; replace mocks with real impls
  service.py                   # EXTEND: OCRService pipeline orchestration (validate → scan → OCR → quality)
  workers.py                   # NEW: OCRWorker (process_ocr handler, mirrors TranscriptionWorker)
app/modules/jobs/              # REUSE as-is: JobService.enqueue_ocr / claim / complete / fail
app/modules/rbac/              # permission seeds land via migration (OCR-2)
```

Frontend (OCR-7):

```
apps/frontend/src/
  lib/documents.ts                       # API client + types
  components/documents/DocumentsPanel.tsx # list + upload + processing states
  components/documents/CorrectionEditor.tsx# human correction → new version
  pages/documents/index.astro             # portal page
```

### Pipeline stage → service mapping

| PRD §16 stage | Implementation |
|---|---|
| Upload | `POST /documents/upload` (exists) → stores original via `DocumentStorageProvider`, sha256 dedupe, `documents.status=pending`, `ocr_status=pending`, initial `document_versions` row v1 |
| Virus/Malware Scan | `MalwareScanHook` seam in `OCRService`, invoked inside the worker before OCR. MVP: magic-byte signature validation per declared type (`%PDF-`, `\x89PNG`, JFIF/EXIF, TIFF `II*`/`MM*`), reject mismatch → job failed + audit `ocr.scan.failed`. ClamAV: **Decision/follow-up — see Non-goals** |
| Document Validation | extension+MIME against PRD §16 types → `422 INVALID_DOCUMENT_TYPE`/`INVALID_FILE_SIGNATURE`; format sniff, page extractability for PDFs via OCRmyPDF probe |
| OCR | `OCRProvider.process()` — PDF → OCRmyPDF impl (`ocrmypdf` sidecar text + `pytesseract.image_to_data` fallback); images → `pytesseract` |
| Text Extraction | `OCRProvider.extract_text()` returns normalized text → `documents.ocr_text`; per-page text → `ocr_jobs.metadata_json` |
| Quality Check | `OCRProvider.confidence()` vs configurable threshold (`OCR_CONFIDENCE_THRESHOLD`, default 0.60). Below threshold → `ocr_status=failed`, `ocr_error="LOW_CONFIDENCE"`, document flagged for correction (UI-visible), audit `ocr.quality.failed`. Above → `ocr_status=completed` |
| Human Correction | `POST /documents/{id}/corrections` with `ocr.correct` → appends `document_versions` row with corrected text (`metadata_json.origin="human_correction"`), bumps `documents.version`, sets current text; **original `file_path`/`sha256` untouched** |
| Processed Document | `documents.status=completed` with `ocr_text` = latest accepted text; traceability chain = original v1 + versions + audit history |

### Job lifecycle (PRD §27)

HTTP handlers never run OCR. `upload` + `POST /documents/{id}/ocr` enqueue via `JobService.enqueue_ocr(document_id)`. The OCR worker (OCR-6) claims with `FOR UPDATE SKIP LOCKED`, runs the pipeline, then `complete`/`fail` (exponential backoff already implemented in `JobService.fail`; `max_attempts=5`).

PRD §27 states ↔ existing `jobs.status` names (existing values are `pending/running/done/failed`):

| PRD §27 | `jobs.status` | Notes |
|---|---|---|
| queued | `pending` | |
| processing | `running` | claimed, `locked_by=worker_id` |
| completed | `done` | |
| failed | `failed` | permanent after max attempts |
| cancelled | — | **not yet in jobs table**; OCR re-run of a queued job supersedes by creating a new job; explicit cancel is out of MVP scope |

The per-document pipeline state machine visible to users stays on `documents.ocr_status` (`pending/processing/completed/failed`) — unchanged values, now driven by the worker. `ocr_jobs` (OCR-2 additive table) holds per-attempt detail: attempt number, `job_id` link, confidence, error, duration.

### Dependency direction

```
router → DocumentsService / OCRService → models
                ↓                    ↓
        MalwareScanHook (port)   OCRProvider (port)
                ↓                    ↓
        JobService.enqueue_ocr   AuditService events (ocr.*, document.*)
worker: JobService.claim → OCRService.run_pipeline → JobService.complete/fail
```

The domain never imports `pytesseract`/`ocrmypdf`/ClamAV SDKs — only the ports; concrete providers are constructed in composition root (`app.state`) — mirrors `AISummaryProvider` in minutes.

## Security

- **Tenant scoping**: sole source `AuthContext.tenant_id`; every documents/ocr query filters `tenant_id` and `deleted_at IS NULL`; cross-tenant reads/writes/corrections yield `404` (never 403). Storage keys stay under `storage/tenants/{tenant_id}/documents/` (PRD §18) — worker resolves paths only through `DocumentStorageProvider` with the row's tenant.
- **RBAC**: `document.read/upload/download/update/delete` (existing references — seeded in OCR-2) + `ocr.run` (re-run), `ocr.read` (job/result detail), `ocr.correct` (corrections). Role matrix mirrors `minutes.*` (super_admin + org_admin full; secretary read/upload/correct; president read; others none). Backend enforces; frontend only hides (AGENTS.md rule 10).
- **Audit** (`resource="document"` or `"ocr_job"`; actor, tenant, ts, ip, user_agent per skill contract): `document.upload` (exists), `document.ocr.enqueue`, `ocr.scan.failed`, `ocr.completed`, `ocr.quality.failed`, `ocr.failed`, `ocr.correction.create` (+ existing `document.version.create`).
- **Upload safety**: PRD §16 type allowlist enforced by extension **and** magic bytes; size cap via config; sha256 computed server-side; originals immutable post-upload; nothing in the OCR path writes the original's `file_path`.
- **Secrets**: none; thresholds/path config via env, `.env.example` updated in OCR-6.

## Testing

(Strategy; concrete cases in test-plan.md.)

- Unit: provider port with fakes (deterministic `OCRResult`), signature validation table (5 formats × match/mismatch/corrupt), confidence threshold boundary, correction version increment.
- Integration: upload→enqueue→worker-run→completed happy path via `register_admin`/app fixtures; 404 cross-tenant on get/ocr/correction/versions; 403 without `ocr.*`; duplicate sha256 → 409; re-run while running → 409; low-confidence → quality-failed state; correction creates version, original untouched.
- Migration: additive `ocr_jobs` + permission seed (count baseline bump like `test_migrations.py`), seed idempotency (0007 pattern), upgrade idempotent from 228004878c15 head.
- Tenant isolation (PRD §33 emphasis): *"Tenant A must never access Tenant B."* — dedicated IDOR cases for every new route.

## Migration

Additive only (AGENTS.md rule 5 — never destructive):

1. New revision with `down_revision` = current head (must include 228004878c15 in ancestry); create `ocr_jobs` (see data-model.md); backfill nothing.
2. Seed `document.*` + `ocr.*` permissions and `role_permissions` with `ON CONFLICT DO NOTHING` (0007 pattern) — idempotent re-runnable.
3. No ALTER to `documents`/`document_versions` required **except** optional non-blocking index `ix_document_versions_document_id_version` (exists) — data-model.md confirms zero column changes.

## Rollback

- OCR-2: `downgrade()` drops `ocr_jobs`, deletes seeded permissions by `resource IN ('document','ocr')` (0007 reverse pattern). Existing `documents` data untouched.
- OCR-3/4/5: features are code-only behind the router; revert commit; queued `process_ocr` jobs remain `pending` and are inert without the worker.
- OCR-6: remove compose service; jobs stay queued harmlessly.
- OCR-7: frontend-only; revert routes/components.

## Acceptance Criteria

1. Uploading a PRD §16 format enqueues OCR; the document transitions `pending → processing → completed` without blocking the HTTP request; `ocr_text` + `ocr_confidence` populated.
2. Confidence below threshold yields a quality-failed, correction-required state; a human correction creates a new `document_versions` row and **never** modifies the original file/sha256 (PRD §17).
3. Every REST route requires its permission; cross-tenant access returns 404; all critical ops write audit events.
4. `TesseractOCRProvider`/OCRmyPDF can be replaced by implementing the PRD §16 `OCRProvider` interface with zero domain changes.
5. `alembic upgrade head` is idempotent; full backend suite green; frontend build green (OCR-7).
