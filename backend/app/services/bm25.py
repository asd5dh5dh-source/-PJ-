from collections import Counter
from dataclasses import dataclass
from math import log
from typing import Any, Mapping, Sequence

from app.services.text import tokenize


@dataclass(frozen=True)
class RankedCase:
    case_id: str
    bm25_score: float
    final_score: float
    matched_keywords: list[str]


@dataclass(frozen=True)
class _Document:
    case: Mapping[str, Any] | Any
    tokens: list[str]
    term_counts: Counter[str]


class Bm25Index:
    _SEARCH_FIELDS = (
        "customer_request",
        "original_mail_body",
        "full_response_history",
    )
    _K1 = 1.5
    _B = 0.75

    def __init__(self) -> None:
        self._candidates: Sequence[Mapping[str, Any] | Any] | None = None
        self._documents: list[_Document] = []
        self._document_frequency: Counter[str] = Counter()
        self._average_length = 0.0

    def refresh(self, candidates: Sequence[Mapping[str, Any] | Any]) -> None:
        self._candidates = candidates
        self._documents = []
        self._document_frequency = Counter()
        for case in candidates:
            tokens = [
                token
                for field in self._SEARCH_FIELDS
                for token in tokenize(self._value(case, field))
            ]
            document = _Document(case, tokens, Counter(tokens))
            self._documents.append(document)
            self._document_frequency.update(document.term_counts.keys())
        self._average_length = (
            sum(len(document.tokens) for document in self._documents) / len(self._documents)
            if self._documents
            else 0.0
        )

    def rank(
        self,
        query: str | None,
        candidates: Sequence[Mapping[str, Any] | Any],
        query_subtype: str | None,
        limit: int,
    ) -> list[RankedCase]:
        if candidates is not self._candidates:
            self.refresh(candidates)

        query_tokens = tokenize(query)
        results = [
            self._rank_document(document, query_tokens, query_subtype)
            for document in self._documents
        ]
        return sorted(
            results,
            key=lambda item: (-item.final_score, -item.bm25_score, item.case_id),
        )[: max(limit, 0)]

    def _rank_document(
        self,
        document: _Document,
        query_tokens: list[str],
        query_subtype: str | None,
    ) -> RankedCase:
        bm25_score = sum(
            self._term_score(token, document)
            for token in query_tokens
            if token in document.term_counts
        )
        subtype = self._value(document.case, "voc_subtype")
        final_score = bm25_score * (1.1 if subtype == query_subtype else 1.0)
        matched_keywords = list(dict.fromkeys(
            token for token in query_tokens if token in document.term_counts
        ))
        return RankedCase(
            case_id=str(self._value(document.case, "case_id")),
            bm25_score=bm25_score,
            final_score=final_score,
            matched_keywords=matched_keywords,
        )

    def _term_score(self, token: str, document: _Document) -> float:
        frequency = document.term_counts[token]
        document_count = len(self._documents)
        inverse_frequency = log(
            1 + (document_count - self._document_frequency[token] + 0.5)
            / (self._document_frequency[token] + 0.5)
        )
        denominator = frequency + self._K1 * (
            1 - self._B + self._B * len(document.tokens) / self._average_length
        )
        return inverse_frequency * frequency * (self._K1 + 1) / denominator

    @staticmethod
    def _value(case: Mapping[str, Any] | Any, field: str) -> Any:
        return case.get(field) if isinstance(case, Mapping) else getattr(case, field, None)
