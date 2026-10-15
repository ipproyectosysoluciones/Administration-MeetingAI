# Proposal — pipeline-ocr

Tracking: issue #167. This is **PR OCR-1 (docs-only)** of the 7-slice chained-PR plan; no implementation code changes in this slice.

## Problem statement

Meetings, recordings, transcriptions, and minutes exist, but the OCR pipeline mandated by PRD §16–18 is not implemented: `apps/backend/app/modules/ocr/` is a 48-line scaffold with **mock** `TesseractOCRProvider`/`OCRmyPDFProvider`, `document.*` permissions are referenced by the documents router but are **never seeded** in any migration, the `ocr_jobs` table listed in PRD §29 **does not exist** (migration 228004878c15 creates only `documents` + `document_versions`), and OCR runs synchronously inside the HTTP request instead of the async worker path of PRD §27. The PRD §16 pipeline — `Upload → Virus/Malware Scan → Document Validation → OCR → Text Extraction → Quality Check → Human Correction → Processed Document` — has no malware-scan hook, no quality gate, and no correction→version flow, and PRD §17 traceability (`original`, `ocr_result`, `corrected_text`, `final_document`, `versions`, `audit_history`) is only partially mapped. This change defines the full pipeline SDD so the remaining slices implement against locked contracts.

## Why now

Document management is one of the product pillars PRD §16–18 defines; minutes already landed (meetings-minutes change) and documents/OCR is its counterpart in the PRD pipeline. The repo already carries a documents CRUD/versioning scaffold with **wrong security wiring** (unseeded permissions) and a **sync OCR path inside the request handler** — every week this ships, the gap between the deployed contract and the PRD contract grows. Locking the SDD first, in slice-sized PRs, keeps each review ≤400 lines and lets provider work (OCR-3) proceed in parallel with REST design review.

## Scope (in)

Mapped 1:1 to the 7 slices of issue #167:

- **PR OCR-1 (docs, this change)**: the SDD artifact set under `openspec/changes/pipeline-ocr/` — proposal, design, data-model, API contract, delta specs, tasks, test plan.
- **PR OCR-2 (backend)**: **verify/extend** migration 228004878c15 — the `documents` and `document_versions` tables ALREADY exist, so no table creation for them; instead: an additive migration for the missing `ocr_jobs` table (per PRD §29), seeding `document.*` permissions (referenced but unseeded today) and `ocr.*` permissions + role matrix, following the 0007 transcriptions seed pattern.
- **PR OCR-3 (backend)**: real `OCRProvider` port per PRD §16 (`process()`, `extract_text()`, `confidence()`) with `TesseractOCRProvider` (pytesseract) for images and OCRmyPDF for PDFs, swapped per mime type; storage stays per-tenant under `storage/tenants/{tenant_id}/documents/` (PRD §18).
- **PR OCR-4 (backend)**: documents service pipeline — upload validation against PRD §16 formats, pluggable malware-scan validation hook (MVP: signature/magic-byte validation; ClamAV as documented follow-up), async job enqueue via `JobService.enqueue_ocr`, quality gate on `confidence()` with configurable threshold, human correction → `document_versions` (original never overwritten, PRD §17), `ocr.*` audit events.
- **PR OCR-5 (backend)**: REST `/api/v1/documents` + `/api/v1/ocr` surface — OCR re-run, versions, corrections — with 404 cross-tenant, 409 conflicts, 422 format errors, idempotent re-runs.
- **PR OCR-6 (backend)**: OCR worker consuming `process_ocr` jobs through the existing `JobService` SKIP-LOCKED claim pattern (states `queued/processing/completed/failed` per PRD §27), docker-compose worker service reusing the transcription worker topology.
- **PR OCR-7 (frontend)**: portal/admin documents UI — upload, processing states, quality-gate status, correction editor, version history.

## Scope (out)

- ClamAV integration (MVP ships the hook + signature validation only; ClamAV is a documented follow-up).
- Search/full-text indexing over extracted text (PRD search module; separate change).
- Wiring OCR output into minutes drafting (`ai_process_meeting` already accepts `document_ids`; the orchestration is a separate change).
- Configuring a non-Tesseract production OCR provider (the port makes it pluggable; adoption is an ops decision).

## Decisions locked

