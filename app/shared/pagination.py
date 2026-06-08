from typing import Annotated, Any

from fastapi import Depends, Query
from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int
    per_page: int

    @property
    def limit(self) -> int:
        return self.per_page

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


def pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginationParams:
    return PaginationParams(page=page, per_page=per_page)


Paginate = Annotated[PaginationParams, Depends(pagination)]


def paginated(items: list[Any], total: int, params: PaginationParams) -> dict:
    pages = (total + params.per_page - 1) // params.per_page
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "per_page": params.per_page,
        "pages": pages,
    }
