#!/usr/bin/env python3
"""E2E smoke: transcribe un wav sintético con faster-whisper real (issue #90).

No corre en CI. Uso local bajo demanda:

    cd apps/backend && .venv/bin/python ../../scripts/smoke_transcription.py

Requiere:
- ffmpeg (genera el wav sintético).
- faster-whisper instalado (worker image / venv).
- PostgreSQL con el esquema migrado (TEST_DATABASE_URL, default :5433).

Verifica el pipeline completo: wav -> storage -> job -> worker.run_once ->
faster-whisper -> Transcript(draft) -> job completed.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

BACKEND = Path(__file__).resolve().parents[1] / "apps" / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select  # noqa: E402

from app.modules.jobs.service import JobService  # noqa: E402
from app.modules.meetings.models import Meeting  # noqa: E402
from app.modules.organizations.models import Organization  # noqa: E402
from app.modules.recordings.models import Recording  # noqa: E402
from app.modules.recordings.providers import LocalStorageProvider  # noqa: E402
from app.modules.transcription import worker  # noqa: E402
from app.modules.transcription.faster_whisper_provider import (  # noqa: E402
    FasterWhisperProvider,
)
from app.modules.transcription.models import Transcript  # noqa: E402
from app.modules.users.models import User  # noqa: E402

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://reunionai:reunionai@localhost:5433/reunionai"
)


def _gen_sine_wav(path: Path, seconds: int = 3) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={seconds}",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


async def _store_wav(storage: LocalStorageProvider, key: str, wav: Path) -> tuple[str, int, str]:
    async def chunks():
        data = wav.read_bytes()
        yield data

    return await storage.store(key, chunks())


async def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="smoke-transcription-")
    wav = Path(tmpdir) / "tone.wav"
    _gen_sine_wav(wav)

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    storage = LocalStorageProvider(base_dir=tmpdir)

    async with factory() as session:
        org = Organization(
            name=f"Smoke {uuid.uuid4().hex[:6]}", slug=f"smoke-{uuid.uuid4().hex[:8]}"
        )
        session.add(org)
        await session.flush()
        user = User(
            email=f"smoke-{uuid.uuid4().hex[:8]}@test.dev", password_hash="x", full_name="Smoke"
        )
        session.add(user)
        await session.flush()
        meeting = Meeting(
            organization_id=org.id,
            title="Junta smoke",
            starts_at=datetime.now(UTC) + timedelta(days=1),
            ends_at=datetime.now(UTC) + timedelta(days=1, hours=1),
        )
        session.add(meeting)
        await session.flush()
        key = f"{org.id}/{meeting.id}/{uuid.uuid4()}"
        recording = Recording(
            meeting_id=meeting.id,
            tenant_id=org.id,
            filename="tone.wav",
            content_type="audio/wav",
            size_bytes=wav.stat().st_size,
            sha256="0" * 64,
            storage_path=key,
            status="queued",
            uploaded_by=user.id,
        )
        session.add(recording)
        await session.flush()

        await JobService().enqueue(
            session,
            type="process_recording",
            payload={
                "recording_id": str(recording.id),
                "meeting_id": str(meeting.id),
                "tenant_id": str(org.id),
            },
        )
        await session.commit()

        recording_id = recording.id

    await _store_wav(storage, key, wav)

    provider = FasterWhisperProvider()
    processed = await worker.run_once(
        factory,
        JobService(),
        provider,
        storage,
        worker_id="smoke-worker",
    )

    async with factory() as session:
        transcript = (
            await session.execute(select(Transcript).where(Transcript.recording_id == recording_id))
        ).scalar_one_or_none()

    await engine.dispose()

    if not processed:
        print("FAIL: no se reclamó ningún job")
        return 1
    if transcript is None:
        print("FAIL: no se creó Transcript")
        return 1
    if transcript.status != "draft":
        print(f"FAIL: status inesperado {transcript.status}")
        return 1

    print(f"PASS: transcript draft creado (id={transcript.id}, text_len={len(transcript.text)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
