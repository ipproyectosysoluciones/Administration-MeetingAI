# Test plan — pipeline-ocr

Conventions follow `apps/backend/tests/`: integration tests hit the real PostgreSQL test DB via the `migrated_engine` engine with `app` / `api` / `register_admin` fixtures; unit tests use fakes only. PRD §33 requires unit, integration, API, authorization, tenant-isolation, and OCR tests — *"Tenant A must never access Tenant B."*

## Unit tests (`tests/unit/ocr/`)

| Test | Covers |
|---|---|
| `test_ocr_provider.py` | fake `OCRProvider` determinism; `OCRResult` shape (`text/confidence/pages`); mime routing pdf→OCRmyPDF impl, images→Tesseract impl (R7) |
| `test_no_domain_sdk_imports.py` | static check: `pytesseract`/`ocrmypdf` absent from `service.py`/`models.py`/`router.py` (R7 s3) |
| `test_malware_scan.py` | magic-byte table: 5 PRD §16 formats × (match / mismatch / truncated / wrong-declared-type) → pass or `INVALID_FILE_SIGNATURE` (R2) |
| `test_quality_gate.py` | confidence below/equal/above threshold → `failed LOW_CONFIDENCE` / pass / pass; `conf_threshold` recorded on attempt (R4) |
| `test_corrections.py` | correction appends version, bumps `documents.version`, leaves `file_path`/`sha256` untouched; stale `base_version` → 409 (R5) |
| `test_pipeline_attempts.py` | retry bookkeeping on `ocr_jobs`: attempt increments, errors preserved, duration recorded (R3) |

## Integration tests (`tests/integration/documents/`, `tests/integration/ocr/`)

| Test | Covers |
|---|---|
| `test_upload_enqueues` | POST upload → 201, `ocr_status=pending`, job row enqueued, audit `document.upload`+`document.ocr.enqueue` (R1 s1) |
| `test_upload_invalid_format_422` / `test_upload_signature_mismatch` | format allowlist; magic-byte failure surfaces as quality/scan failure (R1 s2, R2 s2) |
| `test_upload_duplicate_409` | sha256 dedupe per tenant (R1 s3) |
| `test_ocr_job_lifecycle` | enqueue → worker run (fake provider) → `completed`; `ocr_text`, `ocr_confidence`, `pages` populated; `ocr_jobs` coherent (R3 s1) |
| `test_ocr_retry_then_success` / `test_ocr_permanent_failure` | backoff retry path; exhaustion → failed + `ocr_error` + audit `ocr.failed` (R3) |
| `test_ocr_in_progress_409` | re-run while `processing` (R3 s4) |
| `test_ocr_low_confidence` | fake provider confidence 0.41 → `ocr_status=failed`, `ocr_error="LOW_CONFIDENCE"`, audit `ocr.quality.failed` (R4 s2) |
| `test_correction_creates_version` | correction → new `document_versions` row `origin="human_correction"`; `GET content?version=1` byte-identical to original (sha256 match) (R5 s1, s4) |
| `test_correction_stale_base_409` | concurrent/stale base version (R5 s2) |
| `test_cross_tenant_404` | tenant B vs tenant A: get document, re-run OCR, correct, list versions, get ocr job → all 404 (R1 s4, R5 s3, api-contract) |
| `test_rbac_403` | secretary cannot delete; president cannot correct/re-run; resident cannot list (R6) |
| `test_audit_chain` | full trace upload→scan-fail→re-run→quality-fail→correction→completed produces ordered `ocr.*`/`document.*` events (R8 s1) |

Fixtures: reuse `register_admin` (org_admin has full matrix after OCR-2 seeds); add role-specific registrars mirroring the minutes integration tests for RBAC matrix cases.

## Migration tests

| Test | Covers |
|---|---|
| `test_migrations.py` (update) | permission count baseline bump after `document.*` + `ocr.*` seeds; role-permission counts per matrix D2 |
| `test_migrations_ocr2.py` (new) | `ocr_jobs` columns/CHECKs/indexes/unique `(document_id, attempt)`; seed `ON CONFLICT DO NOTHING` idempotency (double-run pattern from 0007 tests); `alembic upgrade head` + `downgrade -1` + `upgrade` round-trip |
| `test_registry.py` (existing) | permission seeding idempotent after new resources `document`/`ocr` |

## Frontend (OCR-7)

- `npm run build` — Astro build incl. `/documents`.
- `npm test` — vitest: `lib/documents.ts` client shapes; panel/correction component smoke (processing state renders, quality-failed badge, version history ordering).

## Regression gate

Full backend suite green (baseline: 296 tests), `ruff check`/`mypy app` clean; frontend build green on OCR-7. Each slice merges only with its own tests + the suite green.

## Strict TDD mapping

- OCR-3/4/5 behavior changes follow RED → GREEN with the unit/integration rows above authored first; TRIANGULATE rows are the boundary (threshold equality), stale-base, and cross-tenant negatives.
