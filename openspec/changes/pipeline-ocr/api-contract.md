# API contract — pipeline-ocr

Base path: `/api/v1`. Bearer auth on every route; tenant is derived from the authenticated membership (`AuthContext.tenant_id`), never from a request body/param. Cross-tenant access yields `404` (existence never leaks). Style mirrors the existing documents router (`DocumentUpload`/`DocumentRead`/… dependency aliases, `_tenant()` helper, `_pages()` pagination).

## Existing `/api/v1/documents` surface (kept; deltas marked)

| Method | Path | Permission | Status | Notes / delta |
|---|---|---|---|---|
| GET | `/documents` | `document.read` | 200 | paginated list (`page`, `page_size`, `status`, `type`, `q`) — exists |
| POST | `/documents` | `document.upload` | 201 | metadata-only create — exists |
| GET | `/documents/{document_id}` | `document.read` | 200 | 404 `DOCUMENT_NOT_FOUND` cross-tenant — exists |
| PATCH | `/documents/{document_id}` | `document.update` | 200 | title/description/meeting_id — exists |
| DELETE | `/documents/{document_id}` | `document.delete` | 204 | soft delete + audit — exists |
| POST | `/documents/upload` | `document.upload` | 201 | **delta**: response returns `ocr_status=pending` and `202`-style semantics — upload now **enqueues** `process_ocr` instead of marking `status=completed` synchronously; audit `document.upload` + `document.ocr.enqueue` |
| GET | `/documents/{document_id}/content` | `document.download` | 200 | stream; `?version=N` for a snapshot (v1 is always the original) — exists |
| GET | `/documents/{document_id}/versions` | `document.read` | 200 | paginated `DocumentVersionResponse` list — exists |
| POST | `/documents/{document_id}/ocr` | `ocr.run` | 202 | **delta**: permission was `document.upload`; now async — enqueues a new `process_ocr` job + `ocr_jobs` attempt row |

> Breaking-change note for OCR-5: `POST /documents/{id}/ocr` moves from synchronous 200 to async **202** with an `OcrJobResponse` body, and its gate moves to `ocr.run`. Version-pinned under `/api/v1` … **Decision needed**: keep sync behavior for one release behind a flag, or accept the contract break at MVP stage (recommended: break now, document in PR — no consumers besides the portal exist yet).

## New routes (OCR-5)

| Method | Path | Permission | Status | Notes |
|---|---|---|---|---|
| POST | `/documents/{document_id}/corrections` | `ocr.correct` | 201 | human correction → new `document_versions` row (never touches original); 409 `VERSION_CONFLICT` on stale `base_version` |
| GET | `/ocr/jobs` | `ocr.read` | 200 | tenant-scoped list of `ocr_jobs` (filter: `document_id`, `status`; paginated) |
| GET | `/ocr/jobs/{ocr_job_id}` | `ocr.read` | 200 | attempt detail incl. confidence + error; 404 cross-tenant |

## Request bodies

`CorrectionCreateRequest`:
```json
{
  "corrected_text": "Texto corregido por el secretario…",
  "base_version": 3,
  "notes": "Nombres propios revisados"
}
```

`POST /documents/{document_id}/ocr`: no body; re-run is idempotent per document state (409 while an attempt is `processing`; otherwise enqueues attempt `max+1`).

## Responses

`DocumentResponse`: unchanged from the existing router (`id, tenant_id, meeting_id, title, description, type, status, file_path, file_size, sha256, mime_type, version, ocr_text, ocr_confidence, ocr_status, ocr_error, pages, uploaded_by, created_at, updated_at`) — `file_path` is the **original**, never rewritten after upload.

`OcrJobResponse`:
```json
{
  "id": "uuid",
  "document_id": "uuid",
  "attempt": 2,
  "status": "queued",
  "provider": "tesseract",
  "confidence": null,
  "conf_threshold": 0.6,
  "error": null,
  "duration_ms": null,
  "pages": null,
  "created_by": "uuid",
  "started_at": null,
  "completed_at": null,
  "created_at": "iso"
}
```

`OcrJobListResponse`: `{ items: [OcrJobResponse], total, page, page_size, pages }`.

`DocumentVersionResponse` (unchanged shape): includes `metadata_json.origin ∈ {"upload","ocr","human_correction"}` for traceability display (PRD §17).

## Errors

| Code | HTTP | Meaning |
|---|---|---|
| `DOCUMENT_NOT_FOUND` | 404 | document absent or foreign tenant (get/ocr/corrections/versions) |
| `OCR_JOB_NOT_FOUND` | 404 | ocr job absent or foreign tenant |
| `NO_ACTIVE_MEMBERSHIP` | 403 | no active tenant membership |
| `Insufficient permissions` | 403 | missing `document.*`/`ocr.*` permission |
| `DUPLICATE_DOCUMENT` | 409 | sha256 already exists in tenant (upload) |
| `OCR_IN_PROGRESS` | 409 | re-run while an attempt is `processing` (idempotency guard) |
| `VERSION_CONFLICT` | 409 | `base_version` ≠ current `version` on correction |
| `INVALID_DOCUMENT_TYPE` | 422 | type outside PRD §16 allowlist (`pdf, jpg, jpeg, png, tiff`) — upgraded from current 400 to 422 for consistency (behavior change flagged in OCR-5 PR) |
| `INVALID_FILE_SIGNATURE` | 422 | magic bytes don't match declared type (malware-scan hook MVP) |
| `FILE_TOO_LARGE` | 422 | exceeds configured upload cap |
