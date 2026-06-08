from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    async def upload_url(self, key: str, content_type: str) -> str: ...

    @abstractmethod
    async def access_url(self, key: str) -> str: ...

    @abstractmethod
    async def save(self, key: str, content: bytes, content_type: str) -> str: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...
