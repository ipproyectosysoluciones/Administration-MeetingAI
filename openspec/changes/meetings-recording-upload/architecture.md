# Architecture — meetings-recording-upload

## Layout

```
apps/backend/app/modules/recordings/
  __init__.py
  models.py              # Recording, RecordingJob ORM rows
  service.py             # RecordingService (tenant-scoped CRUD+download metadata)
  schemas.py             # Pydantic in/out
  router.py              # REST endpoints
  providers.py           # StorageProvider protocol + LocalStorageProvider
apps/backend/app/modules/jobs/
  __init__.py
  models.py              # Job ORM (generic queue)
  service.py             # JobService.enqueue / dequeue / lifecycle helpers
```

No new routers for `jobs` — jobs are an internal transport, exposed under `/api/v1/recordings` only where needed for the current step (upload→enqueue).

## Dependency rules

- `recordings` → `jobs`, `meetings` (read-only FK + tenant propagation), `core`, `audit`
- `jobs` module is self-contained; recordings imports `jobs.service` (JobService)
- Forbidden: domain → sqlalchemy dialects, domain → aiofiles/fastapi internals beyond request/response streaming.

## Provider contract (StorageProvider)

```python
class StorageProvider(Protocol):
    async def upload(self, key: str, stream: AsyncIterator[bytes], *, size_limit: int | None) -> StoredObject
    async def download(self, key: str) -> AsyncIterator[bytes]
    async def delete(self, key: str) -> None       # idempotent
    async def exists(self, key: str) -> bool
```

- Path naming: `data/recordings/{tenant_id}/{meeting_id}/{recording_id}` (no user input in key).
- `LocalStorageProvider` implements atomic tmp+rename to avoid partial reads.

## Upload flow

1. Auth via `require_permission("recording.upload")` + tenant from JWT membership.
2. Meeting lookup via the same tenant (404 `MEETING_NOT_FOUND` if cross-tenant).
3. Streaming read with 1MB chunks while hashing (sha256) and enforcing the size cap with early exit.
4. Dedup per meeting+sha256 → return 200 with existing row.
5. Wrap in one transaction: `recordings` insert + `jobs` insert. On storage write failure, rollback.
6. Audit: `recording.upload`.

## Download flow

- GET /api/v1/recordings/{id}/content → RecordService.lookUp(tenant, id) → stream via provider; single audit event `recording.download`.

## Job lifecycle

- Statuses: `pending` → `running` → `done` | `failed (final)` ; `failed` with attempts < max_attempts → back to `pending` with `run_at` backoff.
- Worker claim uses `FOR UPDATE SKIP LOCKED` ordering by `run_at`.
- The change only enqueues jobs; the worker is a follow-up (transcription change).

## Error envelope

| Condition | HTTP | Code |
|-----------|------|------|
| Unsupported content type / extension | 415 | UNSUPPORTED_MEDIA |
| File too large | 413 | PAYLOAD_TOO_LARGE |
| Meeting not found (cross-tenant or missing) | 404 | MEETING_NOT_FOUND |
| Recording not found (cross-tenant or missing) | 404 | RECORDING_NOT_FOUND |
| Duplicate recording per meeting+sha256 | 200 (existing) | — (idempotent) |
| Missing permission | 403 | PERMISSION_DENIED |
