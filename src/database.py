"""SQLite persistence for VisionIQ.

The database layer is deliberately small and boring: every public function
opens its own connection, performs one unit of work, and closes the connection.
That pattern is reliable for Streamlit's rerun-based execution model.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import time
from contextlib import closing
from typing import Any

from src.config import DB_PATH

PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 160_000


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection and ensure the data directory exists.

    SQLite creates the database file automatically, but it will not create the
    parent directory. Creating it here keeps callers from needing path logic.
    """

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def _normalize_username(username: str) -> str:
    """Normalize usernames so email lookups are case-insensitive."""

    return (username or "").strip().lower()


def _hash_password(password: str) -> str:
    """Create a salted PBKDF2 password hash for storage.

    The salt is random per password, while the iteration count is stored inside
    the encoded value so future verification can reproduce the same digest.
    """

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return (
        f"{PASSWORD_HASH_ALGORITHM}"
        f"${PASSWORD_HASH_ITERATIONS}"
        f"${salt.hex()}"
        f"${digest.hex()}"
    )


def _verify_password(password: str, stored_hash: str) -> bool:
    """Compare a submitted password with the stored PBKDF2 hash."""

    if not password or not stored_hash:
        return False

    try:
        algorithm, iterations_text, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False

        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
        actual_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)

        # Constant-time comparison avoids leaking information through timing.
        return hmac.compare_digest(actual_digest, expected_digest)
    except (ValueError, TypeError):
        return False


def init_db() -> None:
    """Create all tables required by the first VisionIQ application batch."""

    with closing(get_connection()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                groq_key TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                timestamp REAL NOT NULL,
                image_number INTEGER,
                file_name TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0,
                model TEXT,
                status TEXT DEFAULT 'success',
                error_message TEXT DEFAULT ''
            )
            """
        )
        conn.commit()


def create_user(username: str, password: str) -> bool:
    """Create a user account and return ``False`` if the email already exists."""

    clean_username = _normalize_username(username)
    if not clean_username or not password:
        return False

    with closing(get_connection()) as conn:
        try:
            conn.execute(
                """
                INSERT INTO users (username, password_hash, groq_key)
                VALUES (?, ?, '')
                """,
                (clean_username, _hash_password(password)),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def validate_user(username: str, password: str) -> bool:
    """Return whether the supplied credentials match a stored account."""

    clean_username = _normalize_username(username)
    if not clean_username or not password:
        return False

    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username=?",
            (clean_username,),
        ).fetchone()

    return bool(row and _verify_password(password, row[0]))


def save_groq_key(username: str, encrypted_key: str) -> None:
    """Store an encrypted Groq API key for the current user."""

    with closing(get_connection()) as conn:
        conn.execute(
            "UPDATE users SET groq_key=? WHERE username=?",
            (encrypted_key, _normalize_username(username)),
        )
        conn.commit()


def get_groq_key(username: str) -> str | None:
    """Return the encrypted Groq API key for a user, if one is stored."""

    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT groq_key FROM users WHERE username=?",
            (_normalize_username(username),),
        ).fetchone()

    if row and row[0]:
        return str(row[0])
    return None


def save_token_usage(
    *,
    username: str,
    image_number: int,
    file_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    duration_seconds: float,
    model: str,
    status: str = "success",
    error_message: str = "",
) -> None:
    """Persist one extraction usage event for audit and account summaries."""

    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT INTO token_usage (
                username, timestamp, image_number, file_name,
                prompt_tokens, completion_tokens, total_tokens,
                duration_seconds, model, status, error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _normalize_username(username),
                time.time(),
                image_number,
                file_name,
                int(prompt_tokens or 0),
                int(completion_tokens or 0),
                int(total_tokens or 0),
                float(duration_seconds or 0),
                model,
                status,
                error_message or "",
            ),
        )
        conn.commit()


def get_user_token_summary(username: str) -> dict[str, Any]:
    """Aggregate lifetime request and token usage for a user's profile menu."""

    with closing(get_connection()) as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(CASE WHEN status='success' THEN 1 END),
                COUNT(CASE WHEN status='error' THEN 1 END),
                COALESCE(SUM(CASE WHEN status='success' THEN prompt_tokens ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN status='success' THEN completion_tokens ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN status='success' THEN total_tokens ELSE 0 END), 0)
            FROM token_usage
            WHERE username=?
            """,
            (_normalize_username(username),),
        ).fetchone()

    return {
        "total_requests": int(row[0] or 0),
        "failed_requests": int(row[1] or 0),
        "prompt_tokens": int(row[2] or 0),
        "completion_tokens": int(row[3] or 0),
        "total_tokens": int(row[4] or 0),
    }
