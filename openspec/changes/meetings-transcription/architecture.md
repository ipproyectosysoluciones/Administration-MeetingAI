# Architecture — meetings-transcription

## Layout

```
apps/backend/app/modules/transcription/
  __init__.py
  models.py              # Transcript ORM row + status enum
  services.py            # TranscriptionService (orchestrates provider + DB)
  provider/              # SpeechToTextProvider protocol + FasterWhisperProvider
    __init__.py
    protocol.py           # Protocol definition
    faster_whisper.py     # concrete implementation
  worker.py              # Standalone loop: claim process_recording jobs, transcribe, write transcript
  schemas.py             # Pydantic in/out for API responses
  router.py              # REST endpoints: GET /transcriptions/{id}, GET /recordings/{id}/transcriptions
```

## Dependency rules

- `transcription` → `recordings`, `meetings` (read-only FK + tenant propagation), `jobs`, `core`, `audit`
- No domain → sqlalchemy dialects, no domain → aiofiles/fastapi internals beyond request/response.
- Provider protocol is the only abstraction over faster-whisper; concrete implementation may import ctranslate2/ffmpeg.

## Provider contract (SpeechToTextProvider)

```python
class SpeechToTextProvider(Protocol):
    async def transcribe(self, audio_bytes: bytes, language: str | None = None) -> TranscriptionResult:
        ...
```

```python
class TranscriptionResult:
    text: str
    segments: list[Segment]  # {start: float, end: float, text: str, speaker: null}
    avg_confidence: float | None
```

- `FasterWhisperProvider` implements the protocol using `faster-whisper` with config from `WHISPER_MODEL` (default `small`) and `WHISPER_DEVICE` (default `auto`).
- Provider is injected via dependency injection; tests mock the protocol.

## Worker bootstrap

`transcription/worker.py` — standalone entrypoint:

```python
async def transcription_worker_loop(session_factory, job_service, provider, storage):
    while True:
        job = await job_service.claim_next("process_recording", session_factory)
        if job is None:
            await asyncio.sleep(2)  # polling interval
            continue

        recording_id = job.payload["recording_id"]
        # Idempotency: skip if draft transcript already exists
        async with session_factory() as session:
            existing = await session.get(Transcript, recording_id)
            if existing and existing.status == "draft":
                await job_service.mark_done(job)
                continue

        # Stream audio from storage
        recording = await ...  # look up recording via recording_id
        audio_bytes = b"".join(
            await storage.open_read(recording.storage_path)
        )

        try:
            result = await provider.transcribe(audio_bytes)
            transcript = Transcript(
                id=recording_id,  # or generate new UUID
                recording_id=recording_id,
                meeting_id=job.payload["meeting_id"],
                tenant_id=job.payload["tenant_id"],
                language=result.language or "es",
                text=result.text,
                segments=result.segments,
                avg_confidence=result.avg_confidence,
                status="draft",
                version=1,
                error=None,
            )
            async with session_factory() as session:
                session.add(transcript)
                await session.commit()
            await job_service.mark_done(job)
            # Audit: transcription.completed
        except Exception as e:
            await job_service.fail(job)
            # Audit: transcription.failed

# Entry point: python -m app.modules.transcription.worker
```

## StorageProvider usage pattern (from recordings.providers)

Refer to `apps/backend/app/modules/recordings/providers.py` for the protocol:

```python
class StorageProvider(Protocol):
    async def open_read(self, key: str) -> AsyncIterator[bytes]:
        ...
    async def upload(self, key: str, stream: AsyncIterator[bytes], *, size_limit: int | None) -> StoredObject:
        ...
```

- Path naming: `data/recordings/{tenant_id}/{meeting_id}/{recording_id}`.
- `LocalStorageProvider` implements atomic tmp+rename to avoid partial reads.
- Worker uses `open_read` to stream audio bytes for transcription; original file is never overwritten.

## Transcript ORM model

Key fields (see data-model.md for full DDL):

- `id`: UUID PK
- `recording_id`: UUID FK → recordings(id), unique where status='draft'
- `meeting_id`: UUID FK → meetings(id)
- `tenant_id`: UUID FK → organizations(id)
- `language`: text (e.g. "es", "en")
- `text`: TEXT (full transcription)
- `segments`: JSONB [{start, end, text, speaker}]
- `avg_confidence`: FLOAT NULL
- `model_used`: text (e.g. "small", "large-v3")
- `version`: INTEGER DEFAULT 1
- `status`: text CHECK (status IN ('draft', 'final')) DEFAULT 'draft'
- `error`: TEXT NULL
- `created_by_job_id`: UUID FK → jobs(id) NULL
- timestamps

Unique constraint: `(recording_id, status='draft')` prevents duplicate draft transcripts.