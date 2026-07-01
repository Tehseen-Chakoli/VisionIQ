"""Top-level Streamlit page flow for VisionIQ.

The UI coordinator decides which screen to show and delegates the actual visual
pieces to ``components.py``. This keeps navigation and app state easy to follow.
"""

from __future__ import annotations

import streamlit as st

from src.auth import init_auth_state
from src.components import (
    apply_global_styles,
    render_app_header,
    render_hero,
    render_login_page,
    render_pipeline_notice,
    render_profile_menu,
    render_section_card,
    render_usage_dashboard,
    render_batch_summary_panel,
)
from src.config import APP_NAME, GROQ_KEYS_URL, MAX_IMAGES
from src.database import get_groq_key, init_db, save_groq_key
from src.encryption import decrypt, encrypt
from src.groq_usage import GroqUsageTracker
from src.usage_store import get_api_daily_usage, init_api_daily_usage_table


def initialize_session_state() -> None:
    """Create Streamlit session keys used by the workspace shell."""

    if "groq_api_key" not in st.session_state:
        st.session_state.groq_api_key = None
    if "upload_widget_key" not in st.session_state:
        st.session_state.upload_widget_key = 0
    if "queued_file_names" not in st.session_state:
        st.session_state.queued_file_names = []
    if "groq_usage_tracker" not in st.session_state:
        st.session_state.groq_usage_tracker = GroqUsageTracker()


def run_app() -> None:
    """Initialize dependencies and render the correct page for the session."""

    st.set_page_config(page_title=APP_NAME, layout="wide")

    # Database and session initialization happen before any page branch so every
    # screen can safely read auth state or account data.
    init_db()
    init_api_daily_usage_table()
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
    """Load a saved model API key or render the key setup screen.

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
    """Render the one-time API key setup form for authenticated users."""

    render_hero()
    render_section_card(
        "Connect Model Access",
        "Save your API key once to enable secure document extraction for this account.",
    )

    st.link_button("Open Groq API Keys", GROQ_KEYS_URL, use_container_width=True)

    with st.form("save_groq_key_form"):
        user_key = st.text_input("API Key", type="password", placeholder="gsk_...")
        submitted = st.form_submit_button("Save API Key", use_container_width=True)

    if submitted:
        if not user_key.strip():
            st.error("Enter your API key before saving.")
        else:
            save_groq_key(username, encrypt(user_key.strip()))
            st.success("API key saved. Loading your workspace...")
            st.rerun()

    st.caption("Your key is encrypted before storage and used only for requests you initiate.")


def render_workspace(username: str, groq_api_key: str) -> None:
    """Render the authenticated VisionIQ workspace shell."""

    upload_key = get_upload_widget_key()
    queued_count = get_current_upload_count(upload_key)
    header_col, profile_col = st.columns([5.0, 1.0], gap="medium", vertical_alignment="top")

    with header_col:
        render_app_header(username)

    with profile_col:
        render_profile_menu(username)

    daily_usage = get_api_daily_usage(groq_api_key)
    usage_tracker: GroqUsageTracker = st.session_state.groq_usage_tracker
    render_usage_dashboard(session_usage=usage_tracker.as_dashboard_usage(daily_tokens=daily_usage["tokens"]))

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    upload_col, status_col = st.columns([1.65, 1.0], gap="large", vertical_alignment="top")

    with upload_col:
        render_upload_shell(groq_api_key=groq_api_key, upload_key=upload_key)

    with status_col:
        render_batch_summary_panel(
            username=username,
            queued_count=queued_count,
            queued_file_names=st.session_state.queued_file_names,
        )

    render_pipeline_notice()


def get_upload_widget_key() -> str:
    """Return the stable uploader key for the current widget generation."""

    return f"uploaded_images_{st.session_state.upload_widget_key}"


def get_current_upload_count(upload_key: str) -> int:
    """Read the current uploader state before the upload widget is rendered."""

    uploaded_files = st.session_state.get(upload_key, [])
    if uploaded_files:
        return len(uploaded_files)
    return len(st.session_state.queued_file_names)


def render_upload_shell(groq_api_key: str, upload_key: str) -> None:
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
        key=upload_key,
    )

    uploaded_count = len(uploaded_files) if uploaded_files else 0
    if uploaded_count > MAX_IMAGES:
        st.error(f"Upload no more than {MAX_IMAGES} images at a time.")
    elif uploaded_count:
        st.session_state.queued_file_names = [uploaded_file.name for uploaded_file in uploaded_files]
        st.success(f"{uploaded_count} image(s) queued for extraction.")

    st.markdown(
        """
<div class="vi-action-strip">
    <div class="vi-action-copy">Files are staged locally until extraction modules are connected.</div>
</div>
        """,
        unsafe_allow_html=True,
    )
    action_col, clear_col, _ = st.columns([1.0, 0.9, 2.8], gap="medium")
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
