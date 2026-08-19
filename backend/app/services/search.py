from datetime import date
from threading import RLock
from typing import Any

from app.schemas import ArchiveQuery, ArchiveSort
from app.services.bm25 import Bm25Index


class ArchiveSearchService:
    _FILTERS = {
        "customer_name",
        "product_equipment",
        "voc_type",
        "voc_subtype",
        "boost_voc_subtype",
        "final_status",
        "responsible_department",
        "received_from",
        "received_to",
    }

    def __init__(self, repository: Any, index: Bm25Index | None = None) -> None:
        self.repository = repository
        self.index = index or Bm25Index()
        self._lock = RLock()
        self._candidate_cache: dict[tuple[tuple[str, Any], ...], list[dict[str, Any]]] = {}

    def refresh(self) -> None:
        with self._lock:
            candidates = self.repository.list_candidates()
            self._candidate_cache = {(): candidates}
            self.index.refresh(candidates)

    def invalidate(self) -> None:
        with self._lock:
            self._candidate_cache.clear()

    def _list_candidates(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        key = tuple(sorted(filters.items()))
        if key not in self._candidate_cache:
            self._candidate_cache[key] = self.repository.list_candidates(filters)
        return self._candidate_cache[key]

    def search_archive(
        self,
        query: ArchiveQuery,
        effective_sort: ArchiveSort,
    ) -> dict[str, Any]:
        filters = query.model_dump(
            include=self._FILTERS - {"boost_voc_subtype"}, exclude_none=True
        )
        with self._lock:
            candidates = self._list_candidates(filters)
            items = [dict(case) for case in candidates]

            if query.q:
                ranked = self.index.rank(
                    query.q,
                    candidates,
                    query.boost_voc_subtype,
                    len(candidates),
                )
                cases_by_id = {str(case["case_id"]): dict(case) for case in candidates}
                items = [
                    cases_by_id[item.case_id]
                    | {
                        "bm25_score": item.bm25_score,
                        "final_score": item.final_score,
                        "matched_keywords": item.matched_keywords,
                    }
                    for item in ranked
                ]

        if effective_sort != "relevance":
            items.sort(
                key=lambda item: item.get("received_at") or date.min,
                reverse=effective_sort == "latest",
            )

        offset = (query.page - 1) * query.page_size
        return {
            "items": items[offset : offset + query.page_size],
            "total": len(items),
            "page": query.page,
            "page_size": query.page_size,
            "sort": effective_sort,
        }

    def rank_similar(
        self,
        source_case: dict[str, Any],
        candidates: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        query = source_case.get("search_document") or " ".join(
            filter(
                None,
                [
                    source_case.get("customer_request"),
                    source_case.get("original_mail_body"),
                ],
            )
        )
        with self._lock:
            ranked = self.index.rank(
                query,
                candidates,
                source_case.get("voc_subtype"),
                limit,
            )
        cases_by_id = {str(case["case_id"]): dict(case) for case in candidates}
        return [
            cases_by_id[item.case_id]
            | {
                "bm25_score": item.bm25_score,
                "final_score": item.final_score,
                "matched_keywords": item.matched_keywords,
            }
            for item in ranked
        ]
