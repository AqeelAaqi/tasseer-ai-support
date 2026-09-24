import io
from contextlib import contextmanager
from typing import Iterator

import paramiko
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, Row

from app.core.config import settings

# This service is READ-ONLY against the live Tasseer operational database.
# It must be configured with a MySQL account that only has SELECT grants on
# `ksatntau_api` (see TODO_INTEGRATION.md) - the ORM layer never issues
# writes, but the real guarantee is the DB grant, not application code.

# Namecheap shared hosting doesn't expose MySQL remotely at all - the only
# supported way in is SSH port-forwarding to the DB server itself (confirmed
# by Namecheap support, see DEPLOY.md). When this service runs anywhere
# other than that same server (e.g. Render), we open that tunnel ourselves
# on startup and connect through it instead of directly.
_tunnel = None


def _resolve_db_target() -> tuple[str, int]:
    """Returns the (host, port) this process should actually dial for MySQL -
    either the tunnel's local end, or settings.tasseer_db_host/port directly
    if no tunnel is configured (e.g. deployed on the same server as the DB)."""
    if not settings.ssh_tunnel_host:
        return settings.tasseer_db_host, settings.tasseer_db_port

    global _tunnel
    from sshtunnel import SSHTunnelForwarder

    pkey = paramiko.RSAKey.from_private_key(
        io.StringIO(settings.ssh_tunnel_private_key),
        password=settings.ssh_tunnel_private_key_passphrase or None,
    )
    _tunnel = SSHTunnelForwarder(
        (settings.ssh_tunnel_host, settings.ssh_tunnel_port),
        ssh_username=settings.ssh_tunnel_username,
        ssh_pkey=pkey,
        # Explicit IP rather than settings.tasseer_db_host ("localhost") -
        # the SSH server resolves this itself, and "localhost" as a bare
        # hostname string caused connections to drop immediately during the
        # MySQL handshake in testing; 127.0.0.1 works reliably.
        remote_bind_address=("127.0.0.1", settings.tasseer_db_port),
    )
    _tunnel.start()
    return "127.0.0.1", _tunnel.local_bind_port


_db_host, _db_port = _resolve_db_target()
_db_url = (
    f"mysql+pymysql://{settings.tasseer_db_user}:{settings.tasseer_db_password}"
    f"@{_db_host}:{_db_port}/{settings.tasseer_db_name}?charset=utf8mb4"
)
_engine: Engine = create_engine(_db_url, pool_pre_ping=True, pool_recycle=1800)


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
