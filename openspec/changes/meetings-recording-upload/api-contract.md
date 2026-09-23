# API contract — meetings-recording-upload

Base path: `/api/v1`. All endpoints require an authenticated user. Errors follow the `{code, message}` envelope.

## Endpoints

### POST /meetings/{meeting_id}/recordings

Upload multipart. Form field `file` required.

- **Permission:** `recording.upload`
- **Success 201** (new recording):
  ```json
  { "id": "", "meeting_id": "", "filename": "", "size_bytes": 0, "sha256": "", "status": "queued", "created_at": "..." }
  ```
- **Success 200** (idempotent dedup): same body as 201 (existing row returned).
- **Errors:** 401 unauthenticated · 403 PERMISSION_DENIED · 404 MEETING_NOT_FOUND (cross-tenant/missing) · 413 PAYLOAD_TOO_LARGE · 415 UNSUPPORTED_MEDIA.

### GET /meetings/{meeting_id}/recordings

- **Permission:** `recording.read`
- **Success 200:**
  ```json
  { "items": [ { "id": "...", "filename": "...", "size_bytes": 0, "status": "queued", "created_at": "..." } ], "total": 0, "page": 1, "page_size": 20, "pages": 1 }
  ```
- **Errors:** 401 · 403 · 404 MEETING_NOT_FOUND.

### GET /recordings/{recording_id}

- **Permission:** `recording.read`
- **Success 200:** full metadata (incl. tenant gate via meeting).
- **Errors:** 401 · 403 · 404 RECORDING_NOT_FOUND.

### GET /recordings/{recording_id}/content

- **Permission:** `recording.read`
- Streams the original file. Sets `Content-Type: audio/mpeg|audio/wav|audio/mp4|audio/ogg` per extension.
- Records `recording.download` audit event.
- **Errors:** 401 · 403 · 404 RECORDING_NOT_FOUND.

### DELETE /recordings/{recording_id}

- **Permission:** `recording.delete`
- **Success 204** (soft-delete; subsequent calls also return 204 without a new audit event).
- **Errors:** 401 · 403 · 404 RECORDING_NOT_FOUND.

## Invariants

- Every mutation records exactly one audit event with actor+tenant+resource.
- Every response follows the canonical error envelope `{code, message}`.
- No endpoint accepts or trusts a client-supplied `tenant_id`.
