# Spec — pipeline-ocr (delta specs)

Scope: OpenSpec delta for module `ocr` + pipeline deltas on module `documents`; conventions follow `minutes` / `transcription` (camelCase permission names, `resource.action` format, 404 cross-tenant, audit on every critical op). PRD anchors quoted verbatim.

PRD §16 mandates formats *"PDF. JPG. JPEG. PNG. TIFF."*, the pipeline *"Upload → Virus/Malware Scan → Document Validation → OCR → Text Extraction → Quality Check → Human Correction → Processed Document"*, and the contract *"OCRProvider ├── process() ├── extract_text() └── confidence()"* with initial implementations *"Tesseract" / "OCRmyPDF"*. PRD §17: *"Nunca se deberá sobrescribir silenciosamente el documento original."* PRD §27: OCR is async with states *"queued / processing / completed / failed / cancelled"*.

## Requirement R1 — Upload is tenant-scoped, format-validated, and enqueue-only

A user with `document.upload` MAY upload a document into their own tenant. The service MUST reject any type outside the PRD §16 allowlist with `422 INVALID_DOCUMENT_TYPE`, MUST compute sha256 server-side and reject duplicates with `409 DUPLICATE_DOCUMENT`, MUST store the original under the tenant-scoped storage path (PRD §18 `storage/tenants/{tenant_id}/documents/`), and MUST NOT run OCR inside the request — it SHALL enqueue a `process_ocr` job via `JobService` and return with `ocr_status=pending`.

Scenarios:
1. **Happy path** — valid PDF in tenant → 201, `documents.status=pending`, `ocr_status=pending`, v1 version row `metadata_json.origin="upload"`, audit `document.upload` + `document.ocr.enqueue`, job queued.
2. **Unsupported format** — `doc.exe` → 422 `INVALID_DOCUMENT_TYPE`; no row, no file stored.
3. **Duplicate content** — same sha256, same tenant → 409 `DUPLICATE_DOCUMENT`.
4. **Tenant isolation** — tenant A's upload never appears in tenant B's list (404/empty list, not 403).

## Requirement R2 — Malware scan is a mandatory pipeline step behind a provider seam

Before OCR, the worker MUST invoke the malware-scan validation step. The MVP implementation SHALL verify magic-byte signatures per declared type (`%PDF-`, `\x89PNG`, JFIF/EXIF, TIFF `II*`/`MM*`) and MUST fail the job + document on mismatch (`422 INVALID_FILE_SIGNATURE` surfaced as `ocr_status=failed`, `ocr_error="INVALID_FILE_SIGNATURE"`), recording audit `ocr.scan.failed`. The step MUST be a swappable provider port so ClamAV integrates later without domain changes (AGENTS.md rules 11–12).

Scenarios:
1. **Signature match** — PNG bytes declared `png` → scan passes, OCR proceeds.
2. **Signature mismatch** — PE/ELF bytes declared `pdf` → job failed, document `ocr_status=failed`, audit `ocr.scan.failed`, no provider call.
3. **Provider swap** — replace the signature validator with a ClamAV-backed implementation; pipeline behavior contract unchanged.

## Requirement R3 — OCR job lifecycle follows PRD §27 states and is retryable

`ocr_jobs` rows MUST track `queued → processing → completed | failed` (PRD vocabulary). The generic `jobs` transport row uses existing `pending/running/done/failed` with SKIP-LOCKED claiming; retries follow existing exponential backoff up to `max_attempts`. Re-running OCR on a document with an attempt currently `processing` MUST return `409 OCR_IN_PROGRESS`; a re-run of a completed/failed document SHALL create attempt `max+1`. Worker success SHALL set `documents.ocr_text`, `ocr_confidence`, `pages`, `ocr_status=completed|failed` and audit `ocr.completed` / `ocr.failed`.

Scenarios:
1. **Full lifecycle** — enqueue → worker claims (`processing`) → provider returns → `completed`; both `ocr_jobs` and `documents` coherent; `duration_ms` recorded.
2. **Transient failure** — provider raises on attempt 1 → transport retries with backoff → attempt succeeds → `completed`; attempts preserved on `ocr_jobs`.
3. **Permanent failure** — attempts exhausted → `jobs.status=failed`, `ocr_jobs.status=failed`, `documents.ocr_status=failed`, `ocr_error` populated, audit `ocr.failed`.
4. **Concurrent re-run** — POST ocr while `processing` → 409, no new job.

