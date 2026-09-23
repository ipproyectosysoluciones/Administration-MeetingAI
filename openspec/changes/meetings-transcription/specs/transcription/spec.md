# Spec — meetings-transcription (delta specs)

Scope: OpenSpec delta for module `transcription`; conventions follow the same template as `recordings` and `meetings` (camelCase permission names, 404 cross-tenant, audit on every transition).

## Requirement R1 — Worker transcription of a queued recording

A `process_recording` job MUST be claimable by the transcription worker via `JobService.claim_next` (SKIP-LOCKED). When claimed, the worker streams the audio bytes from `StorageProvider.open_read(recording.storage_path)`, hands them to `SpeechToTextProvider.transcribe()` (default `FasterWhisperProvider`, configured by `WHISPER_MODEL`/`WHISPER_DEVICE`), and persistence a `Transcript` row with `status="draft"` before marking the job done.

Scenarios:
1. **Happy path** — pending job + valid recording → transcript row created (status=draft), job marked done, audit event `transcription.completed` exists.
2. **Provider produces no segments** → transcript.row persisted with empty text and 0 avg_confidence, job done (per AGENTS.md: incomplete output is still a reviewed draft).
3. **Job retry after worker crash** → a fail transitions job to pending with backoff; a subsequent claim finds it again.

## Requirement R2 — Idempotency

If a draft transcript already exists for the same `recording_id`, the worker MUST skip re-transcribing and complete the job (no duplicate transcript rows).

Scenarios:
1. Existing draft → worker completes job without calling the provider.
2. Two concurrent claims never produce two transcripts; unique constraint (unique index on recording_id where status='draft') enforces.

## Requirement R3 — Failure path

Provider/OOM/Option errors on the worker mark the job failed (status=failed via `JobService.fail`) and do NOT produce a transcript. Audit event `transcription.failed` recorded.

Scenarios:
1. Provider raises → job.status='failed'; no rows in transcripts.
2. Transient storage read error → job returns to pending via failure path.

## Requirement R4 — Read-only transcription API

- `GET /api/v1/transcriptions/{id}` — permission `transcription.read`; cross-tenant → 404.
- `GET /api/v1/recordings/{recording_id}/transcriptions` — list for a recording; same gate.

Scenarios:
1. Authorized role reads transcript → 200 with transcript payload (language, text, segments, segments JSONB, model_used, version, status).
2. Cross-tenant read → 404.
3. Without `transcription.read` → 403.

## Requirement R5 — Audit trail

Actions recorded as audit events with actor=worker (system) or actor=user as applicable:
- `transcription.started` (at claim)
- `transcription.completed` (after draft write)
- `transcription.failed` (after provider/storage failure)

Scenarios:
1. Worker claims job → `transcription.started` event written in same transaction.

## Requirement R6 — Upload enqueues transcription job

When `POST /api/v1/meetings/{id}/recordings` succeeds (a new row), the recordings service must enqueue a `process_recording` job via `JobService.enqueue` with payload `{"recording_id": "...", "meeting_id": "...", "tenant_id": "..."}` in the same transaction as the recording insert.

Scenarios:
1. Upload create → job row exists, status pending, same commit.
2. Idempotent upload (sha256 dedup) → NO new job created (existing job already pending/done).

## Data-shape invariants

- `transcriptions.tenant_id` copies `recordings.tenant_id` (no cross-tenant reads possible).
- `segments` JSONB item shape: `{start: float, end: float, text: string, speaker: null}`. v1 always `speaker: null` (no diarization).
- `status` CHECK: draft | final (final is reserved; nothing in this change writes final).
- `version` starts at 1; increments only under a later editing flow (not here).
