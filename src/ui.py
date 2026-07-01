"""Top-level Streamlit page flow for VisionIQ.

The UI coordinator decides which screen to show and delegates the actual visual
pieces to ``components.py``. This keeps navigation and app state easy to follow.
"""

from __future__ import annotations

import streamlit as st

from src.auth import init_auth_state
from src.components import (
    apply_global_styles,
    render_hero,
    render_login_page,
    render_pipeline_notice,
    render_profile_menu,
    render_section_card,
)
from src.config import APP_NAME, GROQ_KEYS_URL, MAX_IMAGES
from src.database import get_groq_key, init_db, save_groq_key
from src.encryption import decrypt, encrypt


def initialize_session_state() -> None:
    """Create Streamlit session keys used by the workspace shell."""

    if "groq_api_key" not in st.session_state:
        st.session_state.groq_api_key = None
    if "upload_widget_key" not in st.session_state:
        st.session_state.upload_widget_key = 0
    if "queued_file_names" not in st.session_state:
        st.session_state.queued_file_names = []


def run_app() -> None:
    """Initialize dependencies and render the correct page for the session."""

    st.set_page_config(page_title=APP_NAME, layout="wide")

    # Database and session initialization happen before any page branch so every
    # screen can safely read auth state or account data.
    init_db()
    init_auth_state()
    initialize_session_state()

    if not st.session_state.logged_in:
        render_login_page()
        st.stop()

    apply_global_styles()

    username = st.session_state.username
    groq_api_key = load_or_request_groq_key(username)
    if not groq_api_key:
        st.stop()

    render_workspace(username=username, groq_api_key=groq_api_key)


def load_or_request_groq_key(username: str) -> str | None:
    """Load a saved Groq key or render the key setup screen.

    A return value of ``None`` means the key is missing or unavailable, so the
    caller should stop rendering the authenticated workspace.
    """

    saved_key = get_groq_key(username)
    if saved_key:
        try:
            groq_api_key = decrypt(saved_key)
            st.session_state.groq_api_key = groq_api_key
            return groq_api_key
        except Exception:
            # Decryption can fail if the deployment uses a different FERNET_KEY.
            st.session_state.groq_api_key = None
            st.error("Your saved Groq API key could not be decrypted. Please update the key to continue.")

    render_api_key_setup(username)
    return None


def render_api_key_setup(username: str) -> None:
    """Render the one-time Groq API key setup form for authenticated users."""

    render_hero()
    render_section_card(
        "Connect Groq API Access",
        "Save your Groq API key once to enable secure document extraction for this account.",
    )

    st.link_button("Open Groq API Keys", GROQ_KEYS_URL, use_container_width=True)

    with st.form("save_groq_key_form"):
        user_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
        submitted = st.form_submit_button("Save API Key", use_container_width=True)

    if submitted:
        if not user_key.strip():
            st.error("Enter your Groq API key before saving.")
        else:
            save_groq_key(username, encrypt(user_key.strip()))
            st.success("Groq API key saved. Loading your workspace...")
            st.rerun()

    st.caption("Your key is encrypted before storage and used only for requests you initiate.")


def render_workspace(username: str, groq_api_key: str) -> None:
    """Render the authenticated VisionIQ workspace shell."""

    header_col, profile_col = st.columns([5.3, 1.0], gap="large", vertical_alignment="top")

    with header_col:
        render_hero()

    with profile_col:
        # A small spacer aligns the popover with the visual height of the hero.
        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
        render_profile_menu(username)

    render_upload_shell(groq_api_key=groq_api_key)
    render_pipeline_notice()


def render_upload_shell(groq_api_key: str) -> None:
    """Render upload controls for the workspace shell.

    The current workspace queues files only. Processing modules will later
    consume these uploaded files for preparation, extraction, and export.
    """

    render_section_card(
        "Upload Source Images",
        "Upload up to 30 PNG or JPEG images. Processing modules will use these files for extraction and export.",
    )

    uploaded_files = st.file_uploader(
        "Select PNG or JPEG images",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key=f"uploaded_images_{st.session_state.upload_widget_key}",
    )

    uploaded_count = len(uploaded_files) if uploaded_files else 0
    if uploaded_count > MAX_IMAGES:
        st.error(f"Upload no more than {MAX_IMAGES} images at a time.")
    elif uploaded_count:
        st.session_state.queued_file_names = [uploaded_file.name for uploaded_file in uploaded_files]
        st.success(f"{uploaded_count} image(s) queued for extraction.")

    action_col, clear_col, _ = st.columns([1.1, 1.0, 3.0], gap="large")
    with action_col:
        if st.button("Start Extraction", type="primary", use_container_width=True):
            st.info("Extraction is not connected yet. The processing pipeline will be added as dedicated modules.")

    with clear_col:
        if st.button("Clear Uploads", use_container_width=True):
            st.session_state.upload_widget_key += 1
            st.session_state.queued_file_names = []
            st.rerun()

    if st.session_state.queued_file_names:
        st.caption("Queued files: " + ", ".join(st.session_state.queued_file_names))

    # This keeps the authenticated API key available for the processing pipeline
    # once extraction modules are connected.
    _ = groq_api_key
