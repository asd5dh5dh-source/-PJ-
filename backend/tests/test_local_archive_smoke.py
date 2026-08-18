import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.voc_cases import VocCaseRepository


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.mark.localdb
def test_archive_reads_training_rows_without_writing(client):
    summary = VocCaseRepository().dataset_summary()
    response = client.get("/api/archive")

    assert response.status_code == 200
    archive = response.json()
    assert summary.historical_count == 135
    assert archive["total"] >= summary.historical_count
    assert all(item["case_id"] for item in archive["items"])
