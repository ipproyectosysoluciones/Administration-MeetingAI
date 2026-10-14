"""Document storage provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class DocumentStorageProvider(ABC):
    """Abstract storage provider for document files."""

    @abstractmethod
    async def store(self, tenant_id: str, sha256: str, content: bytes) -> str:
        """Store content and return the storage path/key."""
        ...

    @abstractmethod
    async def retrieve(self, path: str) -> BinaryIO:
        """Retrieve a file handle for reading."""
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete a file from storage."""
        ...


class LocalStorageProvider(DocumentStorageProvider):
    """Local filesystem storage provider."""

    def __init__(self, base_path: str = "/var/lib/reunionai/documents") -> None:
        self._base_path = base_path

    async def store(self, tenant_id: str, sha256: str, content: bytes) -> str:
        import os

        import aiofiles

        # Path: /base/tenant_id/sha256[:2]/sha256[2:4]/sha256
        path_parts = [self._base_path, tenant_id, sha256[:2], sha256[2:4], sha256]
        file_path = os.path.join(*path_parts)

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        return file_path

    async def retrieve(self, path: str) -> BinaryIO:
        import aiofiles

        return await aiofiles.open(path, "rb")

    async def delete(self, path: str) -> None:
        import os

        if os.path.exists(path):
            os.remove(path)
