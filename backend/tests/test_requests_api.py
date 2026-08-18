from copy import deepcopy
from datetime import date
import re

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


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

    def create(self, values):
        self.created_values = dict(values)
        created = dict(values)
        self.cases.append(created)
        return created

    def get(self, case_id):
        return next((case for case in self.cases if case["case_id"] == case_id), None)

    def list_candidates(self, filters=None, **filter_values):
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


@pytest.fixture
def client(repository):
    return TestClient(create_app(repository))


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
