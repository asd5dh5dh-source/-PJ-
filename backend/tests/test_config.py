import pytest

from app.config import Settings


def test_only_training_database_is_allowed(monkeypatch):
    """Rejecting another database keeps runtime writes in the training DB."""
    monkeypatch.setenv("VOC_DB_NAME", "테스트용 Data")

    with pytest.raises(ValueError, match="학습용 Data"):
        Settings()


def test_training_database_builds_dsn(monkeypatch):
    """The allowed database name is safely URL-encoded in its DSN."""
    monkeypatch.setenv("VOC_DB_NAME", "학습용 Data")
    monkeypatch.setenv("VOC_DB_PASSWORD", "local-secret")

    settings = Settings()

    assert "%ED%95%99%EC%8A%B5%EC%9A%A9%20Data" in settings.database_dsn()
