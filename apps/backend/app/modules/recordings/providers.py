"""StorageProvider contract (protocol) + LocalStorageProvider (TASK-251).

Domain-neutral port: callers depend only on this interface, so an S3/object-store
backend can be swapped in later without touching business logic.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import UUID


class StoredObject(Protocol):
    key: str
    size_bytes: int
    sha256: str


class StorageProvider(Protocol):
    async def store(self, key: str, stream: AsyncIterator[bytes]) -> tuple[str, int, str]:
        """Write stream under key. Returns (key, size_bytes, sha256)."""
        ...

    async def open_read(self, key: str) -> BinaryIO: ...

    async def exists(self, key: str) -> bool: ...


def make_recording_key(tenant_id: UUID, meeting_id: UUID, recording_id: uuid.UUID) -> str:
    """Key convention: {tenant_id}/{meeting_id}/{recording_id} (no user input)."""
    return str(Path(str(tenant_id), str(meeting_id), str(recording_id)))


class LocalStorageProvider(StorageProvider):
    """Stores blobs under a local directory (default ./data/recordings)."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or os.environ.get("STORAGE_BASE", "data/recordings"))

    def _abs(self, key: str) -> Path:
        return self.base_dir / key

    async def store(self, key: str, stream: AsyncIterator[bytes]) -> tuple[str, int, str]:
        target = self._abs(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_name = tempfile.mkstemp(prefix=target.name, dir=target.parent)

        hasher = hashlib.sha256()
        size = 0
        try:
            with os.fdopen(tmp_fd, "wb") as tmp:
                async for chunk in stream:
                    tmp.write(chunk)
                    size += len(chunk)
                    hasher.update(chunk)
        except BaseException:
            await asyncio.to_thread(os.unlink, tmp_name)
            raise

        os.replace(tmp_name, target)
        return key, size, hasher.hexdigest()

    async def open_read(self, key: str) -> BinaryIO:
        return open(self._abs(key), "rb")

    async def exists(self, key: str) -> bool:
        return self._abs(key).exists()
