import re
from email.parser import Parser
from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas import ArchiveQuery, MailAnalysis, MailAnalysisRequest
from app.services.mail_parser import parse_sender
from app.services.search import ArchiveSearchService
from app.services.translation import TranslationService
from app.services.text import tokenize


_COMMON_MAIL_WORDS = {"please", "kindly", "dear", "regards", "thanks", "thank", "from", "company", "subject", "sent", "mailto"}


def _issue_keywords(raw_mail: str) -> list[str]:
    body = raw_mail.split("\n\n", 1)[-1]
    return list(dict.fromkeys(
        token for token in tokenize(body)
        if len(token) > 2 and token not in _COMMON_MAIL_WORDS
    ))[:12]


def _request_summary(raw_mail: str) -> str:
    message = Parser().parsestr(raw_mail)
    subject = message.get("subject", "").strip()
    if subject:
        return subject
    body = raw_mail.split("\n\n", 1)[-1]
    return " ".join(body.split())[:500]


def _product_equipment(raw_mail: str, suggested: dict) -> str | None:
    if suggested.get("product_equipment"):
        return suggested["product_equipment"]
    match = re.search(r"\b(NCA|NCM\d*|NCMA|LFP|LMFP)\b", raw_mail, re.I)
    return match.group(1).upper() if match else None


def _departments(value: str | None) -> list[str]:
    return [part.strip() for part in re.split(r"[,/，]", value or "") if part.strip()]


def create_mail_analysis_router(
    search_service: ArchiveSearchService,
) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["mail analysis"])

    @router.post("/mail-analysis", response_model=MailAnalysis)
    def analyze_mail(
        payload: MailAnalysisRequest,
        settings: Annotated[Settings, Depends(get_settings)],
    ):
        keywords = _issue_keywords(payload.original_mail_body)
        issue_query = " ".join(keywords) or payload.original_mail_body
        first_pass = search_service.search_archive(
            ArchiveQuery(
                q=issue_query,
                final_status="closed",
                sort="relevance",
                page_size=3,
            ),
            "relevance",
        )
        suggested = first_pass["items"][0] if first_pass["items"] else {}
        ranked = search_service.search_archive(
            ArchiveQuery(
                q=issue_query,
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
            "suggested_product_equipment": _product_equipment(
                payload.original_mail_body, suggested
            ),
            "suggested_customer_request": _request_summary(payload.original_mail_body),
            "suggested_priority": "high"
            if str(suggested.get("priority", "")).lower() in {"high", "높음"}
            else "normal",
            "suggested_departments": _departments(
                suggested.get("responsible_departments")
            ),
            "extracted_keywords": keywords,
            "items": ranked["items"],
        }

    return router
