# Tasks — pipeline-ocr

Convenciones: TDD estricto (RED → GREEN → REFACTOR) per `reunionai-tdd-standards`; cada slice ≤400 líneas de producción; Conventional Commits; cada PR cierra contra issue #167; no merge si CI no está green. PR numbers assigned when slices are opened.

| Task | Slice (PR) | Tipo | Alcance | Acceptance |
|---|---|---|---|---|
| OCR-100 | OCR-1 (docs) | docs | This SDD artifact set under `openspec/changes/pipeline-ocr/` (7 files) | artifacts cite PRD §16–18/§27/§29 verbatim; requirements R1–R8 traceable to tasks |
| OCR-200 | OCR-2 (backend) | feat | Additive migration: `ocr_jobs` table (D1) + seed `document.*` and `ocr.*` permissions/role matrix (D2), 0007 pattern | `alembic upgrade head` idempotent; migration tests (columns, CHECKs, seed counts, idempotency) green |
| OCR-201 | OCR-2 (backend) | feat | RBAC wiring verification: `require_permission` aliases on documents router resolve to seeded permissions | integration: role-matrix cases (R6 scenarios) green |
| OCR-300 | OCR-3 (backend) | feat | Real `OCRProvider` port per PRD §16 (`process/extract_text/confidence`) + `TesseractOCRProvider` (pytesseract) for images + OCRmyPDF impl for PDFs; mime routing; fakes kept for tests | unit: fake determinism, mime routing, no provider SDK imports in domain (R7) |
| OCR-301 | OCR-3 (backend) | feat | `MalwareScanHook` port + magic-byte signature validator (MVP) | unit: signature table for 5 formats × match/mismatch/corrupt (R2) |
| OCR-400 | OCR-4 (backend) | feat | `OCRService.run_pipeline`: scan → validate → OCR → extract → quality gate (`OCR_CONFIDENCE_THRESHOLD`) → persist; `ocr_jobs` attempt bookkeeping | unit: boundary/below/above threshold (R4); failed attempts preserved (R3) |
| OCR-401 | OCR-4 (backend) | feat | Human correction flow → append `document_versions`, bump version, original immutable | unit + integration: R5 scenarios incl. stale `base_version` 409, v1 byte-identical |
| OCR-402 | OCR-4 (backend) | feat | Upload path: enqueue-only (remove sync OCR), audit events `ocr.*` | integration: R1 scenarios 1–4 |
| OCR-500 | OCR-5 (backend) | feat | REST deltas: `POST /documents/{id}/ocr` → 202 `ocr.run` async re-run; `POST /documents/{id}/corrections`; `GET /ocr/jobs`, `GET /ocr/jobs/{id}` (`ocr.read`) | integration: happy paths, 404 cross-tenant, 403 RBAC, 409 in-progress/version-conflict, 422 formats |
| OCR-501 | OCR-5 (backend) | fix | `INVALID_DOCUMENT_TYPE` 400→422 alignment (flagged contract change) | integration error-shape tests green |
| OCR-600 | OCR-6 (backend) | feat | `OCRWorker` handler on `process_ocr` (SKIP-LOCKED pattern from `TranscriptionWorker`) + docker-compose worker service + `.env.example` (`OCR_CONFIDENCE_THRESHOLD`, storage base) | integration: enqueue→worker→completed with job-service lifecycle; compose config validates |
| OCR-700 | OCR-7 (frontend) | feat | `lib/documents.ts` client, `DocumentsPanel` (upload + processing states + quality-failed flag), `CorrectionEditor`, version history view, `/documents` portal page | `npm run build` + vitest green; UI distinguishes draft/corrected states |
