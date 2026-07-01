"""Encryption helpers for sensitive user-owned values.

VisionIQ stores Groq API keys only after encrypting them with Fernet. The
encryption key should be supplied by Streamlit secrets in production, or by the
``FERNET_KEY`` environment variable during local development.
"""

from __future__ import annotations

import os

import streamlit as st
from cryptography.fernet import Fernet


def _get_secret_value(name: str) -> str | None:
    """Read a secret from Streamlit first, then fall back to the environment."""

    try:
        value = st.secrets.get(name)
    except Exception:
        # Streamlit raises when no secrets file is configured. Falling back to
        # the environment makes local CLI/import checks friendlier.
        value = None

    return str(value or os.getenv(name) or "") or None


def _get_cipher() -> Fernet:
    """Build the Fernet cipher used by ``encrypt`` and ``decrypt``."""

    key = _get_secret_value("FERNET_KEY")
    if not key:
        raise RuntimeError(
            "FERNET_KEY is missing. Add it to .streamlit/secrets.toml or set "
            "it as an environment variable before saving API keys."
        )

    return Fernet(key.encode("utf-8"))


def encrypt(text: str) -> str:
    """Encrypt plain text and return a database-safe string."""

    return _get_cipher().encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    """Decrypt a string produced by ``encrypt`` back to plain text."""

    return _get_cipher().decrypt(token.encode("utf-8")).decode("utf-8")
