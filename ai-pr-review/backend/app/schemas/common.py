"""
Common Pydantic schemas — pagination, error responses, etc.
"""
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Standard error detail body."""

    code: str
    message: str
    details: dict | None = None


class ErrorResp(BaseModel):
    """Standard error response wrapped with request_id."""

    error: ErrorDetail
    request_id: str | None = None


class PaginatedResponse[T](BaseModel):
    """Generic paginated response wrapper."""

    items: list[T]
    total: int
    page: int
    per_page: int

    @property
    def total_pages(self) -> int:
        if self.per_page == 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page
