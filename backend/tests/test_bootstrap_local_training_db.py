from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unicodedata

import pytest
from pydantic import SecretStr

from app.bootstrap_local_training_db import (
    bootstrap_training_database,
    load_training_rows,
    resolve_catalog_name,
    seed_action,
    seed_training_rows,
)


BACKEND = Path(__file__).parents[1]
REPOSITORY = BACKEND.parent
WRAPPER = BACKEND / "scripts" / "verify_local_training_db.ps1"
SEARCH_MIGRATION = BACKEND / "migrations" / "001_local_search.sql"


def expected_database_name():
    return "".join(chr(code) for code in (0xD559, 0xC2B5, 0xC6A9)) + " Data"


def test_catalog_resolution_prefers_exact_match():
    expected = expected_database_name()

    assert resolve_catalog_name([expected + " ", expected]) == expected


def test_catalog_resolution_accepts_one_normalized_match():
    expected = expected_database_name()
    decomposed = unicodedata.normalize("NFD", expected) + " "

    assert resolve_catalog_name([decomposed]) == decomposed


@pytest.mark.parametrize("names", [["postgres"], ["학습용 Data ", "학습용 Data  "]])
def test_catalog_resolution_stops_when_match_is_not_unique(names):
    with pytest.raises(RuntimeError):
        resolve_catalog_name(names)


@pytest.mark.parametrize(
    ("row_count", "expected"),
    [(0, "seed"), (135, "skip")],
)
def test_seed_action_allows_only_empty_or_complete_database(row_count, expected):
    assert seed_action(row_count) == expected


def test_seed_action_rejects_partial_database():
    with pytest.raises(RuntimeError):
        seed_action(1)


def test_training_csv_has_exact_expected_shape():
    headers, rows = load_training_rows(REPOSITORY / "work" / "voc_train.csv")

    assert len(headers) == 24
    assert len(rows) == 135


class FakeCursor:
    def __init__(self):
        self.query = None
        self.values = None

    def executemany(self, query, values):
        self.query = query
        self.values = values

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_training_seed_uses_parameterized_executemany_for_all_rows():
    _, rows = load_training_rows(REPOSITORY / "work" / "voc_train.csv")
    cursor = FakeCursor()
    connection = SimpleNamespace(cursor=lambda: cursor)

    seed_training_rows(connection, rows)

    assert cursor.query.count("%s") == 24
    assert len(cursor.values) == 135
    assert all(len(values) == 24 for values in cursor.values)


class FakeResult:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, database_name, summary=None):
        self.database_name = database_name
        self.summary = summary
        self.queries = []

    def execute(self, query, params=None):
        self.queries.append((query, params))
        if "FROM pg_database" in query:
            return FakeResult(rows=[{"datname": expected_database_name()}])
        if "count(*) AS row_count" in query:
            return FakeResult(row={"row_count": 135})
        if "AS historical_count" in query:
            return FakeResult(
                row=self.summary or {
                    "database_name": expected_database_name(),
                    "historical_count": 135,
                    "duplicate_case_ids": 0,
                    "missing_product_equipment": 0,
                }
            )
        return FakeResult()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_bootstrap_uses_psycopg_keyword_connections_and_plain_sql():
    connections = []

    def connect(**kwargs):
        connection = FakeConnection(kwargs["dbname"])
        connections.append((kwargs, connection))
        return nullcontext(connection)

    settings = SimpleNamespace(
        voc_db_host="localhost",
        voc_db_port=5432,
        voc_db_user="postgres",
        voc_db_password=SecretStr("local-secret"),
    )

    summary = bootstrap_training_database(
        settings=settings,
        connect=connect,
        repository_root=REPOSITORY,
    )

    assert [item[0]["dbname"] for item in connections] == [
        "postgres",
        expected_database_name(),
    ]
    assert all("conninfo" not in item[0] for item in connections)
    target_sql = "\n".join(query for query, _ in connections[1][1].queries)
    assert "CREATE TABLE IF NOT EXISTS public.voc_cases" in target_sql
    assert "ALTER TABLE public.voc_cases" in target_sql
    assert "\\copy" not in target_sql
    assert summary.historical_count == 135


def test_bootstrap_rejects_invalid_summary_before_success():
    connection_count = 0

    def connect(**kwargs):
        nonlocal connection_count
        connection_count += 1
        summary = None
        if connection_count == 2:
            summary = {
                "database_name": expected_database_name(),
                "historical_count": 135,
                "duplicate_case_ids": 0,
                "missing_product_equipment": 1,
            }
        return nullcontext(FakeConnection(kwargs["dbname"], summary))

    settings = SimpleNamespace(
        voc_db_host="localhost",
        voc_db_port=5432,
        voc_db_user="postgres",
        voc_db_password=SecretStr("local-secret"),
    )

    with pytest.raises(RuntimeError, match="verification summary"):
        bootstrap_training_database(
            settings=settings,
            connect=connect,
            repository_root=REPOSITORY,
        )


def test_wrapper_contains_only_secure_python_bootstrap_path():
    wrapper = WRAPPER.read_text("ascii")
    lowered = wrapper.lower()

    assert "psql" not in lowered
    assert "createdb" not in lowered
    assert "pgdatabase" not in lowered
    assert "pgpassword" not in lowered
    assert "voc_test" not in lowered
    assert "테스트용 Data" not in wrapper
    assert "-m app.bootstrap_local_training_db" in wrapper


def test_search_migration_extracts_product_without_escaped_boundaries():
    migration = SEARCH_MIGRATION.read_text("ascii")

    assert (
        "substring(customer_request from "
        "'(?i)(NCM811|NCM9|NCA|LMFP|LFP)')"
    ) in migration
    assert "\\\\m" not in migration
    assert "WHERE product_equipment IS NULL OR btrim(product_equipment) = '';" in migration
