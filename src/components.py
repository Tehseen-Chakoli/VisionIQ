"""Reusable Streamlit components for VisionIQ.

The component layer contains user-facing text, styling, and small rendering
functions. Business logic stays in auth/database/ui modules so visual changes do
not leak into persistence or authentication code.
"""

from __future__ import annotations

import streamlit as st

from src.auth import login_user, logout, register_user
from src.database import get_groq_key, get_user_token_summary, save_groq_key
from src.encryption import encrypt
from src.config import APP_NAME, APP_TAGLINE, DEFAULT_PDF_NAME, GROQ_KEYS_URL, PDF_THEMES, RPD_LIMIT, RPM_LIMIT, TPD_LIMIT, TPM_LIMIT


def apply_global_styles() -> None:
    """Inject the shared VisionIQ visual system into the Streamlit page."""

    st.markdown(
        """
<style>
.stApp {
    background:
        radial-gradient(circle at 8% 8%, rgba(49, 91, 143, 0.18), transparent 26%),
        radial-gradient(circle at 88% 14%, rgba(63, 143, 131, 0.18), transparent 28%),
        radial-gradient(circle at 50% 92%, rgba(147, 119, 84, 0.10), transparent 32%),
        linear-gradient(135deg, #e8eef4 0%, #f6f3ed 46%, #e7f1ef 100%) !important;
    color: #213040 !important;
}
header, footer {visibility: hidden;}
[data-testid="stSidebar"] {display: none !important;}
.block-container {
    max-width: 1120px !important;
    padding-top: 1.25rem !important;
    padding-bottom: 3rem !important;
}
h1, h2, h3, h4, h5, h6, p, span, label, div {
    color: #213040;
}
a { color: #315b8f !important; }
.vi-hero {
    border: 1px solid #cfd8e3;
    border-radius: 8px;
    background: #f8fafc;
    box-shadow: 0 12px 28px rgba(33, 48, 64, 0.08);
    padding: 24px 26px 20px 26px;
    margin-bottom: 18px;
}
.vi-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    border: 1px solid #cfd8e3;
    border-radius: 8px;
    background:
        linear-gradient(135deg, rgba(255, 255, 255, 0.96) 0%, rgba(241, 247, 250, 0.95) 100%),
        linear-gradient(90deg, rgba(49, 91, 143, 0.08), rgba(63, 143, 131, 0.08));
    box-shadow: 0 10px 24px rgba(33, 48, 64, 0.07);
    padding: 18px 20px;
    margin-bottom: 16px;
    animation: vi-rise 360ms ease-out both;
}
.vi-brand {
    display: flex;
    align-items: center;
    gap: 14px;
}
.vi-mark {
    width: 42px;
    height: 42px;
    border-radius: 8px;
    background: linear-gradient(135deg, #213040, #315b8f);
    color: #ffffff !important;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 850;
    letter-spacing: 0;
}
.vi-brand-name {
    color: #172233 !important;
    font-size: 24px;
    font-weight: 850;
    line-height: 1.05;
    letter-spacing: 0;
}
.vi-brand-subtitle {
    color: #66758a !important;
    font-size: 13px;
    font-weight: 650;
    margin-top: 3px;
}
.vi-topbar-meta {
    text-align: right;
    color: #6b7a8f !important;
    font-size: 12px;
    font-weight: 650;
}
.vi-account-card {
    border: 1px solid #cfd8e3;
    border-radius: 8px;
    background: #f8fafc;
    box-shadow: 0 10px 24px rgba(33, 48, 64, 0.055);
    padding: 12px;
    min-height: 96px;
    animation: vi-rise 420ms ease-out both;
}
.vi-account-label {
    color: #6b7a8f !important;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.vi-account-email {
    color: #172233 !important;
    font-size: 12px;
    font-weight: 700;
    line-height: 1.35;
    overflow-wrap: anywhere;
    margin-bottom: 8px;
}
.vi-title {
    color: #172233 !important;
    text-align: left;
    font-size: 38px;
    font-weight: 850;
    line-height: 1.05;
    margin: 0;
    letter-spacing: 0;
}
.vi-subtitle {
    text-align: left;
    color: #66758a !important;
    font-weight: 650;
    margin-top: 8px;
    font-size: 14px;
}
.vi-rule {
    height: 3px;
    width: 84px;
    margin: 18px 0 0 0;
    background: linear-gradient(90deg, #315b8f, #3f8f83);
    border-radius: 999px;
}
.vi-card {
    border: 1px solid #cfd8e3;
    border-radius: 8px;
    background:
        linear-gradient(180deg, rgba(248, 250, 252, 0.98), rgba(242, 247, 249, 0.98)),
        linear-gradient(90deg, rgba(49, 91, 143, 0.06), rgba(63, 143, 131, 0.06));
    box-shadow: 0 8px 20px rgba(33, 48, 64, 0.06);
    padding: 20px;
    margin-bottom: 16px;
    animation: vi-rise 440ms ease-out both;
}
.vi-card::before {
    content: "";
    display: block;
    width: 72px;
    height: 3px;
    border-radius: 999px;
    background: linear-gradient(90deg, #315b8f, #3f8f83, #b18b5e);
    margin-bottom: 14px;
}
.vi-panel {
    border: 1px solid #cfd8e3;
    border-radius: 8px;
    background:
        linear-gradient(180deg, rgba(248, 250, 252, 0.98), rgba(240, 247, 245, 0.98)),
        linear-gradient(135deg, rgba(63, 143, 131, 0.08), rgba(49, 91, 143, 0.04));
    box-shadow: 0 8px 20px rgba(33, 48, 64, 0.06);
    padding: 18px;
    min-height: 100%;
    animation: vi-rise 480ms ease-out both;
}
.vi-section-title {
    color: #172233 !important;
    font-size: 22px;
    font-weight: 800;
    margin: 0 0 10px 0;
}
.vi-caption {
    color: #66758a !important;
    font-size: 13px;
    line-height: 1.6;
}
.vi-kpi {
    border: 1px solid #cfd8e3;
    border-radius: 8px;
    background:
        linear-gradient(180deg, #fbfcfe 0%, #f2f6f9 100%),
        linear-gradient(135deg, rgba(49, 91, 143, 0.08), rgba(63, 143, 131, 0.06));
    box-shadow: 0 8px 18px rgba(33, 48, 64, 0.055);
    padding: 14px 15px;
    min-height: 92px;
    transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
    animation: vi-rise 420ms ease-out both;
}
.vi-kpi:nth-child(1) {
    border-top: 3px solid #315b8f;
}
.vi-kpi:hover {
    border-color: #abc4dc;
    box-shadow: 0 12px 24px rgba(49, 91, 143, 0.10);
    transform: translateY(-1px);
}
.vi-kpi-label {
    color: #6b7a8f !important;
    font-size: 12px;
    font-weight: 750;
    margin-bottom: 8px;
}
.vi-kpi::before {
    content: "";
    display: block;
    width: 32px;
    height: 3px;
    border-radius: 999px;
    background: #315b8f;
    margin-bottom: 10px;
}
.stColumn:nth-of-type(2) .vi-kpi::before {
    background: #3f8f83;
}
.stColumn:nth-of-type(3) .vi-kpi::before {
    background: #8b5cf6;
}
.stColumn:nth-of-type(4) .vi-kpi::before {
    background: #b18b5e;
}
.vi-kpi-value {
    color: #172233 !important;
    font-size: 22px;
    font-weight: 850;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
}
.vi-kpi-value-small {
    color: #172233 !important;
    font-size: 18px;
    font-weight: 850;
    line-height: 1.18;
    font-variant-numeric: tabular-nums;
}
.vi-kpi-note {
    color: #6b7a8f !important;
    font-size: 11px;
    margin-top: 7px;
}
.vi-kpi-remaining {
    display: inline-block;
    color: #35685f !important;
    background: #e8f3f0;
    border: 1px solid #b8d8d0;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 750;
    margin-top: 8px;
}
.vi-action-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border: 1px solid #cfd8e3;
    border-radius: 8px;
    background:
        linear-gradient(90deg, rgba(49, 91, 143, 0.08), rgba(63, 143, 131, 0.09)),
        #f3f7f8;
    padding: 12px;
    margin-top: 12px;
}
.vi-action-copy {
    color: #66758a !important;
    font-size: 12px;
    line-height: 1.45;
}
.vi-status-list {
    margin: 10px 0 0 0;
    padding-left: 18px;
}
.vi-batch-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid #e1e8ef;
}
.vi-batch-row:nth-child(3) .vi-batch-value {
    color: #315b8f !important;
}
.vi-batch-row:nth-child(4) .vi-batch-value {
    color: #3f8f83 !important;
}
.vi-batch-row:nth-child(5) .vi-batch-value {
    color: #8b5cf6 !important;
}
.vi-batch-row:nth-child(6) .vi-batch-value {
    color: #b18b5e !important;
}
.vi-batch-row:last-child {
    border-bottom: 0;
}
.vi-batch-label {
    color: #6b7a8f !important;
    font-size: 12px;
    font-weight: 750;
}
.vi-batch-value {
    color: #172233 !important;
    font-size: 12px;
    font-weight: 800;
    text-align: right;
    flex: 1 1 auto;
    min-width: 0;
    overflow-wrap: anywhere;
}
.vi-job-meta {
    color: #66758a !important;
    font-size: 12px;
    line-height: 1.5;
}
.vi-job-status {
    color: #35685f !important;
    font-size: 12px;
    font-weight: 750;
    margin-top: 4px;
}
.vi-status-list li {
    color: #314155 !important;
    margin-bottom: 8px;
    line-height: 1.45;
}
.vi-result-meta {
    color: #66758a !important;
    font-size: 12px;
    line-height: 1.5;
    margin-bottom: 10px;
}
.vi-result-ok {
    color: #35685f !important;
    font-weight: 800;
}
.vi-result-error {
    color: #9a3d3d !important;
    font-weight: 800;
}
.vi-pill {
    display: inline-block;
    color: #35685f !important;
    background: #e8f3f0;
    border: 1px solid #b8d8d0;
    border-radius: 6px;
    padding: 2px 7px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    overflow-wrap: anywhere;
}
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    background-color: #fbfcfe !important;
    color: #213040 !important;
    border-color: #b9c7d6 !important;
    border-radius: 8px !important;
}
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, .stLinkButton > a {
    border-radius: 8px !important;
    border: 1px solid #254b77 !important;
    background: linear-gradient(135deg, #315b8f 0%, #2f6f85 52%, #3f8f83 100%) !important;
    color: #ffffff !important;
    font-weight: 750 !important;
    box-shadow: 0 8px 18px rgba(49, 91, 143, 0.18) !important;
    text-decoration: none !important;
}
.stButton > button[kind="secondary"] {
    border-color: #b9c7d6 !important;
    background: #f8fafc !important;
    color: #213040 !important;
    box-shadow: none !important;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover, .stLinkButton > a:hover {
    border-color: #203f64 !important;
    background: linear-gradient(135deg, #284c78 0%, #2d6277 52%, #356f68 100%) !important;
}
.stFileUploader section {
    background:
        linear-gradient(135deg, rgba(49, 91, 143, 0.06), rgba(63, 143, 131, 0.08)),
        #f3f7f8 !important;
    border: 1px dashed #7d9bb7 !important;
    border-radius: 8px !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #cfd8e3 !important;
    background: #f8fafc !important;
    box-shadow: 0 8px 20px rgba(33, 48, 64, 0.055) !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 14px;
    border-bottom: 1px solid #d9e1ea;
}
.stTabs [data-baseweb="tab"] p {
    color: #66758a !important;
    font-weight: 700 !important;
}
.stTabs [aria-selected="true"] p {
    color: #315b8f !important;
}
.stAlert {
    border-radius: 8px !important;
    border-color: #d9dee7 !important;
}
@keyframes vi-rise {
    from {
        opacity: 0;
        transform: translateY(7px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
@media (max-width: 760px) {
    .vi-topbar {
        align-items: flex-start;
        flex-direction: column;
    }
    .vi-topbar-meta {
        text-align: left;
    }
    .vi-title {
        font-size: 32px;
    }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    """Render the product identity block used on authenticated pages."""

    st.markdown(
        f"""
<div class="vi-hero">
    <div class="vi-title">{APP_NAME}</div>
    <div class="vi-subtitle">{APP_TAGLINE}</div>
    <div class="vi-rule"></div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(username: str) -> None:
    """Render the primary workspace header with brand and account context."""

    st.markdown(
        f"""
<div class="vi-topbar">
    <div class="vi-brand">
        <div class="vi-mark">VI</div>
        <div>
            <div class="vi-brand-name">{APP_NAME}</div>
            <div class="vi-brand-subtitle">{APP_TAGLINE}</div>
        </div>
    </div>
    <div class="vi-topbar-meta">Document workspace<br>Secure extraction setup</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_login_page() -> None:
    """Render the unauthenticated sign-in and account creation experience."""

    apply_global_styles()
    render_hero()
    render_api_access_intro()
    render_auth_forms()
    render_security_note()


def render_api_access_intro() -> None:
    """Explain why external model access is needed before the user signs in."""

    with st.container(border=True):
        st.markdown("### Model Access")
        st.write("Connect an API key to process uploaded documents securely.")
        st.link_button("Open Groq API Keys", GROQ_KEYS_URL)
        st.caption(
            "After signing in, you can save the key once for your account. "
            "VisionIQ encrypts it before storage."
        )


def render_auth_forms() -> None:
    """Render sign-in and registration forms and route submissions to auth logic."""

    with st.container(border=True):
        sign_in_tab, create_account_tab = st.tabs(["Sign In", "Create Account"])

        with sign_in_tab:
            with st.form("sign_in_form", clear_on_submit=False):
                email = st.text_input("Email", key="sign_in_email")
                password = st.text_input("Password", type="password", key="sign_in_password")
                submitted = st.form_submit_button("Sign In")

                if submitted:
                    if not email.strip() or not password:
                        st.error("Enter your email and password to continue.")
                    elif login_user(email, password):
                        st.rerun()
                    else:
                        st.error("The email or password is incorrect.")

        with create_account_tab:
            with st.form("create_account_form", clear_on_submit=False):
                email = st.text_input("Email", key="create_account_email")
                password = st.text_input("Password", type="password", key="create_account_password")
                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    key="create_account_confirm_password",
                )
                submitted = st.form_submit_button("Create Account")

                if submitted:
                    if not email.strip() or not password:
                        st.error("Enter an email and password to create an account.")
                    elif password != confirm_password:
                        st.error("The password confirmation does not match.")
                    elif register_user(email, password):
                        st.success("Account created. You can now sign in.")
                    else:
                        st.error("An account with this email already exists.")


def render_security_note() -> None:
    """Render a concise trust note for key storage and request handling."""

    with st.container(border=True):
        st.markdown("### Private by Design")
        st.caption(
            "Your API key is encrypted before storage and used only for extraction "
            "requests you initiate."
        )


def render_profile_menu(username: str) -> None:
    """Render account context and profile actions in a compact header card."""

    with st.container(border=True):
        st.markdown('<div class="vi-account-label">Account</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="vi-account-email">{username}</div>', unsafe_allow_html=True)
        if hasattr(st, "popover"):
            with st.popover("Manage", use_container_width=True):
                render_profile_actions(username)
        else:
            with st.expander("Manage", expanded=False):
                render_profile_actions(username)


def render_profile_actions(username: str) -> None:
    """Render account summary and sign-out controls for an authenticated user."""

    summary = get_user_token_summary(username)
    key_is_saved = bool(get_groq_key(username))

    st.caption("Signed in as")
    st.code(username, language=None)
    if key_is_saved:
        st.success("API key connected")
    st.markdown("**Account Usage**")

    request_col, token_col = st.columns(2)
    with request_col:
        st.metric("Requests", f"{summary['total_requests']:,}")
    with token_col:
        st.metric("Tokens", f"{summary['total_tokens']:,}")

    st.caption(
        f"Prompt: {summary['prompt_tokens']:,} | "
        f"Completion: {summary['completion_tokens']:,} | "
        f"Errors: {summary['failed_requests']:,}"
    )

    st.divider()
    with st.form("change_api_key_form"):
        new_key = st.text_input("Change API Key", type="password", placeholder="Paste a new gsk_... key")
        save_clicked = st.form_submit_button("Save API Key", use_container_width=True)

    if save_clicked:
        if not new_key.strip():
            st.error("Enter an API key before saving.")
        else:
            save_groq_key(username, encrypt(new_key.strip()))
            st.session_state.groq_api_key = new_key.strip()
            st.success("API key updated.")
            st.rerun()

    if st.button("Sign Out", use_container_width=True):
        logout()


def _format_number(value: int) -> str:
    """Format dashboard numbers with grouping for quick scanning."""

    return f"{int(value or 0):,}"


def render_usage_dashboard(session_usage: dict[str, int]) -> None:
    """Render operational quota metrics modeled after the original useful dashboard."""

    usage_items = [
        ("Requests / min", session_usage["requests_last_minute"], RPM_LIMIT),
        ("Tokens / min", session_usage["tokens_last_minute"], TPM_LIMIT),
        ("Session requests", session_usage["session_requests"], RPD_LIMIT),
        ("Tokens / day", session_usage["tokens_today"], TPD_LIMIT),
    ]

    columns = st.columns(4, gap="small")
    for column, (label, used, limit) in zip(columns, usage_items):
        remaining = max(0, limit - used)
        with column:
            st.markdown(
                f"""
<div class="vi-kpi">
    <div class="vi-kpi-label">{label}</div>
    <div class="vi-kpi-value-small">{_format_number(used)} / {_format_number(limit)}</div>
    <div class="vi-kpi-remaining">{_format_number(remaining)} remaining</div>
</div>
                """,
                unsafe_allow_html=True,
            )


def render_section_card(title: str, body: str) -> None:
    """Render a reusable section heading card with consistent spacing."""

    st.markdown(
        f"""
<div class="vi-card">
    <div class="vi-section-title">{title}</div>
    <div class="vi-caption">{body}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_batch_summary_panel(username: str, queued_count: int, queued_file_names: list[str]) -> None:
    """Render practical batch and account context beside the upload workflow."""

    summary = get_user_token_summary(username)
    files_label = "No files selected"
    if queued_file_names:
        visible_names = queued_file_names[:3]
        files_label = ", ".join(visible_names)
        if len(queued_file_names) > 3:
            files_label += f" +{len(queued_file_names) - 3} more"

    st.markdown(
        f"""
<div class="vi-panel">
    <div class="vi-section-title">Batch Summary</div>
    <div class="vi-caption">
        Review the current batch before starting extraction.
    </div>
    <div class="vi-batch-row">
        <div class="vi-batch-label">Queued images</div>
        <div class="vi-batch-value">{_format_number(queued_count)}</div>
    </div>
    <div class="vi-batch-row">
        <div class="vi-batch-label">Selected files</div>
        <div class="vi-batch-value">{files_label}</div>
    </div>
    <div class="vi-batch-row">
        <div class="vi-batch-label">Lifetime requests</div>
        <div class="vi-batch-value">{_format_number(summary["total_requests"])}</div>
    </div>
    <div class="vi-batch-row">
        <div class="vi-batch-label">Lifetime tokens</div>
        <div class="vi-batch-value">{_format_number(summary["total_tokens"])}</div>
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_pipeline_notice() -> None:
    """Render a concise note for the connected processing workflow."""

    st.info(
        "Image cleanup, extraction, usage tracking, review, and PDF export are connected as separate services."
    )


def render_results_editor(results: list[dict[str, object]]) -> list[dict[str, object]]:
    """Render editable extraction results and return the updated list."""

    if not results:
        return []

    render_section_card(
        "Review Extracted Text",
        "Check each image result, correct any OCR issues, and export only the reviewed text.",
    )

    updated_results: list[dict[str, object]] = []
    active_job_key = st.session_state.get("active_job_id", "session")
    for index, result in enumerate(results):
        edited_result = dict(result)
        file_name = str(edited_result.get("file_name", f"Image {index + 1}"))
        status = str(edited_result.get("status", "success"))
        status_class = "vi-result-ok" if status == "success" else "vi-result-error"
        status_label = "Ready" if status == "success" else "Needs attention"

        with st.expander(f"{index + 1}. {file_name}", expanded=index == 0):
            st.markdown(
                f"""
<div class="vi-result-meta">
    Status: <span class="{status_class}">{status_label}</span><br>
    Tokens: {_format_number(int(edited_result.get("total_tokens", 0) or 0))} |
    Duration: {float(edited_result.get("duration_seconds", 0) or 0):.2f}s |
    Final image: {edited_result.get("final_size", (0, 0))}
</div>
                """,
                unsafe_allow_html=True,
            )

            if status != "success":
                st.warning(str(edited_result.get("error_message", "This image could not be extracted.")))

            edited_result["output"] = st.text_area(
                "Extracted text",
                value=str(edited_result.get("output", "")),
                height=260,
                key=f"visioniq_result_text_{active_job_key}_{index}",
            )
            updated_results.append(edited_result)

    return updated_results


def render_pdf_export_controls(default_name: str | None = None) -> tuple[str, str, bool]:
    """Render PDF export options and return the selected values."""

    with st.container(border=True):
        st.markdown("### Export")
        name_col, theme_col, button_col = st.columns([1.5, 0.8, 0.8], gap="medium", vertical_alignment="bottom")
        with name_col:
            pdf_name = st.text_input("PDF file name", value=(default_name or DEFAULT_PDF_NAME))
        with theme_col:
            theme = st.selectbox("Theme", PDF_THEMES)
        with button_col:
            export_clicked = st.button("Generate PDF", type="primary", use_container_width=True)

    return pdf_name, theme, export_clicked
