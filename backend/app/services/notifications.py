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
        values = self._notification_values(task, event, now)
        if values is None:
            return None

        claim = getattr(self.repository, "claim_notification", None)
        notification = (
            claim(values) if claim is not None else self.repository.record_notification(values)
        )
        if notification is None:
            return None
        if self.settings.runtime_profile == "external_review":
            self.preview_count += 1
            return notification
        if not self.settings.smtp_configured:
            return notification
        try:
            self.send_mail(notification)
        except Exception as error:
            changes = {"delivery_status": "failed", "error_message": str(error)}
        else:
            changes = {
                "delivery_status": "sent",
                "real_delivery": True,
                "sent_at": now or datetime.now(self.timezone),
            }
            self.sent_messages.append({**notification, **changes})
        update = getattr(self.repository, "update_notification_delivery", None)
        if update is not None:
            return update(notification["id"], changes)
        notification.update(changes)
        return notification

    def list_pending_previews(
        self,
        logs: list[Mapping[str, Any]] | None = None,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        task_ids = getattr(self.repository, "list_daily_notification_task_ids", lambda: [])()
        get_context = getattr(self.repository, "get_notification_context", None)
        if get_context is None:
            return []
        known_keys = {
            log.get("dedupe_key")
            for log in logs or []
            if log.get("dedupe_key")
        }
        previews = []
        for task_id in task_ids:
            for event in ("assigned", "scheduled"):
                task = get_context(task_id, event)
                values = (
                    self._notification_values(task, event, now)
                    if task is not None
                    else None
                )
                if values is None or values["dedupe_key"] in known_keys:
                    continue
                event_offset = 1 if event == "assigned" else 2
                previews.append(
                    {
                        "id": -(int(task_id) * 10 + event_offset),
                        **values,
                        "created_at": values["scheduled_at"],
                    }
                )
        return previews

    def _notification_values(
        self,
        task: Mapping[str, Any],
        event: str,
        now: datetime | None,
    ) -> dict[str, Any] | None:
        timezone = ZoneInfo(task.get("timezone_name", self.timezone.key))
        weekday_time = task.get("weekday_time", self.weekday_time)
        now = now or datetime.now(timezone)
        now = now.astimezone(timezone)
        if not self._is_due(task, event, now.date()):
            return None

        immediate = event in {"assigned", "reopened"}
        scheduled_at = now if immediate else datetime.combine(
            now.date(), weekday_time, timezone
        )
        recipients = self._recipients(task, event)
        template_values = _TemplateValues({**task, "event": event})
        subject_template = task.get("subject_template") or (
            "[{case_id}] {event} notification"
        )
        body_template = task.get("body_template") or "Department: {department}"
        dedupe_key = f"task:{task.get('id')}:{event}"
        if event == "scheduled":
            dedupe_key += f":{now.date().isoformat()}"
        return {
            "voc_request_id": task.get("voc_request_id"),
            "task_id": task.get("id"),
            "event_key": event,
            "dedupe_key": dedupe_key,
            "recipients": recipients,
            "subject": subject_template.format_map(template_values),
            "body": body_template.format_map(template_values),
            "scheduled_at": scheduled_at,
            "runtime_profile": self.settings.runtime_profile,
            "delivery_status": (
                "preview"
                if self.settings.runtime_profile == "external_review"
                else "pending"
            ),
            "real_delivery": False,
            "sent_at": None,
            "error_message": None,
        }

    def queue_task(
        self,
        task_id: int,
        event: str,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        get_context = getattr(self.repository, "get_notification_context", None)
        if get_context is None:
            return None
        task = get_context(task_id, event)
        return None if task is None else self.queue(task, event, now)

    def queue_daily(self, now: datetime | None = None) -> list[dict[str, Any]]:
        task_ids = self.repository.list_daily_notification_task_ids()
        return [
            queued
            for task_id in task_ids
            if (queued := self.queue_task(task_id, "scheduled", now)) is not None
        ]

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


class _TemplateValues(dict):
    def __init__(self, task: Mapping[str, Any]):
        super().__init__(task)
        self["event"] = task.get("event", "")

    def __missing__(self, key: str) -> str:
        return ""
