from pydantic import BaseModel


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedResponse(BaseModel):
    meta: PaginationMeta
    data: list


class ErrorResponse(BaseModel):
    error: dict
