from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import date
import re
from threading import Event, Lock

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.repositories.voc_cases import VocCaseRepository
from app.services.search import ArchiveSearchService


VALID_REQUEST = {
    "customer_name": "Battery Customer",
    "product_equipment": "NCA",
    "voc_type": "Complaint",
    "voc_subtype": "Gas Generation",
    "customer_request": "Gas generation during storage",
    "original_mail_body": "Please investigate the gas generation issue.",
    "responsible_departments": "Quality",
    "received_at": "2026-08-14",
}

WRITER_HEADERS = {
    "X-Writer-Name": "Kim",
    "X-Writer-Password": "correct-password",
}


class AlwaysUnlockedWriterAttemptStore:
    def record_and_check_locked(
        self, writer_name: str, client_ip: str, succeeded: bool
    ) -> bool:
        return False


class FakeCollaborationRepository:
    def list_archive_items(self):
        return []


CASES = [
    {
        "case_id": f"CLOSED-{number}",
        "customer_name": f"Customer {number}",
        "product_equipment": "NCA",
        "voc_type": "Complaint",
        "voc_subtype": "Gas Generation" if number == 1 else "Other",
        "customer_request": (
            "Gas generation investigation"
            if number == 1
            else f"Unrelated cell voltage report {number}"
        ),
        "original_mail_body": (
            "Please investigate the gas issue."
            if number == 1
            else "The voltage report was reviewed."
        ),
        "full_response_history": "The closed investigation was completed.",
        "responsible_departments": "Quality",
        "received_at": date(2026, number, 1),
        "final_status": "closed",
        "record_origin": "historical",
    }
    for number in range(1, 5)
] + [
    {
        "case_id": "OPEN-1",
        "customer_name": "Open Customer",
        "product_equipment": "NCA",
        "voc_type": "Complaint",
        "voc_subtype": "Gas Generation",
        "customer_request": "Gas generation gas generation gas generation",
        "original_mail_body": "Urgent gas generation investigation.",
        "full_response_history": "Still investigating.",
        "responsible_departments": "Quality",
        "received_at": date(2026, 5, 1),
        "final_status": "in_progress",
        "record_origin": "historical",
    }
]


class FakeRepository:
    def __init__(self):
        self.cases = deepcopy(CASES)
        self.created_values = None
        self.filters_history = []
        self.list_error = None

    def create(self, values):
        self.created_values = dict(values)
        created = dict(values)
        self.cases.append(created)
        return created

    def get(self, case_id):
        return next((case for case in self.cases if case["case_id"] == case_id), None)

    def list_candidates(self, filters=None, **filter_values):
        if self.list_error is not None:
            raise self.list_error
        selected = dict(filters or {}) | filter_values
        self.filters_history.append(selected)
        return [
            case
            for case in self.cases
            if all(
                case.get(
                    "responsible_departments"
                    if key == "responsible_department"
                    else key
                )
                == value
                for key, value in selected.items()
                if key not in {"received_from", "received_to", "exclude_case_id"}
            )
            and (
                selected.get("exclude_case_id") is None
                or case["case_id"] != selected["exclude_case_id"]
            )
        ]


@pytest.fixture
def repository():
    return FakeRepository()


@pytest.fixture(autouse=True)
def writer_environment(monkeypatch):
    monkeypatch.setenv(
        "VOC_WRITER_PASSWORD_HASH",
        "9246aa9be8de7b40d64eb664986430793b6cc13a19d2a456981e44f28303f9cf",
    )
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def authenticated_client(app):
    app.state.writer_attempt_store = AlwaysUnlockedWriterAttemptStore()
    return TestClient(app, headers=WRITER_HEADERS)


@pytest.fixture
def client(repository):
    return authenticated_client(
        create_app(
            repository,
            collaboration_repository=FakeCollaborationRepository(),
        )
    )


def test_manual_request_requires_writer_headers(repository):
    response = TestClient(create_app(repository)).post(
        "/api/requests", json=VALID_REQUEST
    )

    assert response.status_code == 401
    assert repository.created_values is None


def test_manual_request_is_stored_as_user_input(client, repository):
    response = client.post("/api/requests", json=VALID_REQUEST)

    assert response.status_code == 201
    assert re.fullmatch(r"WEB-[0-9A-F]{12}", response.json()["case_id"])
    assert response.json()["record_origin"] == "user_input"
    assert response.json()["final_status"] == "received"
    assert repository.created_values == {
        "case_id": response.json()["case_id"],
        "customer_request": "Gas generation during storage",
        "record_origin": "user_input",
        "final_status": "received",
        "search_document": (
            "Gas generation during storage "
            "Please investigate the gas generation issue."
        ),
        "original_mail_body": "Please investigate the gas generation issue.",
        "customer_name": "Battery Customer",
        "product_equipment": "NCA",
        "voc_type": "Complaint",
        "voc_subtype": "Gas Generation",
        "responsible_departments": "Quality",
        "received_at": date(2026, 8, 14),
    }


