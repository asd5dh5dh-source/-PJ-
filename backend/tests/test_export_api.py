import csv
from datetime import date
from io import StringIO
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
