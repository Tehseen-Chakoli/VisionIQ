"""Top-level Streamlit page flow for VisionIQ.

The UI coordinator decides which screen to show and delegates the actual visual
pieces to ``components.py``. This keeps navigation and app state easy to follow.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from src.auth import init_auth_state
from src.components import (
    apply_global_styles,
    render_app_header,
    render_hero,
    render_login_page,
    render_pdf_export_controls,
    render_pipeline_notice,
    render_profile_menu,
    render_results_editor,
    render_section_card,
    render_usage_dashboard,
    render_batch_summary_panel,
)
from src.config import APP_NAME, GROQ_KEYS_URL, MAX_IMAGES
from src.database import (
    create_extraction_job,
    get_extraction_job,
    get_groq_key,
    init_db,
    list_extraction_jobs,
    save_groq_key,
    update_extraction_job,
)
from src.encryption import decrypt, encrypt
from src.extraction_runner import run_extraction_batch
from src.file_utils import get_temp_pdf_path
from src.groq_usage import GroqUsageTracker
from src.image_processor import ImagePrepConfig
from src.pdf_service import create_extraction_pdf
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
    if "extraction_results" not in st.session_state:
        st.session_state.extraction_results = []
    if "active_job_id" not in st.session_state:
        st.session_state.active_job_id = None
    if "active_job_name" not in st.session_state:
        st.session_state.active_job_name = ""
    if "job_results_last_saved" not in st.session_state:
        st.session_state.job_results_last_saved = 0.0


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

    usage_placeholder = st.empty()
    refresh_usage_dashboard(groq_api_key=groq_api_key, usage_placeholder=usage_placeholder)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    upload_col, status_col = st.columns([1.65, 1.0], gap="large", vertical_alignment="top")

    with upload_col:
        render_upload_shell(
            username=username,
            groq_api_key=groq_api_key,
            upload_key=upload_key,
            usage_placeholder=usage_placeholder,
        )

    with status_col:
        render_batch_summary_panel(
            username=username,
            queued_count=queued_count,
            queued_file_names=st.session_state.queued_file_names,
        )
        render_saved_jobs_panel(username)

    render_pipeline_notice()
    render_results_and_export(username)


def refresh_usage_dashboard(groq_api_key: str, usage_placeholder) -> None:
    """Render the quota dashboard from local daily and session usage data."""

    daily_usage = get_api_daily_usage(groq_api_key)
    usage_tracker: GroqUsageTracker = st.session_state.groq_usage_tracker
    with usage_placeholder.container():
        render_usage_dashboard(session_usage=usage_tracker.as_dashboard_usage(daily_tokens=daily_usage["tokens"]))


def get_upload_widget_key() -> str:
    """Return the stable uploader key for the current widget generation."""

    return f"uploaded_images_{st.session_state.upload_widget_key}"


def get_current_upload_count(upload_key: str) -> int:
    """Read the current uploader state before the upload widget is rendered."""

    uploaded_files = st.session_state.get(upload_key, [])
    if uploaded_files:
        return len(uploaded_files)
    return len(st.session_state.queued_file_names)


def render_upload_shell(username: str, groq_api_key: str, upload_key: str, usage_placeholder) -> None:
    """Render upload controls for the workspace shell.

    Uploaded files are staged in Streamlit state, then passed to the extraction
    runner when the user starts the batch.
    """

    render_section_card(
        "Upload Source Images",
        "Upload up to 30 PNG or JPEG images. VisionIQ will prepare, extract, and organize them into reviewed results.",
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
    <div class="vi-action-copy">Files are processed one at a time so usage tracking and errors stay transparent.</div>
</div>
        """,
        unsafe_allow_html=True,
    )
    action_col, clear_col, _ = st.columns([1.0, 0.9, 2.8], gap="medium")
    extract_clicked = False
    with action_col:
        extract_clicked = st.button("Start Extraction", type="primary", use_container_width=True)

    with clear_col:
        if st.button("Clear Uploads", use_container_width=True):
            st.session_state.upload_widget_key += 1
            st.session_state.queued_file_names = []
            st.session_state.extraction_results = []
            st.session_state.active_job_id = None
            st.session_state.active_job_name = ""
            st.rerun()

    if st.session_state.queued_file_names:
        st.caption("Queued files: " + ", ".join(st.session_state.queued_file_names))

    if extract_clicked:
        if not uploaded_files:
            st.warning("Select at least one image before starting extraction.")
        elif uploaded_count > MAX_IMAGES:
            st.error(f"Upload no more than {MAX_IMAGES} images at a time.")
        else:
            job_name = _build_batch_name([uploaded_file.name for uploaded_file in uploaded_files])
            results = run_extraction_batch(
                uploaded_files=uploaded_files,
                username=username,
                groq_api_key=groq_api_key,
                prep_config=ImagePrepConfig(),
                usage_refresh=lambda: refresh_usage_dashboard(groq_api_key, usage_placeholder),
            )
            if results:
                saved_job_id = create_extraction_job(
                    username=username,
                    job_name=job_name,
                    results=results,
                )
                st.session_state.active_job_id = saved_job_id
                st.session_state.active_job_name = job_name
                st.session_state.job_results_last_saved = _current_timestamp()
                st.success("Batch saved to extraction history.")

    _ = groq_api_key


