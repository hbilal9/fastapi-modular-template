from typing import cast

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, errors: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.errors = errors or {}
        super().__init__(message)


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    err = cast(AppError, exc)
    return JSONResponse(
        status_code=err.status_code,
        content={"errors": err.errors, "message": err.message},
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    err = cast(RequestValidationError, exc)
    errors: dict[str, list[str]] = {}
    for item in err.errors():
        field = ".".join(str(p) for p in item["loc"] if p != "body")
        errors.setdefault(field or "non_field", []).append(item["msg"])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"errors": errors, "message": "Validation failed."},
    )
