from collections.abc import Callable
from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.schemas import ArchiveDetail, ManualRequest, SimilarCases
from app.services.search import ArchiveSearchService


def create_requests_router(
    repository: Any,
    search_service: ArchiveSearchService,
    receipt_date: Callable[[], date],
) -> APIRouter:
    router = APIRouter(prefix="/api/requests", tags=["requests"])

    @router.post("", response_model=ArchiveDetail, status_code=status.HTTP_201_CREATED)
    def create_request(payload: ManualRequest):
        values = payload.model_dump(exclude_none=True)
        values.update(
            {
                "case_id": f"WEB-{uuid4().hex[:12].upper()}",
                "record_origin": "user_input",
                "final_status": "received",
                "search_document": " ".join(
                    filter(
                        None,
                        [payload.customer_request, payload.original_mail_body],
                    )
                ),
            }
        )
        values.setdefault("received_at", receipt_date())
        created = repository.create(values)
        search_service.invalidate()
        return created

    @router.get("/{case_id}/similar-cases", response_model=SimilarCases)
    def list_similar_cases(case_id: str):
        source_case = repository.get(case_id)
        if source_case is None:
            raise HTTPException(status_code=404, detail="Case not found.")
        candidates = repository.list_candidates(
            final_status="closed",
            exclude_case_id=case_id,
        )
        return {
            "items": search_service.rank_similar(source_case, candidates, limit=3)
        }

    return router
