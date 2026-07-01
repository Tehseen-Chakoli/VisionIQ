"""Image resizing and JPEG compression for VisionIQ.

The model service works best with clear images, but very large uploads can make
requests slower and more expensive. This module keeps the compression policy in
one place so the extraction runner can prepare every image consistently.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from src.config import IMAGE_JPEG_QUALITY, IMAGE_TARGET_WIDTH


@dataclass(frozen=True)
class CompressionConfig:
    """Settings that control how images are resized before model submission."""

    target_width: int = IMAGE_TARGET_WIDTH
    jpeg_quality: int = IMAGE_JPEG_QUALITY
    allow_upscale: bool = False


@dataclass(frozen=True)
class CompressionResult:
    """Metadata produced after writing a compressed image."""

    output_path: str
    original_size: tuple[int, int]
    final_size: tuple[int, int]
    quality: int


def normalize_image(image: Image.Image) -> Image.Image:
    """Return an RGB image with camera orientation applied.

    Phone screenshots and camera photos often store orientation in EXIF instead
    of rotating pixels directly. ``exif_transpose`` makes the pixel data match
    what the user sees before any crop or resize is performed.
    """

    oriented_image = ImageOps.exif_transpose(image)
    if oriented_image.mode != "RGB":
        return oriented_image.convert("RGB")
    return oriented_image


def resize_for_model(image: Image.Image, config: CompressionConfig | None = None) -> Image.Image:
    """Resize an image to the configured width while preserving aspect ratio."""

    active_config = config or CompressionConfig()
    normalized_image = normalize_image(image)
    width, height = normalized_image.size

    if width <= 0 or height <= 0:
        raise ValueError("Image has invalid dimensions.")

    should_resize = width > active_config.target_width or active_config.allow_upscale
    if not should_resize:
        return normalized_image.copy()

    ratio = active_config.target_width / width
    target_height = max(1, int(height * ratio))
    return normalized_image.resize((active_config.target_width, target_height), Image.Resampling.LANCZOS)


def save_compressed_jpeg(
    image: Image.Image,
    output_path: str | Path,
    config: CompressionConfig | None = None,
) -> CompressionResult:
    """Write a prepared image as optimized JPEG and return processing metadata."""

    active_config = config or CompressionConfig()
    original_size = image.size
    resized_image = resize_for_model(image, active_config)
    final_path = str(output_path)

    resized_image.save(
        final_path,
        format="JPEG",
        quality=active_config.jpeg_quality,
        optimize=True,
        progressive=True,
    )

    return CompressionResult(
        output_path=final_path,
        original_size=original_size,
        final_size=resized_image.size,
        quality=active_config.jpeg_quality,
    )
