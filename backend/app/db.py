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
    def record_and_check_locked(
        self, writer_name: str, client_ip: str, succeeded: bool
    ) -> bool:
        with database_connection() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (client_ip,),
            )
            row = connection.execute(
                """
                WITH latest_success AS (
                    SELECT max(attempted_at) AS attempted_at
                    FROM writer_attempts
                    WHERE client_ip = %s
                      AND succeeded
                )
                SELECT count(*)::integer AS failure_count
                FROM writer_attempts AS attempts
                CROSS JOIN latest_success
                WHERE attempts.client_ip = %s
                  AND NOT attempts.succeeded
                  AND attempts.attempted_at >= now() - interval '15 minutes'
                  AND attempts.attempted_at > coalesce(
                      latest_success.attempted_at,
                      '-infinity'::timestamptz
                )
                """,
                (client_ip, client_ip),
            ).fetchone()
            if int(row["failure_count"]) >= 5:
                return True
            connection.execute(
                """
                INSERT INTO writer_attempts (writer_name, client_ip, succeeded)
                VALUES (%s, %s, %s)
                """,
                (writer_name, client_ip, succeeded),
            )
        return False
