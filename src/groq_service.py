"""Groq model service for VisionIQ document extraction.

This module is responsible for converting image files into model requests and
returning a structured result object. It does not know about Streamlit, files
uploaded by users, or database persistence.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass

from groq import Groq

from src.config import MODEL_NAME


@dataclass
class GroqExtractionResult:
    """Normalized result returned by one Groq Vision extraction request."""

    output: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    duration_seconds: float


def encode_image_to_base64(image_path: str) -> str:
    """Read an image file and return a base64 string for a data URL."""

    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def build_extraction_prompt(image_number: int) -> str:
    """Build the prompt used for strict multiple-choice transcription."""

    return f"""
You are VisionIQ's document extraction assistant.

This is image number {image_number}.

Task:
Extract every visible multiple-choice question from the image exactly as shown.

Rules:
1. Extract only text that is physically visible in the image.
2. Do not solve, infer, summarize, or complete missing text.
3. If text is unreadable, write exactly: [UNCLEAR]
4. Preserve question numbers, wording, option labels, and option order.
5. Include all visible options, including E or later options when present.
6. If the answer is visibly printed, include it. Otherwise write: Answer: Not available
7. Do not add explanations or commentary.

Output format:

Question <number>: <question text>

Options:
A. <option text>
B. <option text>
C. <option text>
D. <option text>
E. <option text> (only if visible)

Answer: <visible answer or Not available>
"""


def extract_questions_with_groq(
    *,
    image_path: str,
    image_number: int,
    groq_api_key: str,
    max_completion_tokens: int = 2048,
) -> GroqExtractionResult:
    """Send one prepared image to Groq and return normalized extraction output."""

    if not groq_api_key:
        raise ValueError("Groq API key is missing.")

    client = Groq(api_key=groq_api_key)
    image_b64 = encode_image_to_base64(image_path)
    prompt = build_extraction_prompt(image_number)

    start_time = time.time()
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            }
        ],
        temperature=0,
        max_completion_tokens=max_completion_tokens,
        top_p=1,
        stream=False,
    )
    duration_seconds = time.time() - start_time
    usage = getattr(completion, "usage", None)

    return GroqExtractionResult(
        output=completion.choices[0].message.content or "",
        prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
        completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        total_tokens=int(getattr(usage, "total_tokens", 0) or 0),
        model=MODEL_NAME,
        duration_seconds=duration_seconds,
    )
