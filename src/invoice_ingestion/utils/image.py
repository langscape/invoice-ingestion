"""Image processing utilities for invoice page images."""

from __future__ import annotations

import base64
import io

from PIL import Image


def normalize_image(image_bytes: bytes, target_dpi: int = 300) -> bytes:
    """Normalize an image: convert to RGB and ensure minimum resolution."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(target_dpi, target_dpi))
    return buf.getvalue()


def compute_quality_score(image_bytes: bytes) -> float:
    """Compute an image quality score between 0.0 and 1.0.

    The score is a weighted combination of:
    - **Resolution score** (60%): ratio of pixel count to A4 at 300 DPI (2550x3300).
    - **Contrast score** (40%): variance of grayscale pixel intensities, normalised.
    """
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size

    # Resolution component
    resolution_score = min(1.0, (width * height) / (2550 * 3300))

    # Contrast component
    gray = img.convert("L")
    pixels = list(gray.getdata())
    mean = sum(pixels) / len(pixels)
    variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
    contrast_score = min(1.0, variance / 3000)

    return round(0.6 * resolution_score + 0.4 * contrast_score, 3)


def image_to_base64(image_bytes: bytes) -> str:
    """Encode raw image bytes to a Base64 string."""
    return base64.b64encode(image_bytes).decode("utf-8")


def image_to_bytes(base64_str: str) -> bytes:
    """Decode a Base64 string back to raw image bytes."""
    return base64.b64decode(base64_str)


def get_image_dimensions(image_bytes: bytes) -> tuple[int, int]:
    """Return the ``(width, height)`` of an image."""
    img = Image.open(io.BytesIO(image_bytes))
    return img.size
