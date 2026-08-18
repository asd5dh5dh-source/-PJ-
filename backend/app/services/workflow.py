from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import HTTPException

from app.repositories.collaboration import (
    ApprovalRequired,
    FinalApproverMismatch,
    ReviewerMismatch,
    RoundNotAllowed,
    StageTransitionNotAllowed,
    validate_stage_transition,
)
from app.services.mail_parser import parse_sender


class WorkflowService:
    def __init__(
        self,
        repository: Any,
        today: Callable[[], date] = date.today,
    ):
        self.repository = repository
        self.today = today

    def create_voc(self, values: dict[str, Any], writer_name: str):
        values = dict(values)
        tasks = values.pop("tasks", []) or []
        self._apply_sender(values)
        return self.repository.create_voc(
            values, tasks, writer_name, self.today().year
        )

    def create_round(
        self, case_id: str, values: dict[str, Any], writer_name: str
    ):
        case = self.repository.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="VOC not found")
        if case["rounds"][-1]["stage"] not in {"customer_reply", "completed"}:
            raise HTTPException(
                status_code=409,
                detail="Follow-up rounds require customer_reply or completed stage",
            )
        values = dict(values)
        self._apply_sender(values)
        try:
            created = self.repository.create_round(case_id, values, writer_name)
        except RoundNotAllowed as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if created is None:
            raise HTTPException(status_code=404, detail="VOC not found")
        return created

    def update_task(
        self, task_id: int, changes: dict[str, Any], writer_name: str
    ):
        task = self.repository.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        changes = dict(changes)
        changes = {
            field: value
            for field, value in changes.items()
            if value != task.get(field)
        }
        if not changes:
            raise HTTPException(status_code=422, detail="Task update has no changes")
        status = changes.get("status", task["status"])
        due_date = changes.get("due_date", task.get("due_date"))
        response = changes.get("response_content", task.get("response_content"))
        delay_reason = changes.get("delay_reason", task.get("delay_reason"))
        if (
            task["status"] not in {"completed", "excluded", "delayed"}
            and due_date
            and due_date < self.today()
        ):
            if not delay_reason:
                raise HTTPException(
                    status_code=422,
                    detail="Overdue tasks require delay_reason before completion",
                )
            changes["status"] = "delayed"
            status = "delayed"
        if status == "completed":
            if not due_date or not response:
                raise HTTPException(
                    status_code=422,
                    detail="Completed tasks require response_content and due_date",
                )
            if due_date < self.today() and not delay_reason:
                raise HTTPException(
                    status_code=422,
                    detail="Overdue tasks require delay_reason before completion",
                )
        if status == "delayed" and not delay_reason:
            raise HTTPException(
                status_code=422, detail="Delayed tasks require delay_reason"
            )
        return self.repository.update_task(task_id, changes, writer_name)

    def review_task(
        self, task_id: int, values: dict[str, Any], writer_name: str
    ):
        task = self.repository.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if (
            values["reviewer_role"] == "department_manager"
            and task.get("manager_name") != writer_name
        ):
            raise HTTPException(
                status_code=403, detail="Task department manager required"
            )
        try:
            return self.repository.review_task(task_id, values, writer_name)
        except ReviewerMismatch as error:
            raise HTTPException(
                status_code=403, detail="Task department manager required"
            ) from error
        except FinalApproverMismatch as error:
            raise HTTPException(
                status_code=403, detail="Fixed final approver required"
            ) from error
        except ApprovalRequired as error:
            raise HTTPException(
                status_code=409,
                detail="Fresh department manager approvals are required",
            ) from error

    def change_stage(
        self, case_id: str, values: dict[str, Any], writer_name: str
    ):
        case = self.repository.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="VOC not found")
        latest = case["rounds"][-1]
        target = values["stage"]
        current = latest["stage"]
        try:
            validate_stage_transition(
                current,
                target,
                values.get("reason"),
                values.get(
                    "cancellation_reason"
                    if target == "cancelled"
                    else "deletion_reason"
                ),
            )
        except StageTransitionNotAllowed as error:
            raise HTTPException(
                status_code=error.status_code, detail=error.detail
            ) from error
        try:
            return self.repository.change_stage(
                case_id,
                values,
                writer_name,
                require_approvals=target == "customer_reply",
            )
        except ApprovalRequired as error:
            raise HTTPException(
                status_code=409,
                detail="All active tasks, manager reviews, and final approval are required",
            ) from error
        except StageTransitionNotAllowed as error:
            raise HTTPException(
                status_code=error.status_code, detail=error.detail
            ) from error

    @staticmethod
    def _apply_sender(values: dict[str, Any]) -> None:
        parsed = parse_sender(values.get("original_mail_body", ""))
        for field, parsed_value in parsed.items():
            if parsed_value is not None and not values.get(field):
                values[field] = parsed_value
