"""Persistent app-side usage storage for VisionIQ.

Groq does not provide a fresh account-wide quota summary on every successful
request. This module records the usage made inside VisionIQ so the dashboard can
show a practical daily token estimate per saved API key.
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from datetime import date

from src.config import DB_PATH


def _hash_api_key(api_key: str) -> str:
    """Hash an API key before using it as a database identifier."""

    return hashlib.sha256((api_key or "").encode("utf-8")).hexdigest()


def init_api_daily_usage_table() -> None:
    """Create the local daily usage table if it does not already exist."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_daily_usage (
                api_key_hash TEXT NOT NULL,
                usage_date TEXT NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                PRIMARY KEY (api_key_hash, usage_date)
            )
            """
        )
        conn.commit()


def add_api_daily_usage(api_key: str, tokens: int) -> None:
    """Record tokens from a successful model request for today's date."""

    init_api_daily_usage_table()
    api_key_hash = _hash_api_key(api_key)
    today = date.today().isoformat()

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            INSERT INTO api_daily_usage (
                api_key_hash, usage_date, total_tokens, total_requests
            )
            VALUES (?, ?, ?, 1)
            ON CONFLICT(api_key_hash, usage_date)
            DO UPDATE SET
                total_tokens = total_tokens + excluded.total_tokens,
                total_requests = total_requests + 1
            """,
            (api_key_hash, today, int(tokens or 0)),
        )
        conn.commit()


def get_api_daily_usage(api_key: str) -> dict[str, int]:
    """Return today's locally recorded usage for one API key."""

    init_api_daily_usage_table()
    api_key_hash = _hash_api_key(api_key)
    today = date.today().isoformat()

    with closing(sqlite3.connect(DB_PATH)) as conn:
        row = conn.execute(
            """
            SELECT total_tokens, total_requests
            FROM api_daily_usage
            WHERE api_key_hash=? AND usage_date=?
            """,
            (api_key_hash, today),
        ).fetchone()

    if not row:
        return {"tokens": 0, "requests": 0}

    return {"tokens": int(row[0] or 0), "requests": int(row[1] or 0)}
