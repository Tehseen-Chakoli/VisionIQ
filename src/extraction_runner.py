"""Extraction orchestration for VisionIQ.

The runner coordinates uploads, image preparation, model calls, usage tracking,
and persistence. Streamlit UI code calls this module, but the lower-level model
and image services remain independent and testable.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Callable, Iterable

import streamlit as st

from src.config import DELAY_SECONDS, MAX_COMPLETION_TOKENS, MODEL_NAME
from src.database import save_token_usage
from src.file_utils import cleanup_temp_files, save_uploaded_file_to_temp
from src.groq_service import GroqExtractionResult, extract_questions_with_groq
from src.groq_usage import GroqUsageTracker, build_friendly_groq_error_message
from src.image_processor import ImagePrepConfig, ImagePrepResult, prepare_image_for_extraction
from src.usage_store import add_api_daily_usage


@dataclass
class ExtractionRecord:
    """Serializable result for one processed image in the current session."""

    image_number: int
    file_name: str
    output: str
    status: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_seconds: float = 0
    model: str = MODEL_NAME
    error_message: str = ""
    was_cropped: bool = False
    original_size: tuple[int, int] = (0, 0)
    final_size: tuple[int, int] = (0, 0)


def run_extraction_batch(
    *,
    uploaded_files: Iterable,
    username: str,
    groq_api_key: str,
    prep_config: ImagePrepConfig | None = None,
    usage_refresh: Callable[[], None] | None = None,
) -> list[dict[str, object]]:
    """Process uploaded files one by one and return session-ready results."""

    files = list(uploaded_files or [])
    if not files:
        st.warning("Add at least one image before starting extraction.")
        return []

    active_config = prep_config or ImagePrepConfig()
    tracker: GroqUsageTracker = st.session_state.groq_usage_tracker
    progress_bar = st.progress(0, text="Preparing extraction batch...")
    status_area = st.empty()
    results: list[dict[str, object]] = []

    for index, uploaded_file in enumerate(files, start=1):
        temp_paths: list[str] = []
        file_name = getattr(uploaded_file, "name", f"image_{index}")
        status_area.info(f"Processing {file_name} ({index}/{len(files)})")

        try:
            source_path = save_uploaded_file_to_temp(uploaded_file)
            temp_paths.append(source_path)

            prep_result = prepare_image_for_extraction(source_path, active_config)
            temp_paths.append(prep_result.output_path)

            extraction = extract_questions_with_groq(
                image_path=prep_result.output_path,
                image_number=index,
                groq_api_key=groq_api_key,
                max_completion_tokens=MAX_COMPLETION_TOKENS,
            )

            record = _build_success_record(index, file_name, prep_result, extraction)
            results.append(asdict(record))
            _record_success(username, file_name, index, extraction, tracker, groq_api_key)

            if usage_refresh:
                usage_refresh()

            status_area.success(f"Completed {file_name}")
        except Exception as exc:
            friendly_error = build_friendly_groq_error_message(str(exc))
            tracker.add_error(
                image_number=index,
                file_name=file_name,
                error_message=friendly_error,
                model=MODEL_NAME,
            )
            save_token_usage(
                username=username,
                image_number=index,
                file_name=file_name,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_seconds=0,
                model=MODEL_NAME,
                status="error",
                error_message=friendly_error,
            )
            results.append(asdict(_build_error_record(index, file_name, friendly_error)))
            status_area.error(f"{file_name}: {friendly_error}")

            # A rate-limit error usually affects the rest of the batch, so stop
            # early instead of spending requests on repeated failures.
            if tracker.last_limit_error:
                break
        finally:
            cleanup_temp_files(temp_paths)
            progress_bar.progress(index / len(files), text=f"Processed {index} of {len(files)} image(s)")

        if index < len(files):
            time.sleep(DELAY_SECONDS)

    st.session_state.extraction_results = results
    return results


def _build_success_record(
    image_number: int,
    file_name: str,
    prep_result: ImagePrepResult,
    extraction: GroqExtractionResult,
) -> ExtractionRecord:
    """Convert service outputs into the result shape used by UI and PDF export."""

    return ExtractionRecord(
        image_number=image_number,
        file_name=file_name,
        output=extraction.output,
        status="success",
        prompt_tokens=extraction.prompt_tokens,
        completion_tokens=extraction.completion_tokens,
        total_tokens=extraction.total_tokens,
        duration_seconds=round(extraction.duration_seconds, 2),
        model=extraction.model,
        was_cropped=prep_result.was_cropped,
        original_size=prep_result.original_size,
        final_size=prep_result.final_size,
    )


def _build_error_record(image_number: int, file_name: str, error_message: str) -> ExtractionRecord:
    """Create a result entry for a failed image so the batch remains auditable."""

    return ExtractionRecord(
        image_number=image_number,
        file_name=file_name,
        output="",
        status="error",
        error_message=error_message,
    )


def _record_success(
    username: str,
    file_name: str,
    image_number: int,
    extraction: GroqExtractionResult,
    tracker: GroqUsageTracker,
    groq_api_key: str,
) -> None:
    """Persist successful usage to both session and daily stores."""

    tracker.add_success(
        image_number=image_number,
        file_name=file_name,
        prompt_tokens=extraction.prompt_tokens,
        completion_tokens=extraction.completion_tokens,
        total_tokens=extraction.total_tokens,
        duration_seconds=extraction.duration_seconds,
        model=extraction.model,
    )
    save_token_usage(
        username=username,
        image_number=image_number,
        file_name=file_name,
        prompt_tokens=extraction.prompt_tokens,
        completion_tokens=extraction.completion_tokens,
        total_tokens=extraction.total_tokens,
        duration_seconds=extraction.duration_seconds,
        model=extraction.model,
        status="success",
    )
    add_api_daily_usage(groq_api_key, extraction.total_tokens)
