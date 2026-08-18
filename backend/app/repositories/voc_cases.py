from dataclasses import dataclass
from typing import Any, Mapping

from app.db import database_connection


@dataclass(frozen=True)
class DatasetSummary:
    database_name: str
    historical_count: int
    duplicate_case_ids: int
    missing_product_equipment: int


class VocCaseRepository:
    _FILTERS = {
        "customer_name": "customer_name = %s",
        "product_equipment": "product_equipment = %s",
        "voc_type": "voc_type = %s",
        "voc_subtype": "voc_subtype = %s",
        "final_status": "final_status = %s",
        "responsible_department": "responsible_departments = %s",
        "received_from": "received_at >= %s",
        "received_to": "received_at <= %s",
        "exclude_case_id": "case_id <> %s",
    }
    _CREATE_COLUMNS = (
        "case_id",
        "customer_request",
        "record_origin",
        "final_status",
        "search_document",
        "original_mail_body",
        "customer_name",
        "product_equipment",
        "voc_type",
        "voc_subtype",
        "responsible_departments",
        "received_at",
    )

    def dataset_summary(self) -> DatasetSummary:
        with database_connection() as connection:
            row = connection.execute(
                """
                SELECT current_database() AS database_name,
                       count(*) FILTER (WHERE record_origin = 'historical') AS historical_count,
                       count(*) - count(DISTINCT case_id) AS duplicate_case_ids,
                       count(*) FILTER (
                           WHERE product_equipment IS NULL
                              OR btrim(product_equipment) = ''
                       ) AS missing_product_equipment
                FROM public.voc_cases
                """
            ).fetchone()
        return DatasetSummary(**row)

    def list_candidates(
        self,
        filters: Mapping[str, Any] | None = None,
        **filter_values: Any,
    ) -> list[dict[str, Any]]:
        selected = dict(filters or {})
        selected.update(filter_values)
        clauses = []
        params = []
        for name, clause in self._FILTERS.items():
            if selected.get(name) is not None:
                clauses.append(clause)
                params.append(selected[name])

        query = "SELECT * FROM public.voc_cases"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY received_at DESC"
        with database_connection() as connection:
            return connection.execute(query, tuple(params)).fetchall()

    def get(self, case_id: str) -> dict[str, Any] | None:
        with database_connection() as connection:
            return connection.execute(
                "SELECT * FROM public.voc_cases WHERE case_id = %s",
                (case_id,),
            ).fetchone()

    def create(self, payload: Any) -> dict[str, Any]:
        source = dict(payload) if isinstance(payload, Mapping) else payload.model_dump()
        source.update(record_origin="user_input", final_status="received")
        values = {name: source[name] for name in self._CREATE_COLUMNS if name in source}
        columns = ", ".join(values)
        placeholders = ", ".join(["%s"] * len(values))
        with database_connection() as connection:
            return connection.execute(
                f"INSERT INTO public.voc_cases ({columns}) "
                f"VALUES ({placeholders}) RETURNING *",
                tuple(values.values()),
            ).fetchone()
