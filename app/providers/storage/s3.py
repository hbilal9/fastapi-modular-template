import anyio.to_thread
import boto3
from botocore.client import Config

from app.core.config import settings
from app.providers.storage.base import StorageProvider


class S3StorageProvider(StorageProvider):
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY or None,
            aws_secret_access_key=settings.S3_SECRET_KEY or None,
            config=Config(signature_version="s3v4"),
        )

    async def upload_url(self, key: str, content_type: str) -> str:
        return await anyio.to_thread.run_sync(self._presign_put, key, content_type)

    async def access_url(self, key: str) -> str:
        if settings.S3_PUBLIC_URL:
            return f"{settings.S3_PUBLIC_URL.rstrip('/')}/{key}"
        return await anyio.to_thread.run_sync(self._presign_get, key)

    async def save(self, key: str, content: bytes, content_type: str) -> str:
        await anyio.to_thread.run_sync(self._put, key, content, content_type)
        return key

    async def delete(self, key: str) -> None:
        await anyio.to_thread.run_sync(self._delete, key)

    def _presign_put(self, key: str, content_type: str) -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key, "ContentType": content_type},
            ExpiresIn=3600,
        )

    def _presign_get(self, key: str) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=3600,
        )

    def _put(self, key: str, content: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=settings.S3_BUCKET, Key=key, Body=content, ContentType=content_type
        )

    def _delete(self, key: str) -> None:
        self._client.delete_object(Bucket=settings.S3_BUCKET, Key=key)
