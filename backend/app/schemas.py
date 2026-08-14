from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ArchiveSort = Literal["relevance", "latest", "oldest"]


class ArchiveQuery(BaseModel):
    q: NonEmptyText | None = None
    customer_name: NonEmptyText | None = None
    product_equipment: NonEmptyText | None = None
    voc_type: NonEmptyText | None = None
    voc_subtype: NonEmptyText | None = None
    final_status: NonEmptyText | None = None
    responsible_department: NonEmptyText | None = None
    received_from: date | None = None
    received_to: date | None = None
    sort: ArchiveSort | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def require_keyword_for_relevance(self):
        if self.sort == "relevance" and self.q is None:
            raise ValueError("relevance sort requires a keyword")
        return self


class ArchiveItem(BaseModel):
    case_id: str
    customer_name: str | None = None
    product_equipment: str | None = None
    voc_type: str | None = None
    voc_subtype: str | None = None
    customer_request: str | None = None
    responsible_departments: str | None = None
    received_at: date | None = None
    final_status: str | None = None
    record_origin: str | None = None
    bm25_score: float | None = None
    final_score: float | None = None
    matched_keywords: list[str] = Field(default_factory=list)


class ArchiveDetail(ArchiveItem):
    original_mail_body: str | None = None
    full_response_history: str | None = None


class ArchivePage(BaseModel):
    items: list[ArchiveItem]
    total: int
    page: int
    page_size: int
    sort: ArchiveSort
