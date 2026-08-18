from collections.abc import Callable
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from app.auth import WriterContext, require_writer
from app.schemas import (
    DepartmentTaskUpdate,
    TaskReviewCreate,
    VocCreate,
    VocRoundCreate,
    VocStageUpdate,
)
from app.services.workflow import WorkflowService


def create_collaboration_router(
    repository: Any,
    today: Callable[[], date] = date.today,
    notification_service: Any | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["collaboration"])
    workflow = WorkflowService(repository, today, notification_service)

    @router.post("/voc", status_code=status.HTTP_201_CREATED)
    def create_voc(
        payload: VocCreate,
        writer: Annotated[WriterContext, Depends(require_writer)],
    ):
        return workflow.create_voc(
            payload.model_dump(exclude_none=True), writer.writer_name
        )

    @router.post("/voc/{case_id}/rounds", status_code=status.HTTP_201_CREATED)
    def create_round(
        case_id: str,
        payload: VocRoundCreate,
        writer: Annotated[WriterContext, Depends(require_writer)],
    ):
        return workflow.create_round(
            case_id,
            payload.model_dump(exclude_none=True, exclude_unset=True),
            writer.writer_name,
        )

    @router.post("/tasks/{task_id}")
    def update_task(
        task_id: int,
        payload: DepartmentTaskUpdate,
        writer: Annotated[WriterContext, Depends(require_writer)],
    ):
        return workflow.update_task(
            task_id,
            payload.model_dump(exclude_none=True, exclude_unset=True),
            writer.writer_name,
        )

    @router.post("/tasks/{task_id}/review", status_code=status.HTTP_201_CREATED)
    def review_task(
        task_id: int,
        payload: TaskReviewCreate,
        writer: Annotated[WriterContext, Depends(require_writer)],
    ):
        return workflow.review_task(
            task_id, payload.model_dump(exclude_none=True), writer.writer_name
        )

    @router.post("/voc/{case_id}/stage")
    def change_stage(
        case_id: str,
        payload: VocStageUpdate,
        writer: Annotated[WriterContext, Depends(require_writer)],
    ):
        return workflow.change_stage(
            case_id, payload.model_dump(exclude_none=True), writer.writer_name
        )

    @router.get("/voc/{case_id}")
    def get_voc(case_id: str):
        case = repository.get_case(case_id)
        if case is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="VOC not found")
        return case

    return router
