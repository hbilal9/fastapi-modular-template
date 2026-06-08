from pydantic import BaseModel


class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str
