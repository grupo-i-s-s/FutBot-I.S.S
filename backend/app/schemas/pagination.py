from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

from app.errors import AppError


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_PAGE_OFFSET = 2**63 - 1  # PostgreSQL recibe OFFSET como bigint.
Item = TypeVar("Item")


def validate_page_offset(page: int, page_size: int) -> None:
    if (page - 1) * page_size > MAX_PAGE_OFFSET:
        raise AppError(
            "VALIDATION_ERROR",
            "Revisá los datos ingresados.",
            {"page": "El número de página supera el máximo permitido para ese tamaño de página."},
        )


class Page(BaseModel, Generic[Item]):
    items: list[Item]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, serialization_alias="pageSize")
    total: int = Field(ge=0)

    @computed_field(alias="totalPages")
    @property
    def total_pages(self) -> int:
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @computed_field(alias="hasNext")
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages
