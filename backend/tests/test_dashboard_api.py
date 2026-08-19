from contextlib import contextmanager
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.repositories.collaboration import CollaborationRepository


WRITER_HEADERS = {
    "X-Writer-Name": "Kim",
    "X-Writer-Password": "correct-password",
}


class AlwaysUnlockedWriterAttemptStore:
    def record_and_check_locked(self, writer_name, client_ip, succeeded):
        return False


class ArchiveRepository:
    def list_candidates(self, filters=None, **filter_values):
        return []

    def get(self, case_id):
        return None


class OperationsRepository:
    def __init__(self):
        self.dashboard_range = None
        self.notifications = [{"id": 1, "delivery_status": "preview"}]
        self.master = {"customers": []}

    def dashboard(self, date_from, date_to):
        self.dashboard_range = (date_from, date_to)
        return {
            "stage_counts": [{"stage": "received", "count": 2}],
            "due_tasks": [{"id": 4, "status": "delayed"}],
            "recent_requests": [{"case_id": "VOC-2026-0002"}],
            "active_requests": [{
                "case_id": "VOC-2026-0002",
                "sender_company": "Example Materials",
                "voc_type": "Complaint",
                "voc_subtype": "Gas Generation",
                "stage": "in_progress",
            }],
        }

    def list_notifications(self):
        return self.notifications

    def list_daily_notification_task_ids(self):
        return []

    def list_master_data(self, resource):
        return self.master[resource]

    def create_master_data(self, resource, values, writer_name):
        self.writer_name = writer_name
        created = {"id": 1, **values}
        self.master[resource].append(created)
        return created


@pytest.fixture(autouse=True)
def writer_environment(monkeypatch):
    monkeypatch.setenv(
        "VOC_WRITER_PASSWORD_HASH",
        "9246aa9be8de7b40d64eb664986430793b6cc13a19d2a456981e44f28303f9cf",
    )
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def repository():
    return OperationsRepository()


@pytest.fixture
def client(repository):
    app = create_app(
        ArchiveRepository(),
        receipt_date=lambda: date(2026, 8, 18),
        collaboration_repository=repository,
    )
    app.state.writer_attempt_store = AlwaysUnlockedWriterAttemptStore()
    return TestClient(app)


def test_dashboard_defaults_to_recent_thirty_days(client, repository):
    response = client.get("/api/dashboard")

    assert response.status_code == 200
    assert repository.dashboard_range == (date(2026, 7, 20), date(2026, 8, 18))
    assert response.json()["stage_counts"] == [{"stage": "received", "count": 2}]
    assert response.json()["due_tasks"] == [{"id": 4, "status": "delayed"}]
    assert response.json()["recent_requests"] == [{"case_id": "VOC-2026-0002"}]
    assert response.json()["active_requests"] == [{
        "case_id": "VOC-2026-0002",
        "sender_company": "Example Materials",
        "voc_type": "Complaint",
        "voc_subtype": "Gas Generation",
        "stage": "in_progress",
    }]


def test_dashboard_strips_sensitive_request_and_task_fields(client, repository):
    repository.dashboard = lambda date_from, date_to: {
        "stage_counts": [{"stage": "received", "count": 1, "internal": "secret"}],
        "due_tasks": [
            {
                "id": 4,
                "case_id": "VOC-2026-0002",
                "department": "Quality",
                "status": "delayed",
                "sender_email": "private@example.com",
                "response_content": "private response",
            }
        ],
        "recent_requests": [
            {
                "case_id": "VOC-2026-0002",
                "sender_company": "Acme",
                "stage": "received",
                "original_mail_body": "private mail",
                "translation_draft": "private translation",
            }
        ],
        "active_requests": [],
    }

    payload = client.get("/api/dashboard").json()

    assert payload["stage_counts"] == [{"stage": "received", "count": 1}]
    assert payload["due_tasks"] == [
        {
            "id": 4,
            "case_id": "VOC-2026-0002",
            "department": "Quality",
            "status": "delayed",
        }
    ]
    assert payload["recent_requests"] == [
        {
            "case_id": "VOC-2026-0002",
            "sender_company": "Acme",
            "stage": "received",
        }
    ]
    assert payload["active_requests"] == []


def test_dashboard_accepts_custom_date_range(client, repository):
    response = client.get(
        "/api/dashboard",
        params={"date_from": "2026-08-01", "date_to": "2026-08-10"},
    )

    assert response.status_code == 200
    assert repository.dashboard_range == (date(2026, 8, 1), date(2026, 8, 10))


