import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.mark.localdb
def test_archive_reads_training_rows_without_writing(client):
    response = client.get("/api/archive")

    assert response.status_code == 200
    archive = response.json()
    assert archive["total"] == 135
    assert all(item["case_id"] for item in archive["items"])