@pytest.mark.parametrize(
    "field",
    [
        "customer_name",
        "voc_type",
        "voc_subtype",
        "customer_request",
        "original_mail_body",
    ],
)
def test_manual_request_rejects_missing_required_fields(client, field):
    payload = VALID_REQUEST | {}
    payload.pop(field)

    response = client.post("/api/requests", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "field",
    [
        "customer_name",
        "voc_type",
        "voc_subtype",
        "customer_request",
        "original_mail_body",
    ],
)
def test_manual_request_rejects_whitespace_only_required_fields(client, field):
    response = client.post("/api/requests", json=VALID_REQUEST | {field: " \t "})

    assert response.status_code == 422


def test_manual_request_assigns_server_receipt_date_when_missing(repository):
    client = authenticated_client(
        create_app(repository, receipt_date=lambda: date(2026, 8, 18))
    )
    payload = VALID_REQUEST | {}
    payload.pop("received_at")

    response = client.post("/api/requests", json=payload)

    assert response.status_code == 201
    assert response.json()["received_at"] == "2026-08-18"
    assert repository.created_values["received_at"] == date(2026, 8, 18)


def test_top_three_uses_closed_cases_only(client, repository):
    case_id = client.post("/api/requests", json=VALID_REQUEST).json()["case_id"]

    response = client.get(f"/api/requests/{case_id}/similar-cases")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 3
    assert all(item["final_status"] == "closed" for item in response.json()["items"])
    assert repository.filters_history[-1] == {
        "final_status": "closed",
        "exclude_case_id": case_id,
    }
    subtype_match = next(
        item for item in response.json()["items"] if item["case_id"] == "CLOSED-1"
    )
    assert subtype_match["final_score"] == pytest.approx(
        subtype_match["bm25_score"] * 1.1
    )


def test_creation_refreshes_once_and_next_archive_search_reuses_it(client, repository):
    client.get("/api/archive", params={"q": "gas generation"})
    response = client.post("/api/requests", json=VALID_REQUEST)

    refreshed_response = client.get("/api/archive", params={"q": "gas generation"})

    assert len(repository.filters_history) == 2
    assert response.json()["case_id"] in {
        item["case_id"] for item in refreshed_response.json()["items"]
    }


def test_creation_survives_unavailable_refresh_and_later_search_reloads(client, repository):
    client.get("/api/archive", params={"q": "gas generation"})
    repository.list_error = RuntimeError("temporary read failure")

    response = client.post("/api/requests", json=VALID_REQUEST)

    assert response.status_code == 201
    repository.list_error = None
    refreshed_response = client.get("/api/archive", params={"q": "gas generation"})
    assert response.json()["case_id"] in {
        item["case_id"] for item in refreshed_response.json()["items"]
    }


def test_repository_enforces_manual_origin_and_status(monkeypatch):
    class Result:
        def fetchone(self):
            return {"case_id": "WEB-ABC123ABC123"}

    class Connection:
        def execute(self, query, params):
            self.query = query
            self.params = params
            return Result()

    connection = Connection()

    @contextmanager
    def fake_connection():
        yield connection

    monkeypatch.setattr(
        "app.repositories.voc_cases.database_connection",
        fake_connection,
    )

    VocCaseRepository().create(
        {
            "case_id": "WEB-ABC123ABC123",
            "customer_request": "Manual request",
            "record_origin": "historical",
            "final_status": "closed",
            "search_document": "Manual request Mail body",
            "original_mail_body": "Mail body",
            "request_embedding": [1.0],
            "response_embedding": [1.0],
        }
    )

    assert connection.params == (
        "WEB-ABC123ABC123",
        "Manual request",
        "user_input",
        "received",
        "Manual request Mail body",
        "Mail body",
    )
    assert "embedding" not in connection.query


def test_shared_search_state_serializes_refresh_and_rank():
    class CollisionDetectingIndex:
        def __init__(self):
            self.entered = Event()
            self.release = Event()
            self.overlap = Event()
            self.guard = Lock()
            self.active = False

        def _access(self):
            with self.guard:
                if self.active:
                    self.overlap.set()
                self.active = True
                self.entered.set()
            self.release.wait(timeout=2)
            with self.guard:
                self.active = False

        def refresh(self, candidates):
            self._access()

        def rank(self, query, candidates, query_subtype, limit):
            self._access()
            return []

    index = CollisionDetectingIndex()
    service = ArchiveSearchService(FakeRepository(), index)

    with ThreadPoolExecutor(max_workers=2) as executor:
        rank = executor.submit(
            service.rank_similar,
            {
                "customer_request": "Gas generation",
                "voc_subtype": "Gas Generation",
            },
            [],
            3,
        )
        assert index.entered.wait(timeout=1)
        refresh = executor.submit(service.refresh)
        try:
            overlap_detected = index.overlap.wait(timeout=0.2)
        finally:
            index.release.set()
        rank.result(timeout=1)
        refresh.result(timeout=1)

    assert not overlap_detected
