# API contract — meetings-transcription

Base path: `/api/v1`. All endpoints require an authenticated user. Errors follow the `{code, message}` envelope.

## Endpoints

### GET /transcriptions/{id}

- **Permission:** `transcription.read`
- **Success 200:**
  ```json
  {
    "id": "",
    "recording_id": "",
    "meeting_id": "",
    "tenant_id": "",
    "language": "",
    "text": "",
    "segments": [],
    "avg_confidence": null,
    "model_used": "",
    "version": 1,
    "status": "draft",
    "error": null,
    "created_at": "",
    "updated_at": ""
  }
  ```
- **Errors:**
  - 401 unauthenticated
  - 403 PERMISSION_DENIED (user lacks `transcription.read`)
  - 404 TRANSCRIPTION_NOT_FOUND (cross-tenant or missing)

> **Cross-tenant gate:** If the requesting user's tenant does not match `transcript.tenant_id`, return 404 (not 403) to avoid leaking existence.

### GET /recordings/{recording_id}/transcriptions

- **Permission:** `transcription.read`
- **Query parameters (optional, platform non-bursting):**
  - `page` (default 1)
  - `page_size` (default 10, max 50)
- **Success 200:**
  ```json
  {
    "items": [
      {
        "id": "",
        "recording_id": "",
        "meeting_id": "",
        "tenant_id": "",
        "language": "",
        "text": "",
        "segments": [],
        "avg_confidence": null,
        "model_used": "",
        "version": 1,
        "status": "draft",
        "created_at": ""
      }
    ],
    "total": 0,
    "page": 1,
    "page_size": 10,
    "pages": 1
  }
  ```
- **Errors:**
  - 401 unauthenticated
  - 403 PERMISSION_DENIED (user lacks `transcription.read`)
  - 404 RECORDING_NOT_FOUND (cross-tenant or missing)

> **Cross-tenant gate:** If the requesting user's tenant does not match the recording's tenant, return 404. The list is empty rather than erroring when the recording has no transcripts.

## Error envelope

| Condition | HTTP | Code |
|-----------|------|------|
| Unauthenticated | 401 | UNAUTHENTICATED |
| Permission denied | 403 | PERMISSION_DENIED |
| Transcription not found (cross-tenant/missing) | 404 | TRANSCRIPTION_NOT_FOUND |
| Recording not found (cross-tenant/missing) | 404 | RECORDING_NOT_FOUND |
| Unsupported pagination | 400 | BAD_REQUEST |

## Invariants

- Every response follows the canonical error envelope `{code, message}`.
- No endpoint accepts or trusts a client-supplied `tenant_id`.
- Pagination limits `page_size` ≤ 50 to prevent bursty queries.
- `GET /transcriptions/{id}` returns 404 for cross-tenant access (not 403) to prevent tenant existence leakage.