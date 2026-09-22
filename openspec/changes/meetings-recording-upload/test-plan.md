# Test plan — meetings-recording-upload

Conventions: TDD strict; backend via apps/backend/.venv/bin/python -m pytest against the Docker test Postgres; integration fixtures mirror existing modules; production slices ≤400 lines.

## Slices

| Slice | Scope | Est. prod lines |
|-------|---|---|
| S1 | Migration 0006 (recordings + jobs) + seed recording.* permissions + role mapping | ~180 |
| S2 | StorageProvider protocol + LocalStorageProvider + tests | ~180 |
| S3 | Recordings module (service + router: upload/list/get/content/delete) + jobs service | ~390 |

## Test matrix

**Unit** (no external state):
- MIME/extension allowlist (mp3/wav/m4a/ogg pass; others → 415).
- Magic-byte sniffing spot checks.
- FSM transition rules for status on upload/update/delete (no backward moves).
- StorageProvider path naming: tenant → meeting → recording (no user input).

**Integration** (Postgres test DB + LocalStorageProvider tmp fixtures):
- Upload happy path → file exists under the scoped key, recording saved, job queued, audit recorded.
- Idempotent sha256 dedup (same file → 200 with existing row; no second file/job).
- Oversize file → 413 mid-stream; no orphaned file on disk.
- Unsupported media → 415.
- Cross-tenant: recording read/creator of another tenant → 404 for list/get/content/delete.
- Permission gating: without upload/read/delete → 403 for each endpoint.
- Download returns bytes + audit `recording.download`; no download of deleted file (404).
- Delete = soft only; second delete is no-op but still 204.

**Migration tests:** schema introspection (FKs, indexes), job status check constraint, upgrades/downgrades idempotent.

## Gates before merge

- Tests green (existing suite plus new ones).
- ruff + mypy clean.
- Head commit within 400 production lines per slice.
