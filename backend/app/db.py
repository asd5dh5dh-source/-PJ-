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
