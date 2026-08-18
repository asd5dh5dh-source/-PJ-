from app.config import Settings


def test_external_review_profile_uses_deployed_database_without_active_integrations(
    monkeypatch,
):
    """External review can use hosted data but cannot activate SMTP or a local model."""
    monkeypatch.setenv("VOC_RUNTIME_PROFILE", "external_review")
    monkeypatch.setenv(
        "VOC_DATABASE_URL", "postgresql://review:secret@db.example.test/voc"
    )
    monkeypatch.setenv("VOC_SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("VOC_SMTP_FROM", "voc@example.test")
    monkeypatch.setenv("VOC_TRANSLATION_COMMAND", "local-translator")
    monkeypatch.setenv("VOC_TRANSLATION_MODEL_PATH", "/models/ko")

    settings = Settings()

    assert settings.database_dsn() == "postgresql://review:secret@db.example.test/voc"
    assert settings.mail_delivery_enabled is False
    assert settings.smtp_configured is False
    assert settings.translation_configured is False


def test_internal_profile_enables_only_fully_configured_integrations(monkeypatch):
    """Internal smoke configuration exposes the explicitly supplied local capabilities."""
    monkeypatch.setenv("VOC_RUNTIME_PROFILE", "internal")
    monkeypatch.setenv(
        "VOC_DATABASE_URL", "postgresql://voc:secret@postgres.internal/voc"
    )
    monkeypatch.setenv("VOC_SMTP_HOST", "smtp.internal")
    monkeypatch.setenv("VOC_SMTP_FROM", "voc@internal.example")
    monkeypatch.setenv("VOC_TRANSLATION_COMMAND", "local-translator")
    monkeypatch.setenv("VOC_TRANSLATION_MODEL_PATH", "C:/models/ko")

    settings = Settings()

    assert settings.database_dsn() == "postgresql://voc:secret@postgres.internal/voc"
    assert settings.mail_delivery_enabled is True
    assert settings.smtp_configured is True
    assert settings.translation_configured is True
