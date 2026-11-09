from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field


Item = TypeVar("Item")


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
