from contextlib import contextmanager

import pytest

from app.repositories import voc_cases
from app.repositories.voc_cases import VocCaseRepository


class FakeConnection:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def execute(self, query, params=()):
        self.calls.append((query, params))
        return self

    def fetchone(self):
        return self.row

    def fetchall(self):
        return [self.row]


def use_connection(monkeypatch, connection):
    @contextmanager
    def fake_database_connection():
        yield connection

    monkeypatch.setattr(voc_cases, "database_connection", fake_database_connection)


@pytest.fixture
def repository():
    return VocCaseRepository()


@pytest.mark.localdb
def test_training_database_contains_only_expected_seed_rows(repository):
    summary = repository.dataset_summary()
    assert summary.database_name == "학습용 Data"
    assert summary.historical_count == 135
    assert summary.duplicate_case_ids == 0
    assert summary.missing_product_equipment == 0


def test_list_candidates_parameterizes_supported_filters(monkeypatch):
    connection = FakeConnection({"case_id": "VOC-001"})
    use_connection(monkeypatch, connection)

    rows = VocCaseRepository().list_candidates(
        {"voc_subtype": "Gas Generation", "final_status": "closed"}
    )

    query, params = connection.calls[0]
    assert rows == [{"case_id": "VOC-001"}]
    assert "voc_subtype = %s" in query
    assert "final_status = %s" in query
    assert params == ("Gas Generation", "closed")


def test_responsible_department_filter_uses_existing_plural_column(monkeypatch):
    connection = FakeConnection({"case_id": "VOC-001"})
    use_connection(monkeypatch, connection)

    VocCaseRepository().list_candidates({"responsible_department": "Quality"})

    query, params = connection.calls[0]
    assert "responsible_departments = %s" in query
    assert params == ("Quality",)


def test_get_parameterizes_case_id(monkeypatch):
    connection = FakeConnection({"case_id": "VOC-001"})
    use_connection(monkeypatch, connection)

    row = VocCaseRepository().get("VOC-001' OR TRUE --")

    query, params = connection.calls[0]
    assert row == {"case_id": "VOC-001"}
    assert "case_id = %s" in query
    assert params == ("VOC-001' OR TRUE --",)


def test_create_parameterizes_confirmed_fields(monkeypatch):
    connection = FakeConnection({"case_id": "WEB-001"})
    use_connection(monkeypatch, connection)
    payload = {
        "case_id": "WEB-001",
        "customer_request": "Gas generation inquiry",
        "record_origin": "user_input",
        "final_status": "received",
        "search_document": "Gas generation inquiry",
        "responsible_departments": "Quality",
    }

    row = VocCaseRepository().create(payload)

    query, params = connection.calls[0]
    assert row == {"case_id": "WEB-001"}
    assert "RETURNING *" in query
    assert params == tuple(payload.values())
