from pathlib import Path

import anyio.to_thread

from app.core.config import settings
from app.providers.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self) -> None:
        self._root = Path(settings.STORAGE_LOCAL_DIR)

    async def upload_url(self, key: str, content_type: str) -> str:
        return f"/api/file/local/{key}"

    async def access_url(self, key: str) -> str:
        return f"{settings.STORAGE_LOCAL_BASE_URL.rstrip('/')}/{key}"

    async def save(self, key: str, content: bytes, content_type: str) -> str:
        await anyio.to_thread.run_sync(self._write, key, content)
        return key

    async def delete(self, key: str) -> None:
        await anyio.to_thread.run_sync(self._remove, key)

    def _write(self, key: str, content: bytes) -> None:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def _remove(self, key: str) -> None:
        (self._root / key).unlink(missing_ok=True)
