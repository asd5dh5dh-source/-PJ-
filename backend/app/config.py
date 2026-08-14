from functools import lru_cache
from urllib.parse import quote

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    voc_db_host: str = "localhost"
    voc_db_port: int = 5432
    voc_db_name: str = "학습용 Data"
    voc_db_user: str = "postgres"
    voc_db_password: SecretStr

    @model_validator(mode="before")
    @classmethod
    def reject_non_training_database(cls, values):
        if values.get("voc_db_name", values.get("VOC_DB_NAME", "학습용 Data")) != "학습용 Data":
            raise ValueError("VOC_DB_NAME must be 학습용 Data")
        return values

    def database_dsn(self) -> str:
        password = quote(self.voc_db_password.get_secret_value(), safe="")
        database = quote(self.voc_db_name, safe="")
        return f"postgresql://{self.voc_db_user}:{password}@{self.voc_db_host}:{self.voc_db_port}/{database}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
