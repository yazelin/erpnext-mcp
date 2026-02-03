from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class ERPNextResponse(BaseModel):
    data: Any = None
    message: Any = None
    exc: str | None = None
    exc_type: str | None = None


class ListFilters(BaseModel):
    filters: dict[str, Any] | list[list] | None = None
    fields: list[str] | None = None
    order_by: str | None = None
    limit_start: int = 0
    limit_page_length: int = 20
    or_filters: dict[str, Any] | list[list] | None = None


class DocumentResponse(BaseModel):
    name: str
    doctype: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
