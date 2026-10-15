# Data model — pipeline-ocr

Baseline: migration **228004878c15** (`documents`, `document_versions`) and ORM in `app/modules/documents/models.py` already exist and are **not redesigned** — this document maps pipeline semantics onto them and defines the additive deltas for slice OCR-2. PRD §29 lists `ocr_jobs` as an initial entity; it does not exist yet.

## Existing tables (no ALTER required)

### `documents` (228004878c15) — one row per uploaded original

| Column | Type | Pipeline meaning |
|---|---|---|
| `id` | UUID PK | document id |
| `tenant_id` | UUID FK `organizations.id` | tenant root — every query filters on it |
| `meeting_id` | UUID FK, NULL | optional link to a meeting |
| `title`, `description` | VARCHAR/TEXT | display metadata |
| `type` | ENUM `pdf/jpg/jpeg/png/tiff` | PRD §16 format allowlist, verbatim |
| `status` | ENUM `pending/processing/completed/failed` | document-level lifecycle (upload validation + overall) |
| `file_path` | VARCHAR(500) | **original** storage key under `storage/tenants/{tenant_id}/documents/` — immutable after upload (PRD §17) |
| `file_size`, `sha256`, `mime_type` | — | original fingerprints; sha256 dedupe → 409 `DUPLICATE_DOCUMENT` |
| `version` | INT, CHECK ≥1 | current accepted version pointer; bumped by human correction |
| `ocr_text` | TEXT | latest OCR/corrected text (PRD §17 `ocr_result`/`corrected_text` — history lives in `document_versions`) |
| `ocr_confidence` | FLOAT | latest `OCRProvider.confidence()` |
| `ocr_status` | VARCHAR(20) | `pending/processing/completed/failed` — user-visible pipeline state |
| `ocr_error` | TEXT | last error or `LOW_CONFIDENCE` quality-gate marker |
| `pages` | INT, NULL | from `OCRResult.pages` |
| `uploaded_by` | UUID FK | original uploader |
| `deleted_at` | TIMESTAMPTZ | soft delete (business reason: retention/portal hide) |
| `created_at`, `updated_at` | TIMESTAMPTZ | |

Indexes: `ix_documents_tenant_id`, `ix_documents_meeting_id`, `ix_documents_status`, `ix_documents_sha256`, `ix_documents_uploaded_by`.

### `document_versions` (228004878c15) — append-only traceability (PRD §17 `versions`)

| Column | Pipeline meaning |
|---|---|
| `document_id` FK CASCADE | owner |
| `version` INT CHECK ≥1 | v1 = original upload snapshot; v2+ = human corrections |
| `file_path`, `file_size`, `sha256` | snapshot of the file state at that version (v1 == original forever) |
| `ocr_text`, `ocr_confidence`, `ocr_status`, `pages` | text state at that version |
| `metadata_json` JSONB | provenance: `origin: "upload" \| "ocr" \| "human_correction"`, `provider`, `job_id`, threshold used |
| `created_by` FK users, `created_at` | actor + timestamp per PRD §17 `audit_history` complement |

## Delta proposals (OCR-2 — additive only, AGENTS.md rule 5)

### D1. New table `ocr_jobs` (PRD §29) — required

Per-document/per-attempt OCR execution detail, complementing the generic `jobs` transport table (which only knows `payload.document_id`).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK `gen_random_uuid()` | |
| `tenant_id` | UUID | FK `organizations.id` ON DELETE CASCADE, NOT NULL | denormalized for tenant-scoped job inspection |
| `document_id` | UUID | FK `documents.id` ON DELETE CASCADE, NOT NULL | |
| `job_id` | UUID | FK `jobs.id` ON DELETE SET NULL, NULL | link to transport queue row |
| `attempt` | INT | NOT NULL, CHECK ≥1 | increments per re-run |
| `status` | VARCHAR(20) | NOT NULL, CHECK in (`queued`,`processing`,`completed`,`failed`) | **PRD §27 states verbatim** (transport uses pending/running/done; this table uses PRD vocabulary) |
| `provider` | VARCHAR(50) | NOT NULL | e.g. `tesseract`, `ocrmypdf` |
| `confidence` | FLOAT | NULL | result confidence; NULL until completed |
| `conf_threshold` | FLOAT | NOT NULL | threshold applied at this attempt (auditability of quality gate) |
| `error` | TEXT | NULL | |
| `duration_ms` | INT | NULL | PRD §34 observability (`tiempo de OCR`) |
| `pages` | INT | NULL | |
| `metadata_json` | JSONB | NOT NULL default `{}` | per-page confidence, scan result detail |
| `created_by` | UUID | FK `users.id` ON DELETE SET NULL | actor who enqueued/re-ran |
| `started_at`, `completed_at`, `created_at` | TIMESTAMPTZ | | |

Indexes: `ix_ocr_jobs_tenant_id`, `ix_ocr_jobs_document_id`, `ix_ocr_jobs_status`, unique `(document_id, attempt)`.

### D2. Permission seeds (idempotent, 0007 pattern) — required

`document.read`, `document.upload`, `document.download`, `document.update`, `document.delete`, `ocr.run`, `ocr.read`, `ocr.correct` (all `is_system=TRUE`).

| Role | document.read | document.upload | document.download | document.update | document.delete | ocr.run | ocr.read | ocr.correct |
|---|---|---|---|---|---|---|---|---|
| super_admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| org_admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| secretary | ✓ | ✓ | ✓ | — | — | ✓ | ✓ | ✓ |
| president | ✓ | — | ✓ | — | — | — | ✓ | — |
| board_member | — | — | — | — | — | — | — | — |
| resident | — | — | — | — | — | — | — | — |

> Note: `document.*` is referenced by the router today but never seeded — OCR-2 fixes this; flag behavior change in that PR's Security impact section.

### D3. Non-changes (explicit)

- No ALTER on `documents`/`document_versions`: existing columns carry the whole pipeline (quality gate uses `ocr_error="LOW_CONFIDENCE"` + `ocr_status=failed`; corrections reuse `version` bump + `document_versions`).
- No destructive operations, no enum value removal. Adding new `document_status`/`ocr_status` values later would be a new additive migration.
- Migration head alignment: the OCR-2 revision must name its `down_revision` so 228004878c15 stays in the ancestry (currently the chain mixes numbered and hash ids).

### Open item

- **Decision needed (mirrors proposal)**: D1 assumes PRD §29's dedicated `ocr_jobs`. Alternative: drop D1 and store attempts in `document_versions.metadata_json` + `jobs`. D1 is PRD-faithful and keeps attempt analytics (PRD §34) queryable; confirm in OCR-1 review.
