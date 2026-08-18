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


def test_external_profile_disables_real_mail(monkeypatch):
    """External review can only preview notifications, never deliver them."""
    monkeypatch.setenv("VOC_DB_PASSWORD", "local-secret")
    monkeypatch.setenv("VOC_RUNTIME_PROFILE", "external_review")

    assert getattr(Settings(), "mail_delivery_enabled", True) is False


def test_unknown_runtime_profile_is_rejected(monkeypatch):
    """A typo must not silently select a profile with unsafe capabilities."""
    monkeypatch.setenv("VOC_DB_PASSWORD", "local-secret")
    monkeypatch.setenv("VOC_RUNTIME_PROFILE", "public_with_mail")

    with pytest.raises(ValueError):
        Settings()


def test_internal_profile_allows_mail_delivery(monkeypatch):
    """Only the internal profile can hand notifications to a mail sender."""
    monkeypatch.setenv("VOC_DB_PASSWORD", "local-secret")
    monkeypatch.setenv("VOC_RUNTIME_PROFILE", "internal")

    assert getattr(Settings(), "mail_delivery_enabled", False) is True


def test_database_url_overrides_legacy_training_database_fields(monkeypatch):
    """Deployable profiles connect through the single injected database URL."""
    monkeypatch.setenv("VOC_DB_PASSWORD", "ignored-local-secret")
    monkeypatch.setenv(
        "VOC_DATABASE_URL", "postgresql://voc_user:secret@db.example.test/voc"
    )

    assert Settings().database_dsn() == (
        "postgresql://voc_user:secret@db.example.test/voc"
    )


def test_writer_password_hash_must_be_sha256_hex(monkeypatch):
    """Malformed password configuration fails before accepting protected writes."""
    monkeypatch.setenv("VOC_DB_PASSWORD", "local-secret")
    monkeypatch.setenv("VOC_WRITER_PASSWORD_HASH", "plain-text-password")

    with pytest.raises(ValueError, match="SHA-256"):
        Settings()
