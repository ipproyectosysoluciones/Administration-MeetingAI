# Recordings Specification

## Purpose

Provide a reliable recording upload and storage channel for the meeting audio pipeline with tenant isolation, SHA-256 dedup, audit trail, and retryable background job queue integration. This is the prerequisite for transcription → minutes processing.

## Requirements

### Requirement: R1 — Upload flow (POST multipart)

The system MUST accept a multipart POST `/api/v1/meetings/{id}/recordings` with a single audio file (mp3/wav/m4a/ogg, max 200MB, magic byte sniffing). On success, create a recording row in the `recordings` table with file stored via `LocalStorageProvider` (tenant-scoped path), queue a background job, and return 201. If the SHA-256 of the file matches an existing recording row within the same meeting, return 200 with the existing row (dedup, no duplicate file or job). Cross-tenant access must return 404 (`RECORDING_NOT_FOUND`). Unsupported media type must return 415; payload exceeding the size cap must return 413.

**Scenarios:**

1. **Happy path upload** — GIVEN a valid multipart request with an mp3 file < 200MB and an auth token for meeting admin of the target meeting WHEN POST `/api/v1/meetings/{id}/recordings` is called THEN the system creates a `recordings` row with status `stored`, stores the file under `local_storage/{tenant_id}/{meeting_id}/{filename}`, queues a job with type `process_recording`, and returns 201 with the recording metadata.

2. **SHA-256 dedup — existing recording** — GIVEN a file with the same SHA-256 as an existing recording row for the same meeting WHEN POST `/api/v1/meetings/{id}/recordings` is called THEN the system returns 200 with the existing recording row and does not create a duplicate file or enqueue a new job.

3. **SHA-256 dedup — different meeting** — GIVEN a file with the same SHA-256 as a recording in a different meeting WHEN POST `/api/v1/meetings/{id}/recordings` is called THEN a new recording row is created (dedup is per-meeting, not global).

4. **Tenant isolation** — GIVEN an auth token for a tenant B user WHEN POST `/api/v1/meetings/{id}/recordings` is called for a meeting belonging to tenant A THEN the system returns 404 (`RECORDING_NOT_FOUND`) — tenant B cannot create recordings in tenant A's meetings.

5. **415 Unsupported media type** — GIVEN a multipart request with a file having an unsupported extension (e.g., `.pdf`) OR passing magic byte sniffing WHEN POST `/api/v1/meetings/{id}/recordings` is called THEN the system returns 415 with error code `UNSUPPORTED_MEDIA`.

6. **413 Payload too large** — GIVEN a multipart request with a file exceeding 200MB WHEN POST `/api/v1/meetings/{id}/recordings` is called THEN the system returns 413 with error code `PAYLOAD_TOO_LARGE`.

---

### Requirement: R2 — List/Get + download (audit)

The system MUST support GET `/api/v1/meetings/{meeting_id}/recordings` with pagination (`page`, `page_size`) and auth read permission, returning only the caller's tenant recordings. GET `/api/v1/recordings/{id}` must return metadata. Streamed download via GET `/api/v1/recordings/{id}/content` must serve the stored file. Each download operation must record an audit event (`recording.download`: actor, tenant, recording_id).

**Scenarios:**

1. **List recordings for a meeting** — GIVEN an auth token for a meeting admin WHEN GET `/api/v1/meetings/{meeting_id}/recordings` is called THEN the system returns 200 with a paginated list of recordings for that meeting, each including id, filename, size_bytes, status, created_at, and tenant_id.

2. **Pagination** — GIVEN multiple recordings across pages WHEN GET `/api/v1/meetings/{meeting_id}/recordings?page=2&page_size=10` is called THEN the system returns the second page of results with proper `next_page` cursor or offset.

3. **Cross-tenant list returns 404** — GIVEN an auth token for a tenant B user WHEN GET `/api/v1/meetings/{meeting_id}/recordings` is called for a tenant A meeting THEN the system returns 404 (`RECORDING_NOT_FOUND`).

4. **Get recording metadata** — GIVEN an auth token and a recording id WHEN GET `/api/v1/recordings/{id}` is called THEN the system returns 200 with the recording metadata (id, meeting_id, tenant_id, filename, content_type, size_bytes, sha256, storage_path, duration_seconds, status, uploaded_by, timestamps).

5. **Streamed download** — GIVEN an auth token with `recording.read` permission and an existing recording WHEN GET `/api/v1/recordings/{id}/content` is called THEN the system streams the file content with proper `Content-Type` and `Content-Disposition` headers and records an audit event `recording.download` (actor, tenant_id, recording_id).

6. **Download without permission returns 403** — GIVEN an auth token without `recording.read` permission WHEN GET `/api/v1/recordings/{id}/content` is called THEN the system returns 403.

---

### Requirement: R3 — Delete (soft delete + audit)

