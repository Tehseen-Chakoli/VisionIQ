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
from typing import Any, Mapping, Sequence

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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS extraction_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                job_name TEXT NOT NULL,
                source_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                model TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS extraction_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                image_number INTEGER,
                file_name TEXT,
                output TEXT DEFAULT '',
                status TEXT DEFAULT 'success',
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0,
                model TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                was_cropped INTEGER DEFAULT 0,
                original_width INTEGER DEFAULT 0,
                original_height INTEGER DEFAULT 0,
                final_width INTEGER DEFAULT 0,
                final_height INTEGER DEFAULT 0,
                FOREIGN KEY(job_id) REFERENCES extraction_jobs(id) ON DELETE CASCADE
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


def _coerce_size_pair(value: object) -> tuple[int, int]:
    """Normalize stored image size values into a predictable integer pair."""

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return int(value[0] or 0), int(value[1] or 0)
    return 0, 0


def _summarize_results(results: Sequence[Mapping[str, object]]) -> dict[str, int | str]:
    """Build batch summary values stored on the extraction job row."""

    normalized_results = list(results)
    success_count = sum(1 for result in normalized_results if str(result.get("status", "success")) == "success")
    error_count = sum(1 for result in normalized_results if str(result.get("status", "success")) != "success")
    total_tokens = sum(int(result.get("total_tokens", 0) or 0) for result in normalized_results)
    model_names = [str(result.get("model", "")).strip() for result in normalized_results if str(result.get("model", "")).strip()]
    return {
        "source_count": len(normalized_results),
        "success_count": success_count,
        "error_count": error_count,
        "total_tokens": total_tokens,
        "model": model_names[0] if model_names else "",
    }


def create_extraction_job(
    *,
    username: str,
    job_name: str,
    results: Sequence[Mapping[str, object]],
) -> int:
    """Persist a newly completed extraction batch and return its job id."""

    now = time.time()
    summary = _summarize_results(results)
    clean_username = _normalize_username(username)
    clean_job_name = (job_name or "Untitled Batch").strip() or "Untitled Batch"

    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            INSERT INTO extraction_jobs (
                username, created_at, updated_at, job_name,
                source_count, success_count, error_count, total_tokens, model
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean_username,
                now,
                now,
                clean_job_name,
                summary["source_count"],
                summary["success_count"],
                summary["error_count"],
                summary["total_tokens"],
                summary["model"],
            ),
        )
        job_id = int(cursor.lastrowid)
        _replace_extraction_items(conn, job_id, results)
        conn.commit()
    return job_id


def update_extraction_job(
    *,
    job_id: int,
    username: str,
    results: Sequence[Mapping[str, object]],
    job_name: str | None = None,
) -> None:
    """Replace the stored job results after the user edits a batch review."""

    now = time.time()
    summary = _summarize_results(results)
    clean_username = _normalize_username(username)

    with closing(get_connection()) as conn:
        existing = conn.execute(
            "SELECT job_name FROM extraction_jobs WHERE id=? AND username=?",
            (int(job_id), clean_username),
        ).fetchone()
        if not existing:
            return

        final_job_name = (job_name or str(existing[0] or "")).strip() or "Untitled Batch"
        conn.execute(
            """
            UPDATE extraction_jobs
            SET updated_at=?, job_name=?, source_count=?, success_count=?,
                error_count=?, total_tokens=?, model=?
            WHERE id=? AND username=?
            """,
            (
                now,
                final_job_name,
                summary["source_count"],
                summary["success_count"],
                summary["error_count"],
                summary["total_tokens"],
                summary["model"],
                int(job_id),
                clean_username,
            ),
        )
        _replace_extraction_items(conn, int(job_id), results)
        conn.commit()


