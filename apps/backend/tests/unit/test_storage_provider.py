"""Unit tests for StorageProvider/LocalStorageProvider (TASK-251)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.modules.recordings.providers import (
    LocalStorageProvider,
    make_recording_key,
)


async def _aiter(chunks: list[bytes]) -> AsyncIterator[bytes]:
    for c in chunks:
        await asyncio.sleep(0)
        yield c


def test_recording_key_format():
    from uuid import uuid4

    t = uuid4()
    m = uuid4()
    r = uuid4()
    key = make_recording_key(t, m, r)
    assert key == f"{t}/{m}/{r}"


def test_local_store_and_read(tmp_path):
    provider = LocalStorageProvider(base_dir=tmp_path)
    data = b"audio content" * 100

    async def run():
        key, size, sha = await provider.store("a/b/blob.bin", _aiter([data[:100], data[100:]]))
        return key, size, sha

    key, size, sha = asyncio.run(run())
    assert size == len(data)
    assert provider.open_read and asyncio.run(provider.exists(key))

    async def read():
        f = await provider.open_read(key)
        with f:
            return f.read()

    assert asyncio.run(read()) == data


def test_store_failure_cleans_tmp(tmp_path, monkeypatch):
    provider = LocalStorageProvider(base_dir=tmp_path)

    async def bad_stream():
        yield b"x"
        raise RuntimeError("disk full")

    async def run():
        await provider.store("f/b.bin", bad_stream())

    import pytest

    with pytest.raises(RuntimeError):
        asyncio.run(run())
    # No temp leftovers
    leftovers = list(tmp_path.rglob("*.tmp")) + list(tmp_path.rglob("*blob.bin*"))
    assert leftovers == []
