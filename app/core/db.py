from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, Row

from app.core.config import settings

# This service is READ-ONLY against the live Tasseer operational database.
# It must be configured with a MySQL account that only has SELECT grants on
# `ksatntau_api` (see infra/README.md) - the ORM layer never issues writes,
# but the real guarantee is the DB grant, not application code.
_engine: Engine = create_engine(settings.db_url, pool_pre_ping=True, pool_recycle=1800)


@contextmanager
def get_connection() -> Iterator[Connection]:
    with _engine.connect() as conn:
        yield conn


def fetch_one(sql: str, params: dict) -> Row | None:
    with get_connection() as conn:
        result = conn.execute(text(sql), params)
        return result.first()


def fetch_all(sql: str, params: dict) -> list[Row]:
    with get_connection() as conn:
        result = conn.execute(text(sql), params)
        return list(result)