## Requirement R4 — Quality gate on confidence

After extraction, the pipeline MUST call `confidence()` and compare against the configured threshold (`OCR_CONFIDENCE_THRESHOLD`, default 0.60). Below threshold SHALL NOT mark the document completed: `ocr_status=failed`, `ocr_error="LOW_CONFIDENCE"`, and audit `ocr.quality.failed` — the document is flagged for human correction (R5). Threshold equality passes. The threshold used MUST be recorded on the `ocr_jobs` attempt (`conf_threshold`).

Scenarios:
1. **Above threshold** — confidence 0.93 vs 0.60 → `completed`.
2. **Below threshold** — 0.41 → quality-failed state, text retained in `ocr_text` for correction, audit `ocr.quality.failed`.
3. **Boundary** — exactly 0.60 → pass.
4. **Threshold auditability** — attempt row shows the threshold applied, so a later config change never rewrites history.

## Requirement R5 — Human correction appends a version; the original is never overwritten

A user with `ocr.correct` MAY submit corrected text for a document in their tenant. The service MUST create a new `document_versions` row (`metadata_json.origin="human_correction"`, `created_by`=actor), bump `documents.version`, and set `ocr_text` to the corrected text. It MUST NOT modify `file_path`, `file_size`, or `sha256` of the original (PRD §17 verbatim: *"Nunca se deberá sobrescribir silenciosamente el documento original"*). A correction referencing a stale `base_version` MUST fail with `409 VERSION_CONFLICT`. Audit: `ocr.correction.create`.

Scenarios:
1. **Happy path** — correction on v1 → v2 row appended; original file/sha256 untouched; version history shows upload → ocr → human_correction chain (PRD §17 `versions` + `audit_history`).
2. **Stale base** — concurrent correction with `base_version=1` after another correction landed v2 → 409.
3. **Cross-tenant** — tenant B corrects tenant A's document → 404.
4. **Original intact** — `GET /documents/{id}/content?version=1` streams bytes identical to upload (sha256 match).

## Requirement R6 — RBAC gates every surface

Routes MUST enforce: `document.read` (get/list/versions), `document.upload` (upload), `document.download` (content), `document.update` (patch), `document.delete` (delete), `ocr.run` (re-run), `ocr.read` (ocr job list/detail), `ocr.correct` (corrections). Missing permission → 403; no active membership → 403 `NO_ACTIVE_MEMBERSHIP`. The backend never relies on frontend restrictions.

Scenarios:
1. **org_admin** — full matrix → all operations succeed.
2. **secretary** — may upload, re-run, and correct; may NOT delete (`document.delete` not in matrix).
3. **president** — read/download only; POST corrections → 403.
4. **resident** — list → 403.

## Requirement R7 — Provider swappability (PRD §16 interface)

The domain MUST depend only on `OCRProvider` with `process()`, `extract_text()`, `confidence()`; concrete providers (`tesseract` for images, OCRmyPDF for PDFs) MUST be selected by mime type and constructed outside the domain. Mock/fake providers MUST remain first-class for tests.

Scenarios:
1. **Mime routing** — `application/pdf` → OCRmyPDF impl; `image/png` → Tesseract impl.
2. **Fake determinism** — fake provider returns fixed `OCRResult`; pipeline produces identical rows across runs.
3. **Zero domain import** — static check: no `pytesseract`/`ocrmypdf` import in `service.py`/`models.py`/`router.py` (enforced via test or lint rule in OCR-3).

## Requirement R8 — Audit coverage

Every critical operation MUST record an audit event with actor, tenant, action, resource, resource_id, timestamp, ip, user_agent: `document.upload`, `document.ocr.enqueue`, `ocr.scan.failed`, `ocr.completed`, `ocr.failed`, `ocr.quality.failed`, `ocr.correction.create` (plus existing `document.*` events). Audit events are never editable from the UI.

Scenarios:
1. **Full trace** — upload → scan fail → successful re-run → quality fail → correction → re-run success yields the exact ordered event chain above on `audit_events` for the tenant.
2. **No cross-tenant audit leak** — tenant B's audit listing shows none of tenant A's OCR events.
