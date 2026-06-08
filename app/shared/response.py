from typing import Any


def success(data: Any = None, status: str = "ok") -> dict:
    return {"data": data, "status": status}


def error(message: str, errors: dict | None = None) -> dict:
    return {"errors": errors or {}, "message": message}
