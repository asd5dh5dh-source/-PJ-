import csv
from datetime import date
from io import StringIO
from xml.etree.ElementTree import fromstring
from zipfile import ZipFile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


WRITER_HEADERS = {
    "X-Writer-Name": "Kim",
    "X-Writer-Password": "correct-password",
}


CASES = [
    {
        "case_id": "COM-001",
        "customer_name": "알파",
        "product_equipment": "NCM811",
        "voc_type": "Complaint",
        "voc_subtype": "Cell Low Voltage",
        "customer_request": "Cell low voltage alarm",
        "responsible_departments": "Quality",
        "received_at": date(2026, 1, 2),
        "final_status": "closed",
        "record_origin": "historical",
    }
]


class AlwaysUnlockedWriterAttemptStore:
    def record_and_check_locked(self, writer_name, client_ip, succeeded):
        return False


class ExportRepository:
    def list_candidates(self, filters=None, **filter_values):
        return CASES

    def get(self, case_id):
        return None


class OperationsRepository:
    def dashboard(self, date_from, date_to):
        return {"stage_counts": [], "due_tasks": [], "recent_requests": []}

    def list_notifications(self):
        return []


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
def client():
    app = create_app(
        ExportRepository(), collaboration_repository=OperationsRepository()
    )
    app.state.writer_attempt_store = AlwaysUnlockedWriterAttemptStore()
    return TestClient(app)


@pytest.mark.parametrize(
    "path", ["/api/export/archive.csv", "/api/export/archive.xlsx"]
)
def test_export_requires_writer_headers(client, path):
    assert client.get(path).status_code == 401


def test_csv_export_contains_archive_rows_and_utf8_bom(client):
    response = client.get("/api/export/archive.csv", headers=WRITER_HEADERS)
    rows = list(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert rows == [
        {
            "case_id": "COM-001",
            "customer_name": "알파",
            "product_equipment": "NCM811",
            "voc_type": "Complaint",
            "voc_subtype": "Cell Low Voltage",
            "customer_request": "Cell low voltage alarm",
            "responsible_departments": "Quality",
            "received_at": "2026-01-02",
            "final_status": "closed",
            "record_origin": "historical",
        }
    ]


def test_xlsx_export_is_a_valid_single_sheet_office_archive(client):
    response = client.get("/api/export/archive.xlsx", headers=WRITER_HEADERS)

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    with ZipFile(BytesIO(response.content)) as workbook:
        assert set(workbook.namelist()) == {
            "[Content_Types].xml",
            "_rels/.rels",
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels",
            "xl/worksheets/sheet1.xml",
        }
        sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "COM-001" in sheet
    assert "알파" in sheet


def test_csv_export_prefixes_formula_like_values(client, monkeypatch):
    monkeypatch.setitem(CASES[0], "customer_name", "=HYPERLINK(\"bad\")")

    response = client.get("/api/export/archive.csv", headers=WRITER_HEADERS)
    row = next(csv.DictReader(StringIO(response.content.decode("utf-8-sig"))))

    assert row["customer_name"] == "'=HYPERLINK(\"bad\")"


def test_xlsx_export_removes_xml_invalid_control_characters(client, monkeypatch):
    monkeypatch.setitem(CASES[0], "customer_request", "bad\x00control")

    response = client.get("/api/export/archive.xlsx", headers=WRITER_HEADERS)
    with ZipFile(BytesIO(response.content)) as workbook:
        sheet = workbook.read("xl/worksheets/sheet1.xml")

    fromstring(sheet)
    assert b"\x00" not in sheet


def test_csv_export_uses_archive_keyword_ranking_and_requested_sort():
    cases = [
        {
            **CASES[0],
            "case_id": "OLD-NO-MATCH",
            "customer_request": "Voltage review",
            "original_mail_body": "Please review voltage.",
            "full_response_history": "Voltage was reviewed.",
            "received_at": date(2026, 1, 1),
        },
        {
            **CASES[0],
            "case_id": "NEW-GAS",
            "customer_request": "Gas generation during storage",
            "original_mail_body": "Please investigate gas generation.",
            "full_response_history": "Gas containment was shared.",
            "received_at": date(2026, 2, 1),
        },
    ]

    class SemanticRepository(ExportRepository):
        def list_candidates(self, filters=None, **filter_values):
            return cases

    app = create_app(
        SemanticRepository(), collaboration_repository=OperationsRepository()
    )
    app.state.writer_attempt_store = AlwaysUnlockedWriterAttemptStore()
    semantic_client = TestClient(app)

    ranked = semantic_client.get(
        "/api/export/archive.csv",
        headers=WRITER_HEADERS,
        params={"q": "gas generation", "sort": "relevance"},
    )
    oldest = semantic_client.get(
        "/api/export/archive.csv",
        headers=WRITER_HEADERS,
        params={"sort": "oldest"},
    )

    assert [row["case_id"] for row in csv.DictReader(StringIO(ranked.content.decode("utf-8-sig")))] == [
        "NEW-GAS",
        "OLD-NO-MATCH",
    ]
    assert [row["case_id"] for row in csv.DictReader(StringIO(oldest.content.decode("utf-8-sig")))] == [
        "OLD-NO-MATCH",
        "NEW-GAS",
    ]
