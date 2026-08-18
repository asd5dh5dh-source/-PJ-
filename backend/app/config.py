from functools import lru_cache
import re
from typing import Literal
from urllib.parse import quote

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    runtime_profile: Literal["external_review", "internal"] = Field(
        default="external_review", validation_alias="VOC_RUNTIME_PROFILE"
    )
    voc_database_url: SecretStr = SecretStr("")
    voc_writer_password_hash: SecretStr = SecretStr("")
    voc_db_host: str = "localhost"
    voc_db_port: int = 5432
    voc_db_name: str = "학습용 Data"
    voc_db_user: str = "postgres"
    voc_db_password: SecretStr = SecretStr("")
    voc_smtp_host: str = ""
    voc_smtp_port: int = 25
    voc_smtp_username: str = ""
    voc_smtp_password: SecretStr = SecretStr("")
    voc_smtp_from: str = ""

    @model_validator(mode="before")
    @classmethod
    def reject_non_training_database(cls, values):
        database_url = values.get(
            "voc_database_url", values.get("VOC_DATABASE_URL", "")
        )
        if not database_url and values.get(
            "voc_db_name", values.get("VOC_DB_NAME", "학습용 Data")
        ) != "학습용 Data":
            raise ValueError("VOC_DB_NAME must be 학습용 Data")
        return values

    @model_validator(mode="after")
    def validate_writer_password_hash(self):
        password_hash = self.voc_writer_password_hash.get_secret_value()
        if password_hash and not re.fullmatch(r"[0-9a-fA-F]{64}", password_hash):
            raise ValueError("VOC_WRITER_PASSWORD_HASH must be SHA-256 hexadecimal")
        return self

    @property
    def mail_delivery_enabled(self) -> bool:
        return self.runtime_profile == "internal"

    @property
    def smtp_configured(self) -> bool:
        return self.mail_delivery_enabled and bool(
            self.voc_smtp_host and self.voc_smtp_from
        )

    def database_dsn(self) -> str:
        database_url = self.voc_database_url.get_secret_value()
        if database_url:
            return database_url
        password = quote(self.voc_db_password.get_secret_value(), safe="")
        database = quote(self.voc_db_name, safe="")
        return f"postgresql://{self.voc_db_user}:{password}@{self.voc_db_host}:{self.voc_db_port}/{database}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
