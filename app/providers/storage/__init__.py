from functools import lru_cache

from app.core.config import settings
from app.providers.storage.base import StorageProvider
from app.providers.storage.local import LocalStorageProvider
from app.providers.storage.s3 import S3StorageProvider

_PROVIDERS: dict[str, type[StorageProvider]] = {
    "local": LocalStorageProvider,
    "s3": S3StorageProvider,
}


@lru_cache
def get_storage_provider() -> StorageProvider:
    provider = _PROVIDERS.get(settings.STORAGE_PROVIDER, LocalStorageProvider)
    return provider()
