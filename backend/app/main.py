from typing import Any

from fastapi import FastAPI

from app.repositories.voc_cases import VocCaseRepository
from app.routers.archive import create_archive_router


def create_app(repository: Any | None = None) -> FastAPI:
    app = FastAPI(title="Local VOC Archive")
    app.include_router(create_archive_router(repository or VocCaseRepository()))
    return app


app = create_app()
