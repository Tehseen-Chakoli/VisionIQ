"""Authentication actions for VisionIQ.

This module owns authentication state and account actions only. Forms, buttons,
and CSS belong in ``components.py`` so the logic remains testable and compact.
"""

from __future__ import annotations

import streamlit as st

from src.database import create_user, validate_user


def init_auth_state() -> None:
    """Initialize authentication keys used in Streamlit session state."""

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None


def login_user(username: str, password: str) -> bool:
    """Validate credentials and mark the session as authenticated."""

    clean_username = (username or "").strip().lower()
    if not clean_username or not password:
        return False

    if not validate_user(clean_username, password):
        return False

    st.session_state.logged_in = True
    st.session_state.username = clean_username
    return True


def register_user(username: str, password: str) -> bool:
    """Create an account using normalized email credentials."""

    clean_username = (username or "").strip().lower()
    if not clean_username or not password:
        return False

    return create_user(clean_username, password)


def logout() -> None:
    """Clear user-specific session state and restart the Streamlit script."""

    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.groq_api_key = None
    st.rerun()