1. **No new `documents`/`document_versions` migration**: both tables already exist (228004878c15). Slice OCR-2 verifies the migration, adds the missing **`ocr_jobs`** table (PRD §29) as an additive migration, and seeds the missing **`document.*`** + new `ocr.*` permissions — never a destructive change (AGENTS.md rule 5).
2. **The original file is never overwritten** (PRD §17, verbatim: *"Nunca se deberá sobrescribir silenciosamente el documento original"*): OCR results and human corrections mutate only metadata/text columns and append `document_versions` rows; `file_path`/`sha256`/`file_size` of the original remain immutable after upload.
3. **OCR is async** (PRD §27): HTTP handlers enqueue `process_ocr` jobs via the existing `JobService`; a worker claims with SKIP-LOCKED and transitions through PRD §27 states (`queued/processing/completed/failed/cancelled`, mapped onto the existing jobs table `pending/running/done/failed` status names — mapping documented in design.md). OCR never runs inside the request handler (removes the current synchronous `trigger_ocr` behavior).
4. **Provider per PRD §16 interface**: the domain depends only on `OCRProvider` with `process()`, `extract_text()`, `confidence()`; `TesseractOCRProvider` (images) and an OCRmyPDF-backed implementation (PDFs) are the initial implementations (PRD §16: *"Implementación inicial: Tesseract / OCRmyPDF"*). Domain never imports provider SDKs (AGENTS.md rules 11–12).
5. **Malware scan is a pluggable validation step**: MVP implements a signature/magic-byte validation hook behind a `MalwareScanProvider`-style seam; ClamAV wiring is an explicit non-goal with a documented follow-up.
6. **Quality gate**: `confidence()` below a configurable threshold (default 0.60, env-configurable) routes the document to `needs_correction`/failed-quality state instead of silently completing; output is always a draft subject to human correction (AGENTS.md rules 6/18 analog).
7. **RBAC naming**: `document.*` (read/upload/download/update/delete — seeded in OCR-2) plus `ocr.run`, `ocr.read`, `ocr.correct` following the `transcription.*` / `minutes.*` conventions.
8. **Cross-tenant access yields 404**, never 403 — IDOR contract (skill: reunionai-multitenant-security).

## Risks

- **Migration chain divergence**: migration 228004878c15 uses a hash-style revision id and sits outside the numbered `0001…0010` chain; OCR-2 must declare `down_revision` explicitly and verify `alembic upgrade head` idempotency. Mitigation: migration tests mirror `test_migrations_0009.py`.
- **Permissions referenced but unseeded**: `document.upload/read/update/delete` are already used by the router with no seed — meaning current deployments rely on wildcard roles. OCR-2's seed may change effective access for existing tenants' roles. Mitigation: seed role matrix mirrors the existing `minutes.*` matrix; document the behavior change in the OCR-2 PR.
- **`ocr_jobs` vs generic `jobs` table duplication**: PRD §29 lists `ocr_jobs`, while `JobService` already persists `process_ocr` in the generic `jobs` table. Design decision (design.md §Data Changes): `ocr_jobs` is the **pipeline-state/OCR-result** record per document (attempts, confidence per attempt, error detail), while `jobs` remains the transport/dispatch queue. See "Decision needed" below if reviewers prefer one table.
- **Tesseract/OCRmyPDF binary dependencies** in worker image: adds system packages to Docker; contained to the worker image (OCR-6), not the API image.
- **Threshold false negatives**: a confidence gate that is too strict floods human correction. Mitigated by configurability + observing real `ocr_confidence` distributions before tightening.

## Decision needed

1. **`ocr_jobs` necessity**: keep `ocr_jobs` as a dedicated per-document OCR attempt/result table (PRD §29 lists it) **or** fold attempt history into `document_versions.metadata_json` + the generic `jobs` table. This SDD authors the PRD-faithful option (dedicated table, additive); reviewers may confirm or narrow in OCR-1 review.
2. **Confidence threshold default**: 0.60 is proposed; no production data exists yet to calibrate. Confirm default or defer to a settings table vs env var.

## Success criteria

- All 7 artifact files exist under `openspec/changes/pipeline-ocr/` and cite PRD §16–18/§27/§29/§33 contracts verbatim where they define formats, pipeline, provider interface, and non-overwrite guarantees.
- Every slice OCR-2…OCR-7 has tasks with acceptance criteria traceable to a numbered spec Requirement.
- The spec covers: tenant-scoped upload+validation, malware-scan hook, async job lifecycle, quality gate, correction→versioning (original never overwritten), RBAC gates, provider swappability, 404 cross-tenant, audit `ocr.*`/`document.*` events.
