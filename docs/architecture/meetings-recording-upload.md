# Architecture notes — meetings-recording-upload

## Scope delivered
Upload, store, list, download, and soft-delete recordings for meetings.
Background job queue for the follow-on transcription change.

## Modules
- `apps/backend/app/modules/recordings/` — models, schemas, provider (`LocalStorageProvider`, StorageProvider protocol), service (tenant-scoped via parent meeting), router (upload/list/get/download/delete).
- `apps/backend/app/modules/jobs/service.py` — queue worker helper: enqueue, claim_next/claim_batch (FOR UPDATE SKIP LOCKED), complete/fail w/ exponential backoff. Jobs exist as `process_recording` placeholders; worker lands next iteration.

## API
- POST /api/v1/meetings/{id}/recordings (multipart; 200MB cap, mp3/wav/m4a/ogg, sha256 idempotent per meeting+checksum)
- GET /api/v1/meetings/{id}/recordings
- GET /api/v1/recordings/{id}, GET .../content, DELETE /api/v1/recordings/{id} (soft)
- Errors: 413/415/404/403/422 per contract; cross-tenant 404.

## Isolation
recordings.tenant_id tracks the meeting's org; deleting messages the parent meeting but storage keys embed tenant path so cross-tenant reads are structurally impossible.

## Storage
LocalStorageProvider stores under data/recordings/{tenant}/{meeting}/{recording} (atomic tmp+rename). Interface allows switching to S3 later without touching the domain.

## Tests
- Backend: 232 passing (jobs lifecycle, upload/download soft-delete, dedup by sha256, cross-tenant 404).
- Frontend: 17 passing on new recordings UI inside meeting detail.

## Next change
`meetings-transcription` — Whisper processing, diarization, minutes-writer.
