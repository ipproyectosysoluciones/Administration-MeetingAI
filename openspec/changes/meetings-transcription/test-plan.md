# Test plan — meetings-transcription

Conventions: TDD strict; backend via apps/backend/.venv/bin/python -m pytest against the Docker test Postgres; integration fixtures mirror existing modules; production slices ≤400 lines.

## Slices

| Slice | Scope | Est. prod lines |
|-------|---|---|
| T1 | Migration 0007 (transcripts + permission seeds + role matrix) + smoke count/idempotency | ≤400 |
| T2 | SpeechToTextProvider protocol + FasterWhisperProvider mock + unit test | ≤400 |
| T3 | Worker + service integration (claim → transcribe → write transcript + audit) | ≤400 |
| T4 | API routers + read-only permission enforcement (GET /transcriptions/{id}, GET /recordings/{id}/transcriptions) | ≤400 |

## Test matrix

### Slice T1 — Migration + seeds

**Unit** (no external state):
- Migration 0007 DDL asserts: PK, FKs to recordings/meetings/organizations, `status` CHECK (draft|final), `segments` JSONB shape, unique index on `(recording_id) WHERE status='draft'`.
- Permission seeds: 2 permissions (`transcription.read`, `transcription.create`) exist after migrate.
- Role matrix: after seed, `super_admin` and `org_admin` have both transcription perms; `secretary` has read+create; `president` has read only; `board_member` has none.
- Idempotency: `ON CONFLICT (name) DO NOTHING` on permission insert; `ON CONFLICT (role_id, permission_id) DO NOTHING` on role-perm insert.

**Integration** (Postgres test DB):
- Schema introspection: FKs resolved, indexes exist, CHECK constraints pass.
- Seed verification: query role_permissions and verify each role has exactly the expected perm set (mirrors `test_migrations.py` pattern).
- Unique constraint: insert two draft transcripts for same recording_id → unique violation on `ux_transcripts_recording_draft`.

### Slice T2 — Provider port + whisper + unit test

**Unit** (no external state, no downloads):
- `SpeechToTextProvider.protocol` is importable and has `transcribe()` method.
- `FasterWhisperProvider` constructs with `model_name="small"`, `device="auto"` from env.
- Mock `faster-whisper` model: provide a small synthetic WAV header (44 bytes) that `transcribe()` consumes; assert result has `text`, `segments`, `avg_confidence`.
- Deterministic audio bytes: generate 1-second silent PCM bytes (known pattern) so transcription output is reproducible.
- Provider raises on invalid input → unit asserts exception propagates.

**Integration** (optional, small audio):
- Real faster-whisper on a ~1s generated WAV; assert segments non-empty when audio has content.
- Assert `model_used` field in transcript row matches `WHISPER_MODEL` env.

### Slice T3 — Worker + service + integration

**Unit** (mocked provider):
- `TranscriptionService.transcribe_recording()` calls `provider.transcribe()` and persists transcript.
- Service raises on provider error; unit asserts `job_service.fail()` is called and no transcript row is written.
- Idempotency check: service skips if draft transcript already exists for recording_id.

**Integration** (Postgres test DB + mocked provider):
- Worker claims a `process_recording` job via `JobService.claim_next` (SKIP-LOCKED).
- Worker streams audio from `StorageProvider.open_read()` and calls provider.
- After successful transcription: transcript row exists with `status="draft"`, job marked `done`, audit event `transcription.completed` recorded.
- Provider empty-segments scenario: transcript row written with empty text, 0 avg_confidence, job done (idempotent per spec R2).
- Provider failure scenario: job marked `failed`, no transcript row, audit event `transcription.failed` recorded.
- Concurrent claims: second claim finds existing draft → job completed without re-transcribing.

### Slice T4 — API routers + read-only permission enforcement

**Unit** (no DB):
- Router dependencies inject `transcription.read` permission check.
- Missing permission → 403 enforced independent of DB state.

**Integration** (Postgres test DB + auth):
- Authorized super_admin/org_admin reads `GET /transcriptions/{id}` → 200 with transcript payload (language, text, segments JSONB, model_used, version, status).
- Cross-tenant read of `GET /transcriptions/{id}` → 404 (not 403) — user cannot tell if transcript exists or not.
- Authorized read of `GET /recordings/{recording_id}/transcriptions` → 200 list (may be empty).
- Cross-tenant list → 404 if tenant mismatch, or 200 empty list if recording has no transcripts but tenant matches.
- Without `transcription.read` → 403 on both endpoints.
- Pagination: `page` and `page_size` parameters respected; `page_size` > 50 → 400.

## Gates before merge

- Tests green (existing 232-pass suite unchanged + new transcription tests).
- ruff + mypy clean per slice.
- Each slice ≤400 production lines.
- Migration 0007 runs upgrade/downgrade idempotently.
- Unique constraint `ux_transcripts_recording_draft` enforced in integration test.
- Cross-tenant 404 (not 403) verified for both API endpoints.