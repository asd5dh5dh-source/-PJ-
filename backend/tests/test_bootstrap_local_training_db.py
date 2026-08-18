from contextlib import nullcontext
from pathlib import Path
import re
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.bootstrap_local_training_db import (
    bootstrap_training_database,
    load_training_rows,
    seed_action,
    seed_training_rows,
)


BACKEND = Path(__file__).parents[1]
REPOSITORY = BACKEND.parent
WRAPPER = BACKEND / "scripts" / "verify_local_training_db.ps1"
SEARCH_MIGRATION = BACKEND / "migrations" / "001_local_search.sql"


def expected_database_name():
    return "".join(chr(code) for code in (0xD559, 0xC2B5, 0xC6A9)) + " Data"


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
    def __init__(self, database_name, summary=None, total_count=135):
        self.database_name = database_name
        self.summary = summary
        self.total_count = total_count
        self.queries = []

    def execute(self, query, params=None):
        self.queries.append((query, params))
        if "FROM pg_database" in query:
            return FakeResult(rows=[{"datname": expected_database_name()}])
        if query.strip() == "SELECT current_database() AS database_name":
            return FakeResult(row={"database_name": self.database_name})
        if "AS seed_historical_count" in query:
            return FakeResult(row={"seed_historical_count": 135})
        if "AS verified_historical_count" in query:
            return FakeResult(row={"verified_historical_count": 135})
        if "count(*) AS row_count" in query:
            return FakeResult(row={"row_count": self.total_count})
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


def settings(database_name=None):
    return SimpleNamespace(
        voc_db_host="localhost",
        voc_db_port=5432,
        voc_db_name=database_name or expected_database_name(),
        voc_db_user="postgres",
        voc_db_password=SecretStr("local-secret"),
    )


def test_bootstrap_connects_directly_to_validated_database_and_verifies_it_first():
    connections = []

    def connect(**kwargs):
        connection = FakeConnection(kwargs["dbname"])
        connections.append((kwargs, connection))
        return nullcontext(connection)

    summary = bootstrap_training_database(
        settings=settings(),
        connect=connect,
        repository_root=REPOSITORY,
    )

    assert [item[0]["dbname"] for item in connections] == [expected_database_name()]
    assert all("conninfo" not in item[0] for item in connections)
    assert connections[0][1].queries[0][0].strip() == (
        "SELECT current_database() AS database_name"
    )
    target_sql = "\n".join(query for query, _ in connections[0][1].queries)
    assert "CREATE TABLE IF NOT EXISTS public.voc_cases" in target_sql
    assert "ALTER TABLE public.voc_cases" in target_sql
    assert "\\copy" not in target_sql
    assert summary.historical_count == 135


def test_bootstrap_allows_user_input_rows_beyond_historical_baseline():
    def connect(**kwargs):
        return nullcontext(FakeConnection(kwargs["dbname"], total_count=137))

    summary = bootstrap_training_database(
        settings=settings(),
        connect=connect,
        repository_root=REPOSITORY,
    )

    assert summary.historical_count == 135


def test_bootstrap_rejects_unvalidated_database_name_before_connecting():
    def connect(**kwargs):
        raise AssertionError("connection must not be attempted")

    with pytest.raises(RuntimeError, match="exact training database"):
        bootstrap_training_database(
            settings=settings(expected_database_name() + " "),
            connect=connect,
            repository_root=REPOSITORY,
        )


def test_bootstrap_rejects_database_identity_mismatch_before_migrations():
    connection = FakeConnection("postgres")

    with pytest.raises(RuntimeError, match="exact training database"):
        bootstrap_training_database(
            settings=settings(),
            connect=lambda **kwargs: nullcontext(connection),
            repository_root=REPOSITORY,
        )

    assert [query.strip() for query, _ in connection.queries] == [
        "SELECT current_database() AS database_name"
    ]


def test_bootstrap_rejects_invalid_summary_before_success():

    def connect(**kwargs):
        summary = {
            "database_name": expected_database_name(),
            "historical_count": 135,
            "duplicate_case_ids": 0,
            "missing_product_equipment": 1,
        }
        return nullcontext(FakeConnection(kwargs["dbname"], summary))

    with pytest.raises(RuntimeError, match="verification summary"):
        bootstrap_training_database(
            settings=settings(),
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


def test_search_migration_uses_postgres_word_boundaries_for_historical_rows():
    migration = SEARCH_MIGRATION.read_text("ascii")

    assert (
        "substring(customer_request from "
        "E'(?i)\\\\m(NCM811|NCM9|NCA|LMFP|LFP)\\\\M')"
    ) in migration
    assert (
        "WHERE record_origin = 'historical'\n"
        "  AND (product_equipment IS NULL OR btrim(product_equipment) = '');"
    ) in migration


def test_product_pattern_matches_tokens_but_not_embedded_prefixes():
    migration = SEARCH_MIGRATION.read_text("ascii")
    assert "E'(?i)\\\\m(NCM811|NCM9|NCA|LMFP|LFP)\\\\M'" in migration

    token_pattern = re.compile(r"(?i)\b(NCM811|NCM9|NCA|LMFP|LFP)\b")
    assert token_pattern.search("Issue observed on NCM811 cathode").group(1) == "NCM811"
    assert token_pattern.search("LMFP qualification").group(1) == "LMFP"
    assert token_pattern.search("XNCM811Y") is None
    assert token_pattern.search("preLFPgrade") is None


def test_product_backfill_preserves_populated_and_user_input_values():
    def selected(record_origin, product_equipment):
        return record_origin == "historical" and (
            product_equipment is None or product_equipment.strip() == ""
        )

    assert selected("historical", None)
    assert selected("historical", " ")
    assert not selected("historical", "NCM811")
    assert not selected("user_input", None)
    assert not selected("user_input", "LFP")
