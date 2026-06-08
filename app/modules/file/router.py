import uuid

from fastapi import APIRouter, Request

from app.core.dependencies import CurrentUser, Storage
from app.modules.file.schema import UploadUrlRequest
from app.shared.response import success

router = APIRouter(prefix="/file", tags=["file"])


@router.post("/upload/")
async def upload(data: UploadUrlRequest, user: CurrentUser, storage: Storage):
    key = f"{uuid.uuid4().hex}/{data.filename}"
    url = await storage.upload_url(key, data.content_type)
    return success({"key": key, "upload_url": url, "method": "PUT"})


@router.get("/access/")
async def access(key: str, user: CurrentUser, storage: Storage):
    return success({"url": await storage.access_url(key)})


@router.put("/local/{key:path}")
async def local_upload(key: str, request: Request, user: CurrentUser, storage: Storage):
    content = await request.body()
    content_type = request.headers.get("content-type", "application/octet-stream")
    await storage.save(key, content, content_type)
    return success({"key": key})