def _replace_extraction_items(
    conn: sqlite3.Connection,
    job_id: int,
    results: Sequence[Mapping[str, object]],
) -> None:
    """Rewrite all child rows for one extraction job."""

    conn.execute("DELETE FROM extraction_items WHERE job_id=?", (int(job_id),))
    for result in results:
        original_width, original_height = _coerce_size_pair(result.get("original_size"))
        final_width, final_height = _coerce_size_pair(result.get("final_size"))
        conn.execute(
            """
            INSERT INTO extraction_items (
                job_id, image_number, file_name, output, status,
                prompt_tokens, completion_tokens, total_tokens, duration_seconds,
                model, error_message, was_cropped, original_width,
                original_height, final_width, final_height
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(job_id),
                int(result.get("image_number", 0) or 0),
                str(result.get("file_name", "") or ""),
                str(result.get("output", "") or ""),
                str(result.get("status", "success") or "success"),
                int(result.get("prompt_tokens", 0) or 0),
                int(result.get("completion_tokens", 0) or 0),
                int(result.get("total_tokens", 0) or 0),
                float(result.get("duration_seconds", 0) or 0),
                str(result.get("model", "") or ""),
                str(result.get("error_message", "") or ""),
                1 if bool(result.get("was_cropped", False)) else 0,
                original_width,
                original_height,
                final_width,
                final_height,
            ),
        )


def list_extraction_jobs(username: str, limit: int = 12) -> list[dict[str, Any]]:
    """Return the most recent saved extraction batches for one account."""

    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT
                id, job_name, created_at, updated_at, source_count,
                success_count, error_count, total_tokens, model
            FROM extraction_jobs
            WHERE username=?
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (_normalize_username(username), int(limit)),
        ).fetchall()

    return [
        {
            "id": int(row[0]),
            "job_name": str(row[1] or ""),
            "created_at": float(row[2] or 0),
            "updated_at": float(row[3] or 0),
            "source_count": int(row[4] or 0),
            "success_count": int(row[5] or 0),
            "error_count": int(row[6] or 0),
            "total_tokens": int(row[7] or 0),
            "model": str(row[8] or ""),
        }
        for row in rows
    ]


def get_extraction_job(job_id: int, username: str) -> dict[str, Any] | None:
    """Load one saved extraction batch and all of its reviewed items."""

    clean_username = _normalize_username(username)
    with closing(get_connection()) as conn:
        job_row = conn.execute(
            """
            SELECT
                id, job_name, created_at, updated_at, source_count,
                success_count, error_count, total_tokens, model
            FROM extraction_jobs
            WHERE id=? AND username=?
            """,
            (int(job_id), clean_username),
        ).fetchone()
        if not job_row:
            return None

        item_rows = conn.execute(
            """
            SELECT
                image_number, file_name, output, status, prompt_tokens,
                completion_tokens, total_tokens, duration_seconds, model,
                error_message, was_cropped, original_width, original_height,
                final_width, final_height
            FROM extraction_items
            WHERE job_id=?
            ORDER BY image_number ASC, id ASC
            """,
            (int(job_id),),
        ).fetchall()

    return {
        "id": int(job_row[0]),
        "job_name": str(job_row[1] or ""),
        "created_at": float(job_row[2] or 0),
        "updated_at": float(job_row[3] or 0),
        "source_count": int(job_row[4] or 0),
        "success_count": int(job_row[5] or 0),
        "error_count": int(job_row[6] or 0),
        "total_tokens": int(job_row[7] or 0),
        "model": str(job_row[8] or ""),
        "results": [
            {
                "image_number": int(row[0] or 0),
                "file_name": str(row[1] or ""),
                "output": str(row[2] or ""),
                "status": str(row[3] or "success"),
                "prompt_tokens": int(row[4] or 0),
                "completion_tokens": int(row[5] or 0),
                "total_tokens": int(row[6] or 0),
                "duration_seconds": float(row[7] or 0),
                "model": str(row[8] or ""),
                "error_message": str(row[9] or ""),
                "was_cropped": bool(row[10]),
                "original_size": (int(row[11] or 0), int(row[12] or 0)),
                "final_size": (int(row[13] or 0), int(row[14] or 0)),
            }
            for row in item_rows
        ],
    }
