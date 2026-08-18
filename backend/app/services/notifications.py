from collections.abc import Callable, Mapping
from datetime import date, datetime, time
from email.message import EmailMessage
import smtplib
from typing import Any
from zoneinfo import ZoneInfo

from app.config import Settings


class NotificationService:
    def __init__(
        self,
        repository: Any,
        settings: Settings,
        send_mail: Callable[[Mapping[str, Any]], None] | None = None,
        weekday_time: time = time(9),
        timezone_name: str = "Asia/Seoul",
    ):
        self.repository = repository
        self.settings = settings
        self.send_mail = send_mail or self._send_smtp
        self.weekday_time = weekday_time
        self.timezone = ZoneInfo(timezone_name)
        self.sent_messages: list[dict[str, Any]] = []
        self.preview_count = 0

    def queue(
        self,
        task: Mapping[str, Any],
        event: str = "scheduled",
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        now = now or datetime.now(self.timezone)
        now = now.astimezone(self.timezone)
        if not self._is_due(task, event, now.date()):
            return None

        immediate = event in {"assigned", "reopened"}
        scheduled_at = now if immediate else datetime.combine(
            now.date(), self.weekday_time, self.timezone
        )
        recipients = self._recipients(task, event)
        values = {
            "voc_request_id": task.get("voc_request_id"),
            "task_id": task.get("id"),
            "recipients": recipients,
            "subject": f"[{task.get('case_id', 'VOC')}] {event} notification",
            "body": f"Department: {task.get('department', '')}",
            "scheduled_at": scheduled_at,
            "runtime_profile": self.settings.runtime_profile,
            "delivery_status": "preview",
            "real_delivery": False,
            "sent_at": None,
            "error_message": None,
        }

        if self.settings.runtime_profile == "external_review":
            self.preview_count += 1
        elif not self.settings.smtp_configured:
            values["delivery_status"] = "pending"
        else:
            try:
                self.send_mail(values)
            except Exception as error:
                values["delivery_status"] = "failed"
                values["error_message"] = str(error)
            else:
                values["delivery_status"] = "sent"
                values["real_delivery"] = True
                values["sent_at"] = now
                self.sent_messages.append(values.copy())
        return self.repository.record_notification(values)

    @staticmethod
    def _is_due(task: Mapping[str, Any], event: str, today: date) -> bool:
        if event in {"assigned", "reopened"}:
            return True
        if today.weekday() >= 5 or not task.get("due_date"):
            return False
        days = (task["due_date"] - today).days
        if task.get("priority") == "high":
            return days >= 0
        return days in {1, 2} or days < 0

    @staticmethod
    def _recipients(task: Mapping[str, Any], event: str) -> list[str]:
        fields = ["assignee_email", "manager_email"]
        if task.get("priority") == "high" and event != "reopened":
            fields.append("final_approver_email")
        return list(dict.fromkeys(task[field] for field in fields if task.get(field)))

    def _send_smtp(self, message: Mapping[str, Any]) -> None:
        email = EmailMessage()
        email["From"] = self.settings.voc_smtp_from
        email["To"] = ", ".join(message["recipients"])
        email["Subject"] = message["subject"]
        email.set_content(message["body"])
        with smtplib.SMTP(
            self.settings.voc_smtp_host, self.settings.voc_smtp_port
        ) as smtp:
            password = self.settings.voc_smtp_password.get_secret_value()
            if self.settings.voc_smtp_username:
                smtp.login(self.settings.voc_smtp_username, password)
            smtp.send_message(email)