The system MUST support DELETE `/api/v1/recordings/{id}` with `recording.delete` permission. Deletion is soft: set `deleted_at` timestamp and change `status` to `deleted`. Record an audit event (`recording.delete`: actor, tenant, recording_id). The row must remain in the database.

**Scenarios:**

1. **Soft delete recording** — GIVEN an auth token with `recording.delete` permission and an existing recording WHEN DELETE `/api/v1/recordings/{id}` is called THEN the system sets `deleted_at = NOW()`, changes `status` to `deleted`, returns 204, and records an audit event `recording.delete` (actor, tenant_id, recording_id).

2. **Soft delete already deleted recording** — GIVEN an auth token with `recording.delete` permission and a recording already soft-deleted WHEN DELETE `/api/v1/recordings/{id}` is called THEN the system returns 204 (idempotent, no-op, no additional audit event) or 200 with no-body; consistent behavior documented.

3. **Cross-tenant delete returns 404** — GIVEN an auth token for a tenant B user WHEN DELETE `/api/v1/recordings/{id}` is called for a recording belonging to tenant A THEN the system returns 404 (`RECORDING_NOT_FOUND`).

4. **Delete without permission returns 403** — GIVEN an auth token without `recording.delete` permission WHEN DELETE `/api/v1/recordings/{id}` is called THEN the system returns 403.

---

### Requirement: R4 — RBAC matrix (recording.upload/read/delete)

The system MUST enforce the following permissions for recording operations:

- `recording.upload` — required for POST `/api/v1/meetings/{id}/recordings`. Granted to: meeting admin role, organization owner.
- `recording.read` — required for GET `/api/v1/recordings/{id}` and GET `/api/v1/recordings/{id}/content`. Granted to: meeting admin, secretary, president, board_member (read-own only for minimal roles).
- `recording.delete` — required for DELETE `/api/v1/recordings/{id}`. Granted to: meeting admin, organization owner.

**Scenarios:**

1. **Upload with recording.upload permission** — GIVEN an auth token with `recording.upload` WHEN POST `/api/v1/meetings/{id}/recordings` is called THEN the system accepts the upload and returns 201.

2. **Upload without recording.upload permission** — GIVEN an auth token without `recording.upload` WHEN POST `/api/v1/meetings/{id}/recordings` is called THEN the system returns 403.

3. **Read with recording.read permission** — GIVEN an auth token with `recording.read` WHEN GET `/api/v1/recordings/{id}` is called THEN the system returns 200 with metadata.

4. **Read without recording.read permission** — GIVEN an auth token without `recording.read` WHEN GET `/api/v1/recordings/{id}` is called THEN the system returns 403.

5. **Delete with recording.delete permission** — GIVEN an auth token with `recording.delete` WHEN DELETE `/api/v1/recordings/{id}` is called THEN the system performs soft delete and returns 204.

6. **Delete without recording.delete permission** — GIVEN an auth token without `recording.delete` WHEN DELETE `/api/v1/recordings/{id}` is called THEN the system returns 403.

---

### Requirement: R5 — Job queue semantics

The system MUST use the `jobs` table as a generic worker queue. When a recording is inserted, a job MUST be enqueued in the same transaction. Job statuses: `pending`, `running`, `done`, `failed`. The worker contract uses `SKIP LOCKED` to dequeue jobs. Each job has: id, type, payload JSONB, status, attempts, run_at, locked_by, timestamps.

**Scenarios:**

1. **Job enqueued in same transaction as recording insert** — GIVEN a valid upload request WHEN the `recordings` row is inserted THEN a corresponding row is inserted into the `jobs` table with type `process_recording`, status `pending`, attempts 0, and the recording's id as part of the payload, all within the same database transaction.

2. **Job status: pending** — GIVEN a newly enqueued job WHEN the worker event loop starts THEN the job status is `pending`.

3. **Worker dequeues with SKIP LOCKED** — GIVEN multiple worker instances polling `SELECT * FROM jobs WHERE status = 'pending' FOR UPDATE SKIP LOCKED` THEN each worker picks a distinct job, updates status to `running` and sets `locked_by`, and processes the recording (e.g., ffprobe for duration, enqueue Whisper transcription).

4. **Job retries on failure** — GIVEN a job that finishes with an error WHEN the worker updates the job status to `failed` and increments `attempts` THEN if `attempts < max_attempts`, the job status is reset to `pending`; otherwise it stays `failed` with a `failed_at` timestamp.

5. **Job: done completes processing** — GIVEN a job that successfully processes the recording WHEN the worker updates the job status to `done` and sets `completed_at` THEN the recording row `status` is updated from `queued` to `transcribed` (or appropriate next state), and `duration_seconds` is populated from ffprobe output.

6. **Job payload includes recording id** — GIVEN a job for processing a recording WHEN the job is created THEN the payload JSONB includes at minimum `recording_id` and `meeting_id` for the worker to look up the recording row.

---

## Open Questions

- None.