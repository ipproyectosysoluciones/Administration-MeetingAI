# Proposal — meetings-transcription

## Problem statement

Recordings exist (recordings-upload merged) and a generic worker queue exists (jobs table + JobService with SKIP-LOCKED claims). The pipeline `Upload → … → Transcribe → Draft` still has no transcription step: job rows are enqueued but no worker consumes them, and no transcript artifact exists. This change implements the STT step behind the provider contract the PRD requires.

## Why now

It's the first real AI-adjacent workload in the platform, and the only bridge between stored audio and the future minutes/review stages. Deferring it further blocks any draft generation in the product.

## Scope (in)

- **Migration 0007**: `transcriptions` table (`recording_id` FK, `meeting_id`, `tenant_id`, `language`, `text`, `segments` JSONB, `avg_confidence`, `model_used`, `version`, `status` draft|final, `error`, `created_by_job_id`, timestamps) + `transcription.*` permission seeds (`transcription.read`, `transcription.create`).
- **`SpeechToTextProvider` protocol + `FasterWhisperProvider`** (faster-whisper, configurable via `WHISPER_MODEL=small`, `WHISPER_DEVICE=auto`).
- **`transcription/worker.py`**: standalone loop `python -m app.modules.transcription.worker` claiming `process_recording` jobs (existing `JobService.claim_next`) and running transcription; skipped if a `draft` transcript for the recording already exists (idempotency).
- Upload hook: `recordings.upload` enqueues `process_recording` job (payload: recording_id, meeting_id, tenant_id).
- Read-only API: `GET /api/v1/transcriptions/{id}` and `GET /api/v1/recordings/{id}/transcriptions` (both `transcription.read`).
- Audit: `transcription.started/completed/failed` with actor=system worker, recording/tenant IDs.
- Docker: `worker` service using the backend image with a different entrypoint (no new Dockerfile needed; image already bundles the requirements).

## Scope (out)

- AI minute drafting/extraction (follow-up: `meetings-minute-draft`).
- Diarization (segments have speaker=null in v1).
- Approval/promotion (`draft → final` flow stays for the later reviews change).
- S3 providers, GPU provisioning, model benchmarks.

## Decisions locked (user-approved during explore)

1. AI minute draft out of scope — separate change.
2. WHISPER_MODEL=small default (CPU); WHISPER_DEVICE=auto; prod override large-v3 allowed.
3. Diarization omitted for v1 (speaker=null).
4. Only draft transcripts exist in this change; finalization lands later.
5. Model downloads at image build time; volume override optional via env.

## Risks

- faster-whisper native deps (ctranslate2, ffmpeg) must be present in the backend/worker Dockerfile; `pip install faster-whisper` must resolve.
- Worker could be slow on CPU for long audio: admitted via run_at backoff + job retry policy; document.
- No GPU assumptions in tests: provider is faked/mocked in unit tests; integration uses a small synthetic audio.
- Tenant gating flows through recording→meeting→tenant chain; worker verifies row-tenant before producing output.

## Success criteria

- Uploading a recording enqueues a job; worker writes a draft transcript and marks the job done; failing transcription marks failed and makes the row retryable.
- API returns draft transcripts with correct RBAC/tenant checks; cross-tenant access yields 404.
- Full test verification green (existing 232-pass suite unchanged + new transcription tests).
