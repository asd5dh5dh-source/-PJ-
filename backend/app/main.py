from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import FastAPI

from app.auth import router as writer_router
from app.repositories.collaboration import CollaborationRepository
from app.repositories.voc_cases import VocCaseRepository
from app.routers.archive import create_archive_router
from app.routers.collaboration import create_collaboration_router
from app.routers.requests import create_requests_router
from app.services.search import ArchiveSearchService


def create_app(
    repository: Any | None = None,
    receipt_date: Callable[[], date] = date.today,
    collaboration_repository: Any | None = None,
) -> FastAPI:
    repository = repository if repository is not None else VocCaseRepository()
    search_service = ArchiveSearchService(repository)
    app = FastAPI(title="Local VOC Archive")
    app.include_router(writer_router)
    app.include_router(create_archive_router(repository, search_service))
    app.include_router(create_requests_router(repository, search_service, receipt_date))
    app.include_router(
        create_collaboration_router(
            collaboration_repository
            if collaboration_repository is not None
            else CollaborationRepository(),
            receipt_date,
        )
    )
    return app


app = create_app()