def render_saved_jobs_panel(username: str) -> None:
    """Render recent saved jobs and allow restoring one into the workspace."""

    jobs = list_extraction_jobs(username)
    render_section_card(
        "Saved Batches",
        "Reopen a previous extraction batch, continue review edits, and export again without rerunning the model.",
    )

    if not jobs:
        st.caption("No saved batches yet. Completed extraction runs will appear here.")
        return

    active_job_id = st.session_state.get("active_job_id")
    for job in jobs:
        updated_at = datetime.fromtimestamp(job["updated_at"]).strftime("%d %b %Y, %I:%M %p")
        status_label = f"{job['success_count']} ready / {job['error_count']} needs attention"
        active_label = "Current batch" if active_job_id == job["id"] else "Load batch"

        with st.container(border=True):
            st.markdown(f"**{job['job_name']}**")
            st.markdown(
                f"""
<div class="vi-job-meta">{updated_at} | {job['source_count']} images | {job['total_tokens']:,} tokens</div>
<div class="vi-job-status">{status_label}</div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                active_label,
                key=f"load_job_{job['id']}",
                use_container_width=True,
                disabled=active_job_id == job["id"],
            ):
                _load_saved_job(username=username, job_id=job["id"])
                st.rerun()


def render_results_and_export(username: str) -> None:
    """Render editable extraction results and create PDF exports on demand."""

    results = st.session_state.get("extraction_results", [])
    if not results:
        return

    _render_active_job_banner()
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.session_state.extraction_results = render_results_editor(results)
    active_job_id = st.session_state.get("active_job_id")
    if active_job_id:
        save_col, stamp_col = st.columns([1.0, 2.2], gap="medium", vertical_alignment="center")
        with save_col:
            if st.button("Save Review Changes", use_container_width=True):
                update_extraction_job(
                    job_id=int(active_job_id),
                    username=username,
                    job_name=st.session_state.get("active_job_name") or None,
                    results=st.session_state.extraction_results,
                )
                st.session_state.job_results_last_saved = _current_timestamp()
                st.success("Saved the reviewed batch.")
        with stamp_col:
            saved_at = st.session_state.get("job_results_last_saved", 0.0)
            if saved_at:
                st.caption(f"Last saved {datetime.fromtimestamp(saved_at).strftime('%d %b %Y, %I:%M %p')}")

    suggested_pdf_name = (st.session_state.get("active_job_name") or "").strip() or None
    pdf_name, theme, export_clicked = render_pdf_export_controls(default_name=suggested_pdf_name)

    if export_clicked:
        successful_results = [
            result
            for result in st.session_state.extraction_results
            if str(result.get("status", "success")) == "success" and str(result.get("output", "")).strip()
        ]

        if not successful_results:
            st.warning("There is no reviewed extraction text to export yet.")
            return

        pdf_path = get_temp_pdf_path(pdf_name)
        create_extraction_pdf(
            results=successful_results,
            output_path=pdf_path,
            title=pdf_name,
            theme=theme,
        )

        with open(pdf_path, "rb") as pdf_file:
            st.download_button(
                "Download PDF",
                data=pdf_file,
                file_name=f"{pdf_name.strip() or 'VisionIQ_Export'}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


def _build_batch_name(file_names: list[str]) -> str:
    """Create a readable default job name from the current upload selection."""

    cleaned_names = [name.strip() for name in file_names if (name or "").strip()]
    timestamp = datetime.now().strftime("%d %b %Y %I:%M %p")
    if not cleaned_names:
        return f"Batch {timestamp}"
    if len(cleaned_names) == 1:
        return cleaned_names[0]
    if len(cleaned_names) == 2:
        return f"{cleaned_names[0]} + {cleaned_names[1]}"
    return f"{cleaned_names[0]} + {len(cleaned_names) - 1} more"


def _load_saved_job(*, username: str, job_id: int) -> None:
    """Load a stored extraction batch into the editable workspace state."""

    job = get_extraction_job(job_id, username)
    if not job:
        st.error("That saved batch could not be loaded.")
        return

    st.session_state.extraction_results = list(job["results"])
    st.session_state.active_job_id = int(job["id"])
    st.session_state.active_job_name = str(job["job_name"] or "")
    st.session_state.job_results_last_saved = float(job["updated_at"] or 0)
    st.session_state.queued_file_names = [str(result.get("file_name", "")) for result in job["results"]]


def _render_active_job_banner() -> None:
    """Show which saved batch is currently open in the review workspace."""

    active_job_name = (st.session_state.get("active_job_name") or "").strip()
    active_job_id = st.session_state.get("active_job_id")
    if not active_job_id:
        return

    label = active_job_name or f"Batch {active_job_id}"
    st.caption(f"Reviewing saved batch: {label}")


def _current_timestamp() -> float:
    """Return the current Unix timestamp for lightweight session bookkeeping."""

    return datetime.now().timestamp()