@pytest.mark.parametrize(
    ("period", "expected"),
    [
        ("week", (date(2026, 8, 17), date(2026, 8, 18))),
        ("month", (date(2026, 8, 1), date(2026, 8, 18))),
    ],
)
def test_dashboard_supports_current_week_and_month(client, repository, period, expected):
    response = client.get("/api/dashboard", params={"period": period})

    assert response.status_code == 200
    assert repository.dashboard_range == expected


def test_dashboard_rejects_reverse_date_range(client):
    response = client.get(
        "/api/dashboard",
        params={"date_from": "2026-08-10", "date_to": "2026-08-01"},
    )

    assert response.status_code == 422


def test_notifications_are_public_read_only(client):
    response = client.get("/api/notifications")

    assert response.status_code == 200
    assert response.json() == [{"id": 1, "delivery_status": "preview"}]


def test_daily_notification_processor_requires_writer_and_is_explicit_post(client):
    assert client.post("/api/notifications/process-daily").status_code == 401

    response = client.post(
        "/api/notifications/process-daily", headers=WRITER_HEADERS
    )

    assert response.status_code == 200
    assert response.json() == {"queued": 0}


def test_external_translate_endpoint_returns_preview_without_model(client):
    response = client.post("/api/translate", json={"text": "Please investigate"})

    assert response.status_code == 200
    assert response.json()["status"] == "preview"
    assert response.json()["translated_text"] is None


def test_master_data_apis_require_writer_headers(client):
    assert client.get("/api/admin/master-data/customers").status_code == 401
    assert (
        client.post(
            "/api/admin/master-data/customers", json={"name": "Acme"}
        ).status_code
        == 401
    )


def test_writer_can_create_and_list_master_data(client, repository):
    created = client.post(
        "/api/admin/master-data/customers",
        headers=WRITER_HEADERS,
        json={"name": "Acme"},
    )
    listed = client.get(
        "/api/admin/master-data/customers", headers=WRITER_HEADERS
    )

    assert created.status_code == 201
    assert created.json() == {"id": 1, "name": "Acme"}
    assert repository.writer_name == "Kim"
    assert listed.json() == [created.json()]


def test_master_data_rejects_blank_required_values(client):
    response = client.post(
        "/api/admin/master-data/customers",
        headers=WRITER_HEADERS,
        json={"name": "   "},
    )

    assert response.status_code == 422


def test_unknown_master_data_resource_is_rejected(client):
    response = client.get(
        "/api/admin/master-data/secrets", headers=WRITER_HEADERS
    )

    assert response.status_code == 404


def test_fixed_approver_change_updates_singleton_and_audits_previous_value():
    class Cursor:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=()):
            normalized = " ".join(query.split())
            self.calls.append((normalized, params))
            if normalized.startswith("SELECT * FROM public.master_final_approvers"):
                return Cursor({"singleton_id": 1, "person_id": 4, "updated_by": "Lee"})
            if normalized.startswith("INSERT INTO public.master_final_approvers"):
                return Cursor({"singleton_id": 1, "person_id": 8, "updated_by": "Kim"})
            return Cursor()

    connection = Connection()

    @contextmanager
    def connection_factory():
        yield connection

    result = CollaborationRepository(connection_factory).create_master_data(
        "final_approver", {"person_id": 8}, "Kim"
    )

    statements = [query for query, _ in connection.calls]
    assert result["person_id"] == 8
    assert any("ON CONFLICT (singleton_id) DO UPDATE" in query for query in statements)
    audit_params = next(
        params
        for query, params in connection.calls
        if query.startswith("INSERT INTO public.change_audits")
    )
    assert audit_params[3].obj["person_id"] == 4
    assert audit_params[4].obj["person_id"] == 8


def test_dashboard_repository_counts_only_current_rounds_in_requested_window():
    class Result:
        def __init__(self, rows):
            self.rows = rows

        def fetchall(self):
            return self.rows

    class Connection:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=()):
            normalized = " ".join(query.split())
            self.calls.append((normalized, params))
            if "GROUP BY stage" in normalized:
                count = 1 if "DISTINCT ON (case_id)" in normalized else 2
                return Result([{"stage": "received", "count": count}])
            if "FROM public.department_tasks" in normalized:
                return Result([])
            return Result([])

    connection = Connection()

    @contextmanager
    def connection_factory():
        yield connection

    payload = CollaborationRepository(connection_factory).dashboard(
        date(2026, 8, 1), date(2026, 8, 18)
    )

    assert payload["stage_counts"] == [{"stage": "received", "count": 1}]
    assert all(
        date(2026, 8, 1) in params and date(2026, 8, 18) in params
        for _, params in connection.calls
    )
