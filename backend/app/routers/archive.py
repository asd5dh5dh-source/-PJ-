from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ArchiveDetail, ArchivePage, ArchiveQuery
from app.services.search import ArchiveSearchService


def create_archive_router(
    repository: Any,
    search_service: ArchiveSearchService,
    collaboration_repository: Any | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/archive", tags=["archive"])

    @router.get("", response_model=ArchivePage)
    def list_archive(query: Annotated[ArchiveQuery, Query()]):
        effective_sort = query.sort or ("relevance" if query.q else "latest")
        current_items = (
            collaboration_repository.list_archive_items()
            if collaboration_repository is not None
            else []
        )
        return search_service.search_archive(query, effective_sort, current_items)

    @router.get("/{case_id}", response_model=ArchiveDetail)
    def get_archive_case(case_id: str):
        case = repository.get(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="사례를 찾을 수 없습니다.")
        return case

    return router
