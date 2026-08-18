from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.config import Settings
from app.services.notifications import NotificationService
from app.services.translation import TranslationService


class MemoryNotificationRepository:
    def __init__(self):
        self.logs = []

    def record_notification(self, values):
        self.logs.append(values)
        return values


TASK = {
    "id": 9,
    "voc_request_id": 3,
    "case_id": "VOC-2026-0007",
    "priority": "high",
    "assignee_email": "owner@example.com",
    "manager_email": "manager@example.com",
    "final_approver_email": "approver@example.com",
    "due_date": date(2026, 8, 20),
    "department": "Quality",
}


def test_external_profile_records_mail_preview_without_dispatch():
    repository = MemoryNotificationRepository()
    dispatched = []
    service = NotificationService(
        repository,
        Settings(VOC_RUNTIME_PROFILE="external_review"),
        send_mail=lambda message: dispatched.append(message),
    )

    result = service.queue(
        TASK,
        event="assigned",
        now=datetime(2026, 8, 18, 12, tzinfo=ZoneInfo("Asia/Seoul")),
    )

    assert dispatched == []
    assert result["delivery_status"] == "preview"
    assert result["real_delivery"] is False
    assert repository.logs == [result]


def test_high_priority_assignment_includes_owner_manager_and_final_approver():
    repository = MemoryNotificationRepository()
    service = NotificationService(
        repository,
        Settings(VOC_RUNTIME_PROFILE="external_review"),
    )

    result = service.queue(
        TASK,
        event="assigned",
        now=datetime(2026, 8, 18, 12, tzinfo=ZoneInfo("Asia/Seoul")),
    )

    assert result["recipients"] == [
        "owner@example.com",
        "manager@example.com",
        "approver@example.com",
    ]


def test_normal_priority_only_queues_d2_d1_or_overdue_on_weekdays():
    repository = MemoryNotificationRepository()
    service = NotificationService(
        repository,
        Settings(VOC_RUNTIME_PROFILE="external_review"),
    )
    task = {**TASK, "priority": "normal", "due_date": date(2026, 8, 21)}

    too_early = service.queue(
        task,
        now=datetime(2026, 8, 18, 9, tzinfo=ZoneInfo("Asia/Seoul")),
    )
    d2 = service.queue(
        task,
        now=datetime(2026, 8, 19, 9, tzinfo=ZoneInfo("Asia/Seoul")),
    )

    assert too_early is None
    assert d2["recipients"] == ["owner@example.com", "manager@example.com"]
    assert d2["scheduled_at"] == datetime(
        2026, 8, 19, 9, tzinfo=ZoneInfo("Asia/Seoul")
    )


def test_notification_schedule_time_and_timezone_are_configurable():
    service = NotificationService(
        MemoryNotificationRepository(),
        Settings(VOC_RUNTIME_PROFILE="external_review"),
        weekday_time=time(8, 30),
        timezone_name="Asia/Tokyo",
    )

    result = service.queue(
        {**TASK, "priority": "normal", "due_date": date(2026, 8, 20)},
        now=datetime(2026, 8, 18, 0, tzinfo=ZoneInfo("UTC")),
    )

    assert result["scheduled_at"] == datetime(
        2026, 8, 18, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo")
    )


def test_reopened_task_alert_is_immediate_even_on_weekend():
    service = NotificationService(
        MemoryNotificationRepository(),
        Settings(VOC_RUNTIME_PROFILE="external_review"),
    )
    now = datetime(2026, 8, 22, 14, 30, tzinfo=ZoneInfo("Asia/Seoul"))

    result = service.queue({**TASK, "priority": "normal"}, event="reopened", now=now)

    assert result["scheduled_at"] == now
    assert result["recipients"] == ["owner@example.com", "manager@example.com"]


def test_internal_profile_without_smtp_records_pending_delivery():
    dispatched = []
    service = NotificationService(
        MemoryNotificationRepository(),
        Settings(VOC_RUNTIME_PROFILE="internal"),
        send_mail=lambda message: dispatched.append(message),
    )

    result = service.queue(
        TASK,
        event="assigned",
        now=datetime(2026, 8, 18, 12, tzinfo=ZoneInfo("Asia/Seoul")),
    )

    assert dispatched == []
    assert result["delivery_status"] == "pending"
    assert result["real_delivery"] is False


def test_external_translation_never_executes_local_model():
    calls = []
    service = TranslationService(
        Settings(VOC_RUNTIME_PROFILE="external_review"),
        translate=lambda text: calls.append(text) or "번역",
    )

    result = service.translate("Please investigate the failure")

    assert calls == []
    assert result == {
        "source_text": "Please investigate the failure",
        "translated_text": None,
        "status": "preview",
    }


def test_korean_input_bypasses_translation_in_internal_profile():
    calls = []
    service = TranslationService(
        Settings(VOC_RUNTIME_PROFILE="internal"),
        translate=lambda text: calls.append(text) or "unused",
    )

    result = service.translate("고객 요청을 확인해 주세요")

    assert calls == []
    assert result["status"] == "bypassed"
    assert result["translated_text"] is None
