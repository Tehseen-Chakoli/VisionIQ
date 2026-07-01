"""Session-level Groq usage tracking for VisionIQ.

The tracker records successful and failed calls during the current Streamlit
session. It is intentionally independent from the database so the UI can update
quickly during processing and persistence can remain a separate concern.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from src.config import MODEL_NAME, RPD_LIMIT, RPM_LIMIT, TPD_LIMIT, TPM_LIMIT


@dataclass
class GroqLimitConfig:
    """Editable quota defaults used by the dashboard and error context."""

    model_name: str = MODEL_NAME
    rpm_limit: int = RPM_LIMIT
    rpd_limit: int = RPD_LIMIT
    tpm_limit: int = TPM_LIMIT
    tpd_limit: int = TPD_LIMIT


@dataclass
class GroqCallUsage:
    """One model request or failed request observed during the session."""

    timestamp: float
    image_number: int
    file_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_seconds: float
    model: str
    status: str = "success"
    error_message: str = ""


@dataclass
class GroqObservedLimitError:
    """Structured information parsed from a Groq rate-limit error."""

    limit_type: str = ""
    limit: int | None = None
    used: int | None = None
    requested: int | None = None
    retry_after_text: str = ""
    raw_message: str = ""

    @property
    def remaining_before_request(self) -> int | None:
        """Return remaining quota before the failed request, when available."""

        if self.limit is None or self.used is None:
            return None
        return max(0, self.limit - self.used)


@dataclass
class GroqUsageTracker:
    """In-memory usage model for the current Streamlit browser session."""

    limits: GroqLimitConfig = field(default_factory=GroqLimitConfig)
    calls: list[GroqCallUsage] = field(default_factory=list)
    last_limit_error: GroqObservedLimitError | None = None

    def add_success(
        self,
        *,
        image_number: int,
        file_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        duration_seconds: float,
        model: str,
    ) -> None:
        """Append one successful extraction request to session history."""

        self.calls.append(
            GroqCallUsage(
                timestamp=time.time(),
                image_number=image_number,
                file_name=file_name,
                prompt_tokens=int(prompt_tokens or 0),
                completion_tokens=int(completion_tokens or 0),
                total_tokens=int(total_tokens or 0),
                duration_seconds=float(duration_seconds or 0),
                model=model,
                status="success",
            )
        )

    def add_error(self, *, image_number: int, file_name: str, error_message: str, model: str) -> None:
        """Append one failed request and parse rate-limit details if present."""

        self.calls.append(
            GroqCallUsage(
                timestamp=time.time(),
                image_number=image_number,
                file_name=file_name,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_seconds=0,
                model=model,
                status="error",
                error_message=error_message,
            )
        )
        parsed_error = parse_groq_rate_limit_error(error_message)
        if parsed_error.limit_type:
            self.last_limit_error = parsed_error

    def calls_last_seconds(self, seconds: int) -> list[GroqCallUsage]:
        """Return successful calls made within a rolling time window."""

        cutoff = time.time() - seconds
        return [call for call in self.calls if call.timestamp >= cutoff and call.status == "success"]

    @property
    def total_requests(self) -> int:
        """Count successful requests in this session."""

        return len([call for call in self.calls if call.status == "success"])

    @property
    def failed_requests(self) -> int:
        """Count failed requests in this session."""

        return len([call for call in self.calls if call.status == "error"])

    @property
    def total_tokens(self) -> int:
        """Sum successful request tokens in this session."""

        return sum(call.total_tokens for call in self.calls if call.status == "success")

    @property
    def requests_last_minute(self) -> int:
        """Count successful requests in the last 60 seconds."""

        return len(self.calls_last_seconds(60))

    @property
    def tokens_last_minute(self) -> int:
        """Sum successful request tokens in the last 60 seconds."""

        return sum(call.total_tokens for call in self.calls_last_seconds(60))

    def as_dashboard_usage(self, daily_tokens: int = 0) -> dict[str, int]:
        """Convert tracker state into the dictionary expected by the UI."""

        return {
            "requests_last_minute": self.requests_last_minute,
            "tokens_last_minute": self.tokens_last_minute,
            "session_requests": self.total_requests,
            "tokens_today": int(daily_tokens or 0),
        }

    def as_rows(self) -> list[dict[str, Any]]:
        """Return tabular rows for future debug or export views."""

        return [
            {
                "image_number": call.image_number,
                "file_name": call.file_name,
                "status": call.status,
                "prompt_tokens": call.prompt_tokens,
                "completion_tokens": call.completion_tokens,
                "total_tokens": call.total_tokens,
                "duration_seconds": round(call.duration_seconds, 2),
                "model": call.model,
                "error_message": call.error_message,
            }
            for call in self.calls
        ]


def parse_groq_rate_limit_error(message: str) -> GroqObservedLimitError:
    """Parse common Groq rate-limit fields from an exception message."""

    text = str(message or "")
    observed = GroqObservedLimitError(raw_message=text)

    type_match = re.search(r"\((TPD|TPM|RPM|RPD)\)", text, flags=re.IGNORECASE)
    if type_match:
        observed.limit_type = type_match.group(1).upper()

    limit_match = re.search(
        r"Limit\s+([0-9,]+),\s*Used\s+([0-9,]+),\s*Requested\s+([0-9,]+)",
        text,
        flags=re.IGNORECASE,
    )
    if limit_match:
        observed.limit = int(limit_match.group(1).replace(",", ""))
        observed.used = int(limit_match.group(2).replace(",", ""))
        observed.requested = int(limit_match.group(3).replace(",", ""))

    retry_match = re.search(r"Please try again in\s+([^\.]+(?:\.\d+)?s)", text, flags=re.IGNORECASE)
    if retry_match:
        observed.retry_after_text = retry_match.group(1)

    return observed


def build_friendly_groq_error_message(error_message: str) -> str:
    """Convert raw service errors into short messages for the UI."""

    text = str(error_message or "")
    observed = parse_groq_rate_limit_error(text)

    if observed.limit_type:
        parts = [f"Groq usage limit reached: {observed.limit_type}."]
        if observed.limit is not None:
            parts.append(f"Limit: {observed.limit:,}.")
        if observed.used is not None:
            parts.append(f"Used: {observed.used:,}.")
        if observed.requested is not None:
            parts.append(f"Next image requested: {observed.requested:,}.")
        if observed.retry_after_text:
            parts.append(f"Try again after {observed.retry_after_text}.")
        return " ".join(parts)

    lower_text = text.lower()
    if "api_key" in lower_text or "invalid api" in lower_text:
        return "The API key is missing or invalid. Update the saved key and try again."
    if "connection" in lower_text or "timeout" in lower_text:
        return "The request timed out or lost network connectivity. Try again shortly."

    return "The extraction request could not be completed. Check the API key, network connection, or quota."
