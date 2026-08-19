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


_COMMON_MAIL_WORDS = {"please", "kindly", "dear", "regards", "thanks", "thank", "from", "company", "subject", "sent", "mailto", "was", "observed"}


def _explicit_voc_subtype(raw_mail: str) -> str | None:
    match = re.search(
        r"(?:\[\s*(?:문의\s*/\s*)?요청\s*주제\s*[:：]\s*([^\]\n]+)\]|(?:件名|Subject)\s*[:：]\s*([^\n]+))",
        raw_mail,
        re.I,
    )
    return " ".join(next(part for part in match.groups() if part is not None).split()) if match else None


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
    sentences = re.split(r"(?<=[.!?])\s*|\n+", body)
    requested = [
        " ".join(sentence.split())
        for sentence in sentences
        if re.search(
            r"회신|제출|확인.*(?:해|바랍니다)|검토.*(?:해|바랍니다)|조치.*(?:해|바랍니다)|제공.*(?:해|바랍니다)|please|request|provide|confirm|review|investigate",
            sentence,
            re.I,
        )
    ]
    return " ".join(requested or sentences).strip()[:500]


def _product_equipment(raw_mail: str, suggested: dict) -> str | None:
    match = re.search(r"\b(NCA|NCM\d*|NCMA|LFP|LMFP)\b", raw_mail, re.I)
    return match.group(1).upper() if match else suggested.get("product_equipment")


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
        explicit_subtype = _explicit_voc_subtype(payload.original_mail_body)
        subtype_history = (
            search_service.search_archive(
                ArchiveQuery(
                    voc_subtype=explicit_subtype,
                    final_status="closed",
                    page_size=1,
                ),
                "latest",
            )
            if explicit_subtype
            else {"items": []}
        )
        matched_subtype = explicit_subtype if subtype_history["items"] else None
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
        first_items = [item for item in first_pass["items"] if item["final_score"] > 0]
        suggested = first_items[0] if first_items else {}
        ranked = search_service.search_archive(
            ArchiveQuery(
                q=issue_query,
                final_status="closed",
                boost_voc_subtype=matched_subtype or suggested.get("voc_subtype"),
                sort="relevance",
                page_size=3,
            ),
            "relevance",
        )
        ranked_items = [item for item in ranked["items"] if item["final_score"] > 0]
        best_match = ranked_items[0] if ranked_items else suggested
        translation = TranslationService(settings).translate(payload.original_mail_body)
        return {
            **parse_sender(payload.original_mail_body),
            "translation_draft": translation["translated_text"],
            "translation_status": translation["status"],
            "suggested_voc_type": best_match.get("voc_type"),
            "suggested_voc_subtype": (
                matched_subtype
                if explicit_subtype
                else best_match.get("voc_subtype") or "과거 이력 없음"
            ) or "과거 이력 없음",
            "suggested_product_equipment": _product_equipment(
                payload.original_mail_body, best_match
            ),
            "suggested_customer_request": _request_summary(payload.original_mail_body),
            "suggested_priority": "high"
            if str(best_match.get("priority", "")).lower() in {"high", "높음"}
            else "normal",
            "suggested_departments": _departments(
                best_match.get("responsible_departments")
            ),
            "extracted_keywords": keywords,
            "items": ranked_items,
        }

    return router
