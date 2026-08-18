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

    def recent_failure_count(self, writer_name: str, client_ip: str) -> int:
        failures = 0
        for attempted_writer, attempted_ip, succeeded in reversed(self.attempts):
            if (attempted_writer, attempted_ip) != (writer_name, client_ip):
                continue
            if succeeded:
                break
            failures += 1
        return failures

    def record_attempt(
        self, writer_name: str, client_ip: str, succeeded: bool
    ) -> None:
        self.attempts.append((writer_name, client_ip, succeeded))


def test_attempt_store_uses_an_unambiguous_parameterized_lockout_query(
    monkeypatch,
):
    class Result:
        def fetchone(self):
            return {"failure_count": 4}

    class Connection:
        def execute(self, query, params):
            assert "attempts.attempted_at >=" in query
            assert "attempts.attempted_at >" in query
            assert params == ("Kim", "198.51.100.10", "Kim", "198.51.100.10")
            return Result()

    @contextmanager
    def fake_connection():
        yield Connection()

    monkeypatch.setattr("app.db.database_connection", fake_connection)

    assert WriterAttemptStore().recent_failure_count("Kim", "198.51.100.10") == 4


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


def test_lock_is_scoped_to_writer_name_and_client_ip(writer_app):
    shared_store = writer_app.state.writer_attempt_store
    first_ip = TestClient(writer_app, client=("198.51.100.10", 50000))
    second_ip = TestClient(writer_app, client=("198.51.100.11", 50000))

    for _ in range(5):
        assert first_ip.post(
            "/api/writer/verify",
            json={"writer_name": "Kim", "password": "wrong"},
        ).status_code == 401

    assert first_ip.post(
        "/api/writer/verify",
        json={"writer_name": "Lee", "password": "wrong"},
    ).status_code == 401
    assert second_ip.post(
        "/api/writer/verify",
        json={"writer_name": "Kim", "password": "wrong"},
    ).status_code == 401
    assert len(shared_store.attempts) == 7
