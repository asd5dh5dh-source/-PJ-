from datetime import date, datetime, time
from subprocess import CompletedProcess
from contextlib import contextmanager
from zoneinfo import ZoneInfo

from app.config import Settings
from app.services.notifications import NotificationService
from app.services.translation import TranslationService
from app.repositories.collaboration import CollaborationRepository


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


def test_internal_translation_uses_configured_local_cpu_adapter(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return CompletedProcess(command, 0, stdout="고장 조사를 요청합니다\n")

    monkeypatch.setattr("subprocess.run", run)
    settings = Settings(
        VOC_RUNTIME_PROFILE="internal",
        VOC_TRANSLATION_COMMAND="local-translator.exe",
        VOC_TRANSLATION_MODEL_PATH="C:/models/ko-model",
    )

    result = TranslationService(settings).translate("Please investigate the failure")

    assert result["status"] == "translated"
    assert result["translated_text"] == "고장 조사를 요청합니다"
    assert calls == [
        (
            ["local-translator.exe", "--model", "C:/models/ko-model"],
            {
                "input": "Please investigate the failure",
                "text": True,
                "capture_output": True,
                "check": True,
                "timeout": 120,
            },
        )
    ]


def test_external_translation_ignores_configured_local_adapter(monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("external review must not start a local process")
        ),
    )
    settings = Settings(
        VOC_RUNTIME_PROFILE="external_review",
        VOC_TRANSLATION_COMMAND="local-translator.exe",
        VOC_TRANSLATION_MODEL_PATH="C:/models/ko-model",
    )

    result = TranslationService(settings).translate("Please investigate")

    assert result["status"] == "preview"


class ManagedNotificationRepository:
    def __init__(self):
        self.logs = {}
        self.next_id = 1
        self.context = {
            **TASK,
            "customer_name": "Acme",
            "product_equipment": "NCM811",
            "request_title": "Investigate failure",
            "stage": "department_work",
            "ecm_link": "https://ecm.example/item",
            "weekday_time": time(8, 30),
            "timezone_name": "Asia/Tokyo",
            "subject_template": "[{case_id}] {department}",
            "body_template": "{customer_name} due {due_date}",
        }

    def get_notification_context(self, task_id, event):
        return dict(self.context)

    def list_daily_notification_task_ids(self):
        return [self.context["id"]]

    def claim_notification(self, values):
        key = values["dedupe_key"]
        if key in self.logs:
            return None
        claimed = {"id": self.next_id, **values}
        self.next_id += 1
        self.logs[key] = claimed
        return claimed

    def update_notification_delivery(self, notification_id, values):
        log = next(item for item in self.logs.values() if item["id"] == notification_id)
        log.update(values)
        return dict(log)


def test_queue_task_uses_managed_final_approver_schedule_and_template():
    repository = ManagedNotificationRepository()
    service = NotificationService(
        repository, Settings(VOC_RUNTIME_PROFILE="external_review")
    )
    now = datetime(2026, 8, 18, 3, tzinfo=ZoneInfo("UTC"))

    result = service.queue_task(9, event="assigned", now=now)

    assert result["recipients"] == [
        "owner@example.com",
        "manager@example.com",
        "approver@example.com",
    ]
    assert result["subject"] == "[VOC-2026-0007] Quality"
    assert result["body"] == "Acme due 2026-08-20"
    assert result["dedupe_key"] == "task:9:assigned"


def test_notification_claim_prevents_duplicate_internal_delivery():
    repository = ManagedNotificationRepository()
    dispatched = []
    service = NotificationService(
        repository,
        Settings(
            VOC_RUNTIME_PROFILE="internal",
            voc_smtp_host="smtp.example.com",
            voc_smtp_from="voc@example.com",
        ),
        send_mail=lambda message: dispatched.append(message),
    )
    now = datetime(2026, 8, 18, 12, tzinfo=ZoneInfo("Asia/Seoul"))

    first = service.queue_task(9, event="assigned", now=now)
    duplicate = service.queue_task(9, event="assigned", now=now)

    assert first["delivery_status"] == "sent"
    assert duplicate is None
    assert len(dispatched) == 1
    assert len(repository.logs) == 1


def test_daily_queue_uses_managed_weekday_schedule():
    repository = ManagedNotificationRepository()
    repository.context.update(priority="normal", due_date=date(2026, 8, 20))
    service = NotificationService(
        repository, Settings(VOC_RUNTIME_PROFILE="external_review")
    )

    queued = service.queue_daily(
        now=datetime(2026, 8, 18, 0, tzinfo=ZoneInfo("UTC"))
    )

    assert queued[0]["scheduled_at"] == datetime(
        2026, 8, 18, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo")
    )
    assert queued[0]["dedupe_key"] == "task:9:scheduled:2026-08-18"


def test_normal_priority_assignment_does_not_queue():
    repository = ManagedNotificationRepository()
    repository.context["priority"] = "normal"
    service = NotificationService(
        repository, Settings(VOC_RUNTIME_PROFILE="external_review")
    )

    assert service.queue_task(9, event="assigned") is None


def test_missing_managed_template_uses_safe_default_content():
    repository = ManagedNotificationRepository()
    repository.context.update(subject_template=None, body_template=None)
    service = NotificationService(
        repository, Settings(VOC_RUNTIME_PROFILE="external_review")
    )

    result = service.queue_task(
        9,
        event="assigned",
        now=datetime(2026, 8, 18, 12, tzinfo=ZoneInfo("Asia/Seoul")),
    )

    assert result["subject"] == "[VOC-2026-0007] assigned notification"
    assert result["body"] == "Department: Quality"


def test_repository_claim_is_atomic_on_notification_dedupe_key():
    class Result:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self):
            self.claimed = False
            self.queries = []

        def execute(self, query, params=()):
            normalized = " ".join(query.split())
            self.queries.append(normalized)
            if self.claimed:
                return Result(None)
            self.claimed = True
            return Result({"id": 1, "dedupe_key": "task:9:assigned"})

    connection = Connection()

    @contextmanager
    def connection_factory():
        yield connection

    repository = CollaborationRepository(connection_factory)
    values = {
        "dedupe_key": "task:9:assigned",
        "event_key": "assigned",
        "recipients": [],
        "subject": "subject",
        "body": "body",
        "runtime_profile": "external_review",
        "delivery_status": "preview",
        "real_delivery": False,
    }

    assert repository.claim_notification(values)["id"] == 1
    assert repository.claim_notification(values) is None
    assert all(
        "ON CONFLICT (dedupe_key) DO NOTHING" in query
        for query in connection.queries
    )
