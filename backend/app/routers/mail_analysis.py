from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import ArchiveQuery, MailAnalysis, MailAnalysisRequest
from app.services.mail_parser import parse_sender
from app.services.search import ArchiveSearchService
from app.services.translation import TranslationService


def create_mail_analysis_router(
    search_service: ArchiveSearchService,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["mail analysis"])

    @router.post("/mail-analysis", response_model=MailAnalysis)
    def analyze_mail(
        payload: MailAnalysisRequest,
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        first_pass = search_service.search_archive(
            ArchiveQuery(
                q=payload.original_mail_body,
                final_status="closed",
                sort="relevance",
                page_size=3,
            ),
            "relevance",
        )
        suggested = first_pass["items"][0] if first_pass["items"] else {}
        ranked = search_service.search_archive(
            ArchiveQuery(
                q=payload.original_mail_body,
                final_status="closed",
                boost_voc_subtype=suggested.get("voc_subtype"),
                sort="relevance",
                page_size=3,
            ),
            "relevance",
        )
        translation = TranslationService(settings).translate(payload.original_mail_body)
        return {
            **parse_sender(payload.original_mail_body),
            "translation_draft": translation["translated_text"],
            "translation_status": translation["status"],
            "suggested_voc_type": suggested.get("voc_type"),
            "suggested_voc_subtype": suggested.get("voc_subtype"),
            "suggested_product_equipment": suggested.get("product_equipment"),
            "items": ranked["items"],
        }

    return router
