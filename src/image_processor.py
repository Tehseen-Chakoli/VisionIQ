"""End-to-end image preparation for VisionIQ extraction.

This module combines crop detection and compression into one public function.
The extraction runner can stay focused on orchestration while this layer owns
the image-specific choices.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from src.image_compressor import CompressionConfig, CompressionResult, save_compressed_jpeg
from src.screen_cropper import CropConfig, CropResult, crop_document_area


@dataclass(frozen=True)
class ImagePrepConfig:
    """Settings passed through to crop and compression steps."""

    crop: CropConfig = CropConfig()
    compression: CompressionConfig = CompressionConfig()


@dataclass(frozen=True)
class ImagePrepResult:
    """Prepared image path plus metadata useful for audit and debugging."""

    output_path: str
    original_path: str
    was_cropped: bool
    crop_box: tuple[int, int, int, int]
    original_size: tuple[int, int]
    final_size: tuple[int, int]
    jpeg_quality: int


def prepare_image_for_extraction(
    input_path: str | Path,
    config: ImagePrepConfig | None = None,
) -> ImagePrepResult:
    """Crop and compress one uploaded image for model extraction."""

    active_config = config or ImagePrepConfig()
    source_path = str(input_path)

    with Image.open(source_path) as source_image:
        crop_result: CropResult = crop_document_area(source_image, active_config.crop)

        # A dedicated temp file keeps prepared images isolated from original
        # uploads and makes cleanup straightforward for the runner.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            prepared_path = temp_file.name

        compression_result: CompressionResult = save_compressed_jpeg(
            crop_result.image,
            prepared_path,
            active_config.compression,
        )

    return ImagePrepResult(
        output_path=compression_result.output_path,
        original_path=source_path,
        was_cropped=crop_result.was_cropped,
        crop_box=crop_result.crop_box,
        original_size=compression_result.original_size,
        final_size=compression_result.final_size,
        jpeg_quality=compression_result.quality,
    )
