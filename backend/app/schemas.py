from datetime import date, datetime
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
    boost_voc_subtype: NonEmptyText | None = None
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


class ManualRequest(BaseModel):
    customer_request: NonEmptyText
    original_mail_body: NonEmptyText
    customer_name: NonEmptyText
    product_equipment: NonEmptyText | None = None
    voc_type: NonEmptyText
    voc_subtype: NonEmptyText
    responsible_departments: NonEmptyText | None = None
    received_at: date | None = None


class SimilarCases(BaseModel):
    items: list[ArchiveItem]


class MailAnalysisRequest(BaseModel):
    original_mail_body: NonEmptyText


class MailAnalysis(BaseModel):
    sender_name: str | None = None
    sender_email: str | None = None
    sender_company: str | None = None
    translation_draft: str | None = None
    translation_status: str
    suggested_voc_type: str | None = None
    suggested_voc_subtype: str | None = None
    suggested_product_equipment: str | None = None
    suggested_customer_request: str | None = None
    suggested_priority: Literal["normal", "high"] = "normal"
    suggested_departments: list[str] = Field(default_factory=list)
    extracted_keywords: list[str] = Field(default_factory=list)
    items: list[ArchiveItem]


TaskStatus = Literal[
    "not_started", "reviewing", "in_progress", "completed", "delayed", "excluded"
]
VocStage = Literal[
    "received",
    "managing",
    "in_progress",
    "department_work",
    "department_review",
    "manager_review",
    "final_review",
    "customer_reply",
    "completed",
    "cancelled",
    "deleted",
]


class DepartmentTaskCreate(BaseModel):
    department: NonEmptyText
    assignee_name: NonEmptyText | None = None
    assignee_email: NonEmptyText | None = None
    manager_name: NonEmptyText | None = None
    manager_email: NonEmptyText | None = None
    due_date: date | None = None
    ecm_link: NonEmptyText | None = None


class VocCreate(BaseModel):
    customer_request: NonEmptyText
    original_mail_body: str = ""
    sender_name: NonEmptyText | None = None
    sender_email: NonEmptyText | None = None
    sender_company: NonEmptyText | None = None
    translation_draft: str | None = None
    translation_final: str | None = None
    voc_type: NonEmptyText | None = None
    voc_subtype: NonEmptyText | None = None
    product_equipment: NonEmptyText | None = None
    priority: Literal["normal", "high"] = "normal"
    tasks: list[DepartmentTaskCreate] = Field(default_factory=list)


class VocRoundCreate(VocCreate):
    tasks: list[DepartmentTaskCreate] | None = None


class DepartmentTaskUpdate(BaseModel):
    department: NonEmptyText | None = None
    assignee_name: NonEmptyText | None = None
    assignee_email: NonEmptyText | None = None
    manager_name: NonEmptyText | None = None
    manager_email: NonEmptyText | None = None
    status: TaskStatus | None = None
    response_content: NonEmptyText | None = None
    due_date: date | None = None
    delay_reason: NonEmptyText | None = None
    ecm_link: NonEmptyText | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not any(
            getattr(self, field) is not None for field in self.model_fields_set
        ):
            raise ValueError("at least one task field is required")
        return self


class TaskReviewCreate(BaseModel):
    reviewer_role: Literal["department_manager", "final_approver"]
    decision: Literal["approved", "rejected"]
    comment: NonEmptyText | None = None


class VocStageUpdate(BaseModel):
    stage: VocStage
    reason: NonEmptyText | None = None
    cancellation_reason: NonEmptyText | None = None
    deletion_reason: NonEmptyText | None = None
    ecm_link: NonEmptyText | None = None

    @model_validator(mode="after")
    def require_terminal_reason(self):
        if self.stage == "cancelled" and self.cancellation_reason is None:
            raise ValueError("cancellation_reason is required")
        if self.stage == "deleted" and self.deletion_reason is None:
            raise ValueError("deletion_reason is required")
        return self


class TranslationRequest(BaseModel):
    text: NonEmptyText


class DashboardStageCount(BaseModel):
    stage: VocStage
    count: int = Field(ge=0)


class DashboardDueTask(BaseModel):
    id: int
    case_id: str | None = None
    department: str | None = None
    status: TaskStatus
    due_date: date | None = None
    priority: Literal["normal", "high"] | None = None
    stage: VocStage | None = None


class DashboardRecentRequest(BaseModel):
    case_id: str
    sender_company: str | None = None
    product_equipment: str | None = None
    priority: Literal["normal", "high"] | None = None
    stage: VocStage | None = None
    created_at: datetime | None = None


class DashboardActiveRequest(DashboardRecentRequest):
    voc_type: str | None = None
    voc_subtype: str | None = None
    responsible_departments: str | None = None


class DashboardMonthlyVocCount(BaseModel):
    month: str
    complaint: int = Field(ge=0)
    request: int = Field(ge=0)
    inquiry: int = Field(ge=0)


class DashboardResponse(BaseModel):
    stage_counts: list[DashboardStageCount]
    monthly_voc_counts: list[DashboardMonthlyVocCount] = Field(default_factory=list)
    due_tasks: list[DashboardDueTask]
    recent_requests: list[DashboardRecentRequest]
    active_requests: list[DashboardActiveRequest]
