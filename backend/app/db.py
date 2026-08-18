from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings


@contextmanager
def database_connection():
    with psycopg.connect(
        get_settings().database_dsn(), row_factory=dict_row
    ) as connection:
        yield connection


class WriterAttemptStore:
    def recent_failure_count(self, writer_name: str, client_ip: str) -> int:
        with database_connection() as connection:
            row = connection.execute(
                """
                WITH latest_success AS (
                    SELECT max(attempted_at) AS attempted_at
                    FROM writer_attempts
                    WHERE writer_name = %s
                      AND client_ip = %s
                      AND succeeded
                )
                SELECT count(*)::integer AS failure_count
                FROM writer_attempts AS attempts
                CROSS JOIN latest_success
                WHERE attempts.writer_name = %s
                  AND attempts.client_ip = %s
                  AND NOT attempts.succeeded
                  AND attempts.attempted_at >= now() - interval '15 minutes'
                  AND attempts.attempted_at > coalesce(
                      latest_success.attempted_at,
                      '-infinity'::timestamptz
                  )
                """,
                (writer_name, client_ip, writer_name, client_ip),
            ).fetchone()
        return int(row["failure_count"])

    def record_attempt(
        self, writer_name: str, client_ip: str, succeeded: bool
    ) -> None:
        with database_connection() as connection:
            connection.execute(
                """
                INSERT INTO writer_attempts (writer_name, client_ip, succeeded)
                VALUES (%s, %s, %s)
                """,
                (writer_name, client_ip, succeeded),
            )
