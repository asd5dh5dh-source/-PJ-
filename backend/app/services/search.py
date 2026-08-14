from datetime import date
from typing import Any

from app.schemas import ArchiveQuery, ArchiveSort
from app.services.bm25 import Bm25Index


class ArchiveSearchService:
    _FILTERS = {
        "customer_name",
        "product_equipment",
        "voc_type",
        "voc_subtype",
        "final_status",
        "responsible_department",
        "received_from",
        "received_to",
    }

    def __init__(self, repository: Any, index: Bm25Index | None = None) -> None:
        self.repository = repository
        self.index = index or Bm25Index()

    def search_archive(
        self,
        query: ArchiveQuery,
        effective_sort: ArchiveSort,
    ) -> dict[str, Any]:
        filters = query.model_dump(include=self._FILTERS, exclude_none=True)
        candidates = self.repository.list_candidates(filters)
        items = [dict(case) for case in candidates]

        if query.q:
            ranked = self.index.rank(query.q, candidates, query.voc_subtype, len(candidates))
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
