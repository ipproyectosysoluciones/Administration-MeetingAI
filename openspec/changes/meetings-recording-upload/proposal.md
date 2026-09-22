# Proposal — meetings-recording-upload

## Problem statement

Meetings exist (meetings-crud merged). No way to attach recordings (audio of the assembly/session) yet. The next stage of the audio pipeline (transcription → minutes) needs a reliable recording channel with tenant isolation, audit and retryable background jobs. This change delivers upload and durable storage only.

## Why now

This is a prerequisite for the entire AI pipeline (PRD §Audio: Upload → Validate → Store → Queue → Transcribe → …). Without it the product cannot ingest any real audio.

## Scope (in)

- `StorageProvider` port + `LocalStorageProvider` implementation (tenant-scoped paths, streaming writes).
- `recordings` table + migration 0006: id, meeting_id FK, tenant_id, filename, content_type, size_bytes, sha256, storage_path, duration_seconds NULL, status (`stored`, `queued`, `transcribing`, `transcribed`, `failed`), uploaded_by, timestamps, deleted_at.
- `jobs` table (generic worker queue): id, type, payload JSONB, status, attempts, run_at, locked_by, timestamps. With SKIP LOCKED contract documented for the future worker.
- Endpoints:
  - POST `/api/v1/meetings/{id}/recordings` (multipart upload, single file; caller provides meeting_id).
  - GET `/api/v1/meetings/{meeting_id}/recordings` list
  - GET `/api/v1/recordings/{id}` metadata
  - GET `/api/v1/recordings/{id}/content` (streamed download)
  - DELETE `/api/v1/recordings/{id}` (soft delete)
- Validation: extension allowlist mp3/wav/m4a/ogg + magic byte sniffing → 415 UNSUPPORTED_MEDIA; 200MB default cap → 413 PAYLOAD_TOO_LARGE.
- Idempotency: same sha256 within same meeting returns existing row (200) vs creating duplicate.
- RBAC: new permissions `recording.upload/read/delete`.
- Audit on upload/download/delete + job.enqueued.

## Scope (out)

- Whisper/transcription, diarization, speaker diarization, AI processing, minutes.
- Resumable chunked upload (tus).
- ffprobe in-band validation (deferred to transcription worker).
- S3 provider.

## Decisions locked (from explore)

| # | Decision | Value |
|---|---|---|
| 1 | Size cap | 200MB default (config override) |
| 2 | `duration_seconds` | Set later by the transcription worker (ffprobe) |
| 3 | Download audit | Record `recording.download` (actor, tenant, recording_id) |

## Risks

- Abort/partials: temp-file-then-rename inside the local provider; cleanup on failure.
- Cross-tenant: meeting lookup enforces tenant before any recording access (404, not 403).
- Upload size: chunked read with mid-stream limit check; nginx proxy body-size must exceed the cap (set in nginx config during deploy; the change notes this).
- Worker lease: lock_by/expiry must be documented before workers can use jobs (test-plan notes this).

## Success criteria

- Meeting admin can upload recording; tenant B cannot see/download.
- Upload unchanged sha256 → returns existing (no duplicate file or job).
- Download serves correct bytes; audit records exactly once.
- Full CI green; no regression in existing suites.
