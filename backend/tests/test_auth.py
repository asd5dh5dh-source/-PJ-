from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.auth import WriterContext, require_writer
from app.config import get_settings
from app.db import WriterAttemptStore
from app.main import create_app


@dataclass
class InMemoryWriterAttemptStore:
    attempts: list[tuple[str, str, bool]] = field(default_factory=list)

    def record_and_check_locked(
        self, writer_name: str, client_ip: str, succeeded: bool
    ) -> bool:
        failures = 0
        for _, attempted_ip, attempt_succeeded in reversed(self.attempts):
            if attempted_ip != client_ip:
                continue
            if attempt_succeeded:
                break
            failures += 1
        if failures >= 5:
            return True
        self.attempts.append((writer_name, client_ip, succeeded))
        return False


def test_attempt_store_locks_and_records_in_one_ip_keyed_transaction(
    monkeypatch,
):
    class Result:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self):
            self.calls = []

        def execute(self, query, params):
            self.calls.append((query, params))
            if "failure_count" in query:
                return Result({"failure_count": 4})
            return Result()

    connection = Connection()

    @contextmanager
    def fake_connection():
        yield connection

    monkeypatch.setattr("app.db.database_connection", fake_connection)

    assert (
        WriterAttemptStore().record_and_check_locked(
            "Kim", "198.51.100.10", False
        )
        is False
    )
    assert "pg_advisory_xact_lock" in connection.calls[0][0]
    assert connection.calls[0][1] == ("198.51.100.10",)
    assert connection.calls[1][1] == ("198.51.100.10", "198.51.100.10")
    assert connection.calls[2][1] == ("Kim", "198.51.100.10", False)


@pytest.fixture
def writer_app(monkeypatch):
    monkeypatch.setenv("VOC_DB_PASSWORD", "local-secret")
    monkeypatch.setenv("VOC_RUNTIME_PROFILE", "external_review")
    monkeypatch.setenv(
        "VOC_WRITER_PASSWORD_HASH",
        "9246aa9be8de7b40d64eb664986430793b6cc13a19d2a456981e44f28303f9cf",
    )
    get_settings.cache_clear()
    app = create_app()
    app.state.writer_attempt_store = InMemoryWriterAttemptStore()
    yield app
    get_settings.cache_clear()


@pytest.fixture
def protected_client(writer_app):
    @writer_app.get("/protected", response_model=WriterContext)
    def protected(
        writer: Annotated[WriterContext, Depends(require_writer)],
    ) -> WriterContext:
        return writer

    return TestClient(writer_app)


def test_writer_dependency_accepts_protected_request_headers(protected_client):
    response = protected_client.get(
        "/protected",
        headers={
            "X-Writer-Name": "Kim",
            "X-Writer-Password": "correct-password",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"writer_name": "Kim"}


def test_writer_dependency_rejects_missing_headers(protected_client):
    assert protected_client.get("/protected").status_code == 401


def test_writer_dependency_rejects_invalid_header_values(protected_client):
    response = protected_client.get(
        "/protected",
        headers={
            "X-Writer-Name": "K" * 201,
            "X-Writer-Password": "correct-password",
        },
    )

    assert response.status_code == 401


def test_valid_password_returns_writer_context_without_password(writer_app):
    response = TestClient(writer_app).post(
        "/api/writer/verify",
        json={"writer_name": "Kim", "password": "correct-password"},
    )

    assert response.status_code == 200
    assert response.json() == {"writer_name": "Kim"}


def test_five_invalid_passwords_lock_writer_for_fifteen_minutes(writer_app):
    client = TestClient(writer_app)

    for _ in range(5):
        response = client.post(
            "/api/writer/verify",
            json={"writer_name": "Kim", "password": "wrong"},
        )
        assert response.status_code == 401

    locked = client.post(
        "/api/writer/verify",
        json={"writer_name": "Kim", "password": "wrong"},
    )
    assert locked.status_code == 429


def test_lock_is_keyed_by_client_ip_not_arbitrary_writer_name(writer_app):
    shared_store = writer_app.state.writer_attempt_store
    first_ip = TestClient(writer_app, client=("198.51.100.10", 50000))
    second_ip = TestClient(writer_app, client=("198.51.100.11", 50000))

    for writer_name in ["Kim", "Lee", "Park", "Choi", "Jung"]:
        assert first_ip.post(
            "/api/writer/verify",
            json={"writer_name": writer_name, "password": "wrong"},
        ).status_code == 401

    assert first_ip.post(
        "/api/writer/verify",
        json={"writer_name": "Another Name", "password": "wrong"},
    ).status_code == 429
    assert second_ip.post(
        "/api/writer/verify",
        json={"writer_name": "Kim", "password": "wrong"},
    ).status_code == 401
    assert len(shared_store.attempts) == 6
