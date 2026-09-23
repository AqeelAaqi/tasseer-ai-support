"""Conversation + audit logging for support chats.

Deliberately its OWN small table in the support service's own database (not
the legacy `ksatntau_api` DB, which this service only ever reads from) so we
never need write access to production. Point `SUPPORT_LOG_DB_*` at a small
Postgres/SQLite/MySQL instance owned by this service.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "support_log.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS support_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    order_id TEXT,
    role TEXT NOT NULL,           -- 'customer' | 'assistant'
    message TEXT NOT NULL,
    context_snapshot TEXT,        -- JSON of SupportContext at the time, for audit
    escalated INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def log_message(
    customer_id: int,
    order_id: str | None,
    role: str,
    message: str,
    context_snapshot: dict | None = None,
    escalated: bool = False,
) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO support_messages (customer_id, order_id, role, message, "
            "context_snapshot, escalated, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                customer_id,
                order_id,
                role,
                message,
                json.dumps(context_snapshot) if context_snapshot else None,
                int(escalated),
                dt.datetime.utcnow().isoformat(),
            ),
        )
