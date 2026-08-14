import csv
from datetime import date, timedelta
from pathlib import Path
import sys
from typing import Any, Callable

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings
from app.repositories.voc_cases import DatasetSummary


EXPECTED_DATABASE = "학습용 Data"
EXPECTED_HEADERS = (
    "case_id",
    "customer_name",
    "country",
    "voc_type",
    "voc_subtype",
    "priority",
    "customer_request",
    "original_mail_body",
    "responsible_departments",
    "received_at",
    "first_response_at",
    "containment_at",
    "root_cause_action_5d_at",
    "customer_reply_at",
    "final_status",
    "delay_stage",
    "delay_reason",
    "auto_close",
    "reactivated",
    "due_6d_at",
    "result_6d",
    "full_response_history",
    "customer_request_embedding",
    "original_mail_body_embedding",
)
DATE_COLUMNS = {"received_at", "first_response_at", "due_6d_at"}
BOOLEAN_COLUMNS = {"auto_close", "reactivated"}


def resolve_catalog_name(names: list[str]) -> str:
    if EXPECTED_DATABASE in names:
        return EXPECTED_DATABASE

    diagnostics = ", ".join(
        f"{name!r} length={len(name)} utf8_hex={name.encode('utf-8').hex()}"
        for name in names
    )
    raise RuntimeError(f"No exact training database match. Catalog: {diagnostics}")


def seed_action(row_count: int) -> str:
    if row_count == 0:
        return "seed"
    if row_count == 135:
        return "skip"
    raise RuntimeError(f"Refusing to seed database containing {row_count} rows")


def load_training_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        rows = list(reader)

    headers = reader.fieldnames or []
    if tuple(headers) != EXPECTED_HEADERS:
        raise RuntimeError("Training CSV must have the expected 24-column schema")
    if len(rows) != 135:
        raise RuntimeError(f"Training CSV must contain exactly 135 rows, found {len(rows)}")
    return headers, rows


def _date_value(value: str) -> date | None:
    if not value:
        return None
    if value.isdigit():
        return date(1899, 12, 30) + timedelta(days=int(value))
    return date.fromisoformat(value)


def _boolean_value(value: str) -> bool | None:
    normalized = value.upper()
    if normalized in {"Y", "TRUE", "T", "1"}:
        return True
    if normalized in {"N", "FALSE", "F", "0"}:
        return False
    return None


def seed_training_rows(connection: Any, rows: list[dict[str, str]]) -> None:
    placeholders = ", ".join(["%s"] * len(EXPECTED_HEADERS))
    query = (
        f"INSERT INTO public.voc_cases ({', '.join(EXPECTED_HEADERS)}) "
        f"VALUES ({placeholders})"
    )
    values = []
    for row in rows:
        converted = []
        for column in EXPECTED_HEADERS:
            value = row[column]
            if column in DATE_COLUMNS:
                value = _date_value(value)
            elif column in BOOLEAN_COLUMNS:
                value = _boolean_value(value)
            converted.append(value)
        values.append(tuple(converted))

    with connection.cursor() as cursor:
        cursor.executemany(query, values)


def execute_plain_sql(connection: Any, path: Path) -> None:
    sql = path.read_text(encoding="ascii")
    if any(line.lstrip().startswith("\\") for line in sql.splitlines()):
        raise RuntimeError(f"psql meta-command is not allowed in {path.name}")
    connection.execute(sql)


def bootstrap_training_database(
    *,
    settings: Any | None = None,
    connect: Callable[..., Any] = psycopg.connect,
    repository_root: Path | None = None,
) -> DatasetSummary:
    settings = settings or get_settings()
    repository_root = repository_root or Path(__file__).resolve().parents[2]
    connection_options = {
        "host": settings.voc_db_host,
        "port": settings.voc_db_port,
        "user": settings.voc_db_user,
        "password": settings.voc_db_password.get_secret_value(),
        "row_factory": dict_row,
    }

    with connect(dbname="postgres", **connection_options) as maintenance:
        names = [
            row["datname"]
            for row in maintenance.execute(
                "SELECT datname FROM pg_database ORDER BY datname"
            ).fetchall()
        ]
    database_name = resolve_catalog_name(names)

    backend = repository_root / "backend"
    with connect(dbname=database_name, **connection_options) as connection:
        execute_plain_sql(connection, backend / "migrations" / "000_bootstrap_voc_cases.sql")
        row_count = connection.execute(
            "SELECT count(*) AS row_count FROM public.voc_cases"
        ).fetchone()["row_count"]
        if seed_action(row_count) == "seed":
            _, rows = load_training_rows(repository_root / "work" / "voc_train.csv")
            seed_training_rows(connection, rows)

        verified_count = connection.execute(
            "SELECT count(*) AS row_count FROM public.voc_cases"
        ).fetchone()["row_count"]
        if verified_count != 135:
            raise RuntimeError(f"Expected 135 training rows, found {verified_count}")

        execute_plain_sql(connection, backend / "migrations" / "001_local_search.sql")
        summary_row = connection.execute(
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
        summary = DatasetSummary(**summary_row)
        if (
            summary.database_name != database_name
            or summary.historical_count != 135
            or summary.duplicate_case_ids != 0
            or summary.missing_product_equipment != 0
        ):
            raise RuntimeError(f"Invalid verification summary: {summary}")

    return summary


def main() -> int:
    try:
        summary = bootstrap_training_database()
    except Exception as error:
        print(f"Bootstrap failed: {error}", file=sys.stderr)
        return 1
    print(
        "Bootstrap verified: "
        f"database={summary.database_name!r} "
        f"historical={summary.historical_count} "
        f"duplicates={summary.duplicate_case_ids} "
        f"missing_product_equipment={summary.missing_product_equipment}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
