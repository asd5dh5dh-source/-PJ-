from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


CASES = [
    {
        "case_id": "COM-001",
        "customer_name": "Alpha",
        "product_equipment": "NCM811",
        "voc_type": "Complaint",
        "voc_subtype": "Cell Low Voltage",
        "customer_request": "Cell low voltage alarm",
        "original_mail_body": "The cell voltage is below the requested level.",
        "full_response_history": "Reviewed low voltage condition.",
        "responsible_departments": "Quality",
        "received_at": date(2026, 1, 2),
        "final_status": "closed",
        "record_origin": "historical",
    },
    {
        "case_id": "REQ-GAS",
        "customer_name": "Beta",
        "product_equipment": "NCA",
        "voc_type": "Inquiry",
        "voc_subtype": "Gas Generation",
        "customer_request": "Gas generation during storage",
        "original_mail_body": "Please investigate gas generation.",
        "full_response_history": "Containment was shared.",
        "responsible_departments": "Engineering",
        "received_at": date(2026, 2, 3),
        "final_status": "in_progress",
        "record_origin": "historical",
    },
]


class FakeRepository:
    def __init__(self):
        self.filters = None

    def list_candidates(self, filters=None, **filter_values):
        self.filters = dict(filters or {}) | filter_values
        return [
            case
            for case in CASES
            if all(
                case.get(
                    "responsible_departments"
                    if key == "responsible_department"
                    else key
                )
                == value
                for key, value in self.filters.items()
                if key not in {"received_from", "received_to"}
            )
        ]

    def get(self, case_id):
        return next((case for case in CASES if case["case_id"] == case_id), None)


@pytest.fixture
def repository():
    return FakeRepository()


@pytest.fixture
def client(repository):
    return TestClient(create_app(repository))


def test_archive_without_query_defaults_to_all_statuses_and_latest(client, repository):
    response = client.get("/api/archive")

    assert response.status_code == 200
    assert response.json()["sort"] == "latest"
    assert response.json()["items"][0]["received_at"] >= response.json()["items"][1]["received_at"]
    assert repository.filters == {}


def test_archive_query_defaults_to_relevance_and_keeps_filters(client, repository):
    response = client.get(
        "/api/archive",
        params={"q": "gas generation", "voc_subtype": "Gas Generation"},
    )

    assert response.status_code == 200
    assert response.json()["sort"] == "relevance"
    assert response.json()["items"][0]["matched_keywords"] == ["gas", "generation"]
    assert repository.filters == {"voc_subtype": "Gas Generation"}


def test_archive_reuses_candidates_for_an_identical_keyword_search(client, repository):
    repository.list_calls = 0
    original_list_candidates = repository.list_candidates

    def count_list_candidates(filters=None, **filter_values):
        repository.list_calls += 1
        return original_list_candidates(filters, **filter_values)

    repository.list_candidates = count_list_candidates

    client.get("/api/archive", params={"q": "gas generation"})
    client.get("/api/archive", params={"q": "gas generation"})

    assert repository.list_calls == 1


def test_archive_propagates_received_date_filters(client, repository):
    response = client.get(
        "/api/archive",
        params={"received_from": "2026-01-01", "received_to": "2026-01-31"},
    )

    assert response.status_code == 200
    assert repository.filters == {
        "received_from": date(2026, 1, 1),
        "received_to": date(2026, 1, 31),
    }


def test_archive_accepts_oldest_sort_without_a_query(client):
    response = client.get("/api/archive", params={"sort": "oldest"})

    assert response.status_code == 200
    assert [item["case_id"] for item in response.json()["items"]] == [
        "COM-001",
        "REQ-GAS",
    ]


@pytest.mark.parametrize(
    ("params", "expected_status"),
    [
        ({"sort": "newest"}, 422),
        ({"sort": "relevance"}, 422),
        ({"page_size": 101}, 422),
    ],
)
def test_archive_rejects_invalid_queries(client, params, expected_status):
    assert client.get("/api/archive", params=params).status_code == expected_status


def test_archive_defaults_to_twenty_items_per_page(client):
    response = client.get("/api/archive")

    assert response.status_code == 200
    assert response.json()["page_size"] == 20


def test_archive_detail_returns_the_case(client):
    response = client.get("/api/archive/COM-001")

    assert response.status_code == 200
    assert response.json()["original_mail_body"].startswith("The cell voltage")


def test_create_app_keeps_a_falsy_injected_repository(monkeypatch):
    class FalsyRepository(FakeRepository):
        def __bool__(self):
            return False

    repository = FalsyRepository()
    default_constructions = []
    monkeypatch.setattr(
        "app.main.VocCaseRepository",
        lambda: default_constructions.append(True) or FakeRepository(),
    )

    response = TestClient(create_app(repository)).get("/api/archive/COM-001")

    assert response.status_code == 200
    assert default_constructions == []


def test_archive_detail_returns_not_found(client):
    response = client.get("/api/archive/UNKNOWN")

    assert response.status_code == 404
    assert response.json()["detail"] == "사례를 찾을 수 없습니다."
