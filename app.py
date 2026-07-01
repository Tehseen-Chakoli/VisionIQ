"""Streamlit entrypoint for the VisionIQ application.

This file intentionally stays small. All application setup, state handling, and
page rendering live in ``src.ui`` so the root entrypoint remains easy to audit.
"""

from src.ui import run_app


if __name__ == "__main__":
    # Streamlit imports this file, but keeping this guard also allows a direct
    # Python execution path during lightweight import checks.
    run_app()
