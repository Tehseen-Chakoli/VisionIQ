"""Reusable Streamlit components for VisionIQ.

The component layer contains user-facing text, styling, and small rendering
functions. Business logic stays in auth/database/ui modules so visual changes do
not leak into persistence or authentication code.
"""

from __future__ import annotations

import streamlit as st

from src.auth import login_user, logout, register_user
from src.config import APP_NAME, APP_TAGLINE, GROQ_KEYS_URL
from src.database import get_user_token_summary


def apply_global_styles() -> None:
    """Inject the shared VisionIQ visual system into the Streamlit page."""

    st.markdown(
        """
<style>
.stApp {
    background:
        radial-gradient(circle at 18% 8%, rgba(0, 216, 245, 0.10), transparent 30%),
        radial-gradient(circle at 82% 18%, rgba(14, 255, 164, 0.06), transparent 28%),
        linear-gradient(135deg, #02070b 0%, #06151b 52%, #010507 100%) !important;
    color: #eafcff !important;
}
header, footer {visibility: hidden;}
[data-testid="stSidebar"] {display: none !important;}
.block-container {
    max-width: 1140px !important;
    padding-top: 1.1rem !important;
    padding-bottom: 3rem !important;
}
h1, h2, h3, h4, h5, h6, p, span, label, div {
    color: #eafcff;
}
a { color: #00d8f5 !important; }
.vi-hero {
    border: 1px solid rgba(0, 216, 245, 0.38);
    border-radius: 14px;
    background: linear-gradient(180deg, rgba(2, 24, 32, 0.96), rgba(1, 10, 15, 0.92));
    box-shadow: 0 0 38px rgba(0, 216, 245, 0.08);
    padding: 28px 24px 22px 24px;
    margin-bottom: 16px;
}
.vi-title {
    color: #00d8f5 !important;
    text-align: center;
    font-size: 44px;
    font-weight: 900;
    line-height: 1;
    margin: 0;
}
.vi-subtitle {
    text-align: center;
    color: #ffffff !important;
    font-weight: 760;
    margin-top: 10px;
    font-size: 14px;
}
.vi-rule {
    height: 1px;
    width: 90%;
    margin: 20px auto 0 auto;
    background: linear-gradient(90deg, transparent, rgba(0, 216, 245, 0.80), transparent);
}
.vi-card {
    border: 1px solid rgba(0, 216, 245, 0.34);
    border-radius: 12px;
    background: rgba(2, 16, 22, 0.78);
    box-shadow: 0 0 26px rgba(0, 216, 245, 0.055);
    padding: 20px;
    margin-bottom: 16px;
}
.vi-section-title {
    color: #00d8f5 !important;
    font-size: 23px;
    font-weight: 900;
    margin: 0 0 12px 0;
}
.vi-caption {
    color: rgba(234, 252, 255, 0.82) !important;
    font-size: 13px;
    line-height: 1.55;
}
.vi-pill {
    display: inline-block;
    color: #0effa4 !important;
    background: rgba(0, 255, 170, 0.08);
    border: 1px solid rgba(0, 255, 170, 0.20);
    border-radius: 6px;
    padding: 2px 7px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    overflow-wrap: anywhere;
}
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    background-color: rgba(0, 0, 0, 0.24) !important;
    color: #eafcff !important;
    border-color: rgba(0, 216, 245, 0.52) !important;
}
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, .stLinkButton > a {
    border-radius: 9px !important;
    border: 1px solid rgba(0, 216, 245, 0.70) !important;
    background: linear-gradient(135deg, #00d8f5, #0099b6) !important;
    color: #001014 !important;
    font-weight: 850 !important;
    box-shadow: 0 0 18px rgba(0, 216, 245, 0.18) !important;
    text-decoration: none !important;
}
.stFileUploader section {
    background: rgba(1, 11, 17, 0.64) !important;
    border: 1px dashed rgba(0, 216, 245, 0.70) !important;
    border-radius: 12px !important;
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
        st.markdown("### Groq API Access")
        st.write("Create or manage your Groq API key before processing documents.")
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
    """Render profile actions in a compact menu at the top of the workspace."""

    if hasattr(st, "popover"):
        with st.popover("Profile", use_container_width=True):
            render_profile_actions(username)
    else:
        with st.expander("Profile Actions", expanded=False):
            render_profile_actions(username)


def render_profile_actions(username: str) -> None:
    """Render account summary and sign-out controls for an authenticated user."""

    summary = get_user_token_summary(username)

    st.caption("Signed in as")
    st.code(username, language=None)
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
    if st.button("Sign Out", use_container_width=True):
        logout()


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


def render_pipeline_notice() -> None:
    """Explain that document processing modules are not connected yet."""

    st.info(
        "Document processing is being prepared. Image cleanup, extraction, usage "
        "tracking, and PDF export will be connected through dedicated modules."
    )
