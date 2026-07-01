"""File handling utilities for uploaded images and generated exports.

Streamlit uploaded files live in memory. The processing pipeline needs stable
filesystem paths, so this module owns temporary-file creation and cleanup.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterable


def get_safe_suffix(file_name: str) -> str:
    """Return a conservative suffix for a user-uploaded file name.

    Only the extension is reused, and only for supported image types. This
    avoids placing user-controlled names into temp paths.
    """

    suffix = Path(file_name or "").suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg"}:
        return suffix
    return ".img"


def save_uploaded_file_to_temp(uploaded_file) -> str:
    """Persist one Streamlit upload to a temporary file and return its path."""

    suffix = get_safe_suffix(getattr(uploaded_file, "name", ""))
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.read())
        return temp_file.name


def cleanup_temp_files(file_paths: Iterable[str]) -> None:
    """Best-effort cleanup for temporary files created during processing."""

    for file_path in file_paths:
        if not file_path:
            continue
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            # Cleanup should never interrupt the user's completed extraction.
            continue


def get_temp_pdf_path(pdf_name: str) -> str:
    """Return a safe temporary path for a generated PDF export."""

    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in pdf_name.strip())
    safe_name = safe_name or "VisionIQ_Export"
    return str(Path(tempfile.gettempdir()) / f"{safe_name}.pdf")
