"""Screen and document crop detection for uploaded images.

The cropper is intentionally conservative. It removes obvious outer background
when a large document/screen area can be detected, and otherwise returns the
original image unchanged so extraction quality is not harmed by an aggressive
crop.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from src.image_compressor import normalize_image


@dataclass(frozen=True)
class CropConfig:
    """Thresholds used by the conservative crop detector."""

    min_area_ratio: float = 0.35
    padding_pixels: int = 12
    max_background_ratio: float = 0.96


@dataclass(frozen=True)
class CropResult:
    """Image and metadata returned after attempting a crop."""

    image: Image.Image
    was_cropped: bool
    crop_box: tuple[int, int, int, int]


def crop_document_area(image: Image.Image, config: CropConfig | None = None) -> CropResult:
    """Detect and crop the main bright document region from an image.

    The detector converts the image to grayscale, finds the strongest external
    contour, and accepts the crop only when it covers enough of the source image
    without being nearly identical to the full frame.
    """

    active_config = config or CropConfig()
    normalized_image = normalize_image(image)
    width, height = normalized_image.size
    full_box = (0, 0, width, height)

    if width <= 0 or height <= 0:
        raise ValueError("Image has invalid dimensions.")

    image_array = np.array(normalized_image)
    gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Otsu thresholding adapts to both screenshots and photographed pages.
    _, threshold = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return CropResult(image=normalized_image, was_cropped=False, crop_box=full_box)

    largest_contour = max(contours, key=cv2.contourArea)
    x, y, crop_width, crop_height = cv2.boundingRect(largest_contour)
    crop_area = crop_width * crop_height
    full_area = width * height
    area_ratio = crop_area / full_area

    if area_ratio < active_config.min_area_ratio or area_ratio > active_config.max_background_ratio:
        return CropResult(image=normalized_image, was_cropped=False, crop_box=full_box)

    padding = active_config.padding_pixels
    left = max(0, x - padding)
    top = max(0, y - padding)
    right = min(width, x + crop_width + padding)
    bottom = min(height, y + crop_height + padding)

    if right <= left or bottom <= top:
        return CropResult(image=normalized_image, was_cropped=False, crop_box=full_box)

    return CropResult(
        image=normalized_image.crop((left, top, right, bottom)),
        was_cropped=True,
        crop_box=(left, top, right, bottom),
    )
