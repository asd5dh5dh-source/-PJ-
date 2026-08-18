from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import HTTPException

from app.services.mail_parser import parse_sender


STAGES = [
    "received",
    "managing",
    "in_progress",
    "department_work",
    "department_review",
    "manager_review",
    "final_review",
    "customer_reply",
    "completed",
]


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
        values = dict(values)
        self._apply_sender(values)
        created = self.repository.create_round(case_id, values, writer_name)
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
        status = changes.get("status", task["status"])
        due_date = changes.get("due_date", task.get("due_date"))
        response = changes.get("response_content", task.get("response_content"))
        delay_reason = changes.get("delay_reason", task.get("delay_reason"))
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
        if self.repository.get_task(task_id) is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if (
            values["reviewer_role"] == "final_approver"
            and hasattr(self.repository, "is_final_approver")
            and not self.repository.is_final_approver(writer_name)
        ):
            raise HTTPException(status_code=403, detail="Fixed final approver required")
        return self.repository.review_task(task_id, values, writer_name)

    def change_stage(
        self, case_id: str, values: dict[str, Any], writer_name: str
    ):
        case = self.repository.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="VOC not found")
        latest = case["rounds"][-1]
        target = values["stage"]
        current = latest["stage"]
        if target == "customer_reply" and not self.repository.approvals_complete(
            latest["id"]
        ):
            raise HTTPException(
                status_code=409,
                detail="All active tasks, manager reviews, and final approval are required",
            )
        if (
            target in STAGES
            and current in STAGES
            and STAGES.index(target) < STAGES.index(current)
            and not values.get("reason")
        ):
            raise HTTPException(
                status_code=422, detail="Reverse stage transitions require reason"
            )
        return self.repository.change_stage(case_id, values, writer_name)

    @staticmethod
    def _apply_sender(values: dict[str, Any]) -> None:
        parsed = parse_sender(values.get("original_mail_body", ""))
        for field, parsed_value in parsed.items():
            if not values.get(field):
                values[field] = parsed_value
