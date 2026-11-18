"""
LabelIntel — Computer Vision Engine Configuration
Centralized configuration models for validation, image quality assessment,
and pipeline runtime thresholds.
"""

from typing import Tuple
from pydantic import BaseModel, Field


class CVValidationConfig(BaseModel):
    """Configuration thresholds and constraints for image validation."""
    min_dimension: int = Field(
        100,
        description="Minimum allowed width or height in pixels (reject low-res inputs below this)"
    )
    max_dimension: int = Field(
        4096,
        description="Maximum dimension before requiring aspect-preserving downscaling"
    )
    min_aspect_ratio: float = Field(
        0.1,
        description="Minimum aspect ratio (width / height) permitted (reject extreme 1:10 slivers)"
    )
    max_aspect_ratio: float = Field(
        10.0,
        description="Maximum aspect ratio (width / height) permitted (reject extreme 10:1 ribbons)"
    )
    allowed_formats: Tuple[str, ...] = Field(
        ("JPEG", "PNG"),
        description="Tuple of permitted image format identifiers"
    )
    max_file_size_bytes: int = Field(
        25 * 1024 * 1024,
        description="Maximum permitted file size in bytes (default: 25MB)"
    )


class CVQualityConfig(BaseModel):
    """Configuration thresholds for image quality and degradation assessment."""
    blur_laplacian_threshold: float = Field(
        100.0,
        description="Laplacian variance threshold below which an image is flagged as blurry"
    )
    brightness_low_threshold: float = Field(
        40.0,
        description="Mean luminance threshold below which an image is flagged as underexposed (0-255)"
    )
    brightness_high_threshold: float = Field(
        220.0,
        description="Mean luminance threshold above which an image is flagged as overexposed (0-255)"
    )
    contrast_low_threshold: float = Field(
        25.0,
        description="Standard deviation threshold below which an image is flagged as low-contrast (0-255)"
    )
    clipping_low_bin_range: Tuple[int, int] = Field(
        (0, 5),
        description="Grayscale pixel intensity range classified as shadow clipping [min, max]"
    )
    clipping_high_bin_range: Tuple[int, int] = Field(
        (250, 255),
        description="Grayscale pixel intensity range classified as highlight clipping [min, max]"
    )
    clipping_low_threshold_pct: float = Field(
        0.05,
        description="Fraction of pixels in low range (5%) that triggers an underexposure clipping warning"
    )
    clipping_high_threshold_pct: float = Field(
        0.05,
        description="Fraction of pixels in high range (5%) that triggers an overexposure/glare clipping warning"
    )
