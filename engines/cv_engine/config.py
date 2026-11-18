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
        ("JPEG", "PNG", "WEBP", "AVIF"),
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


class CVPreprocessingConfig(BaseModel):
    """Configuration settings for Stage 3 Image Preprocessing Pipeline."""
    # Resize settings
    resize_enabled: bool = Field(True, description="Enable aspect-preserving resizing")
    max_width: int = Field(1920, description="Maximum width constraint in pixels")
    max_height: int = Field(1920, description="Maximum height constraint in pixels")
    allow_upscaling: bool = Field(False, description="Whether to upscale images smaller than target bounds")

    # CLAHE contrast enhancement settings
    clahe_enabled: bool = Field(True, description="Enable Contrast Limited Adaptive Histogram Equalization")
    clahe_clip_limit: float = Field(2.0, description="CLAHE contrast clipping limit threshold")
    clahe_tile_grid_size: Tuple[int, int] = Field((8, 8), description="Tile grid dimension (rows, cols)")

    # Denoising settings
    denoise_enabled: bool = Field(False, description="Enable edge-preserving denoising filter (disabled by default)")
    denoise_method: str = Field("bilateral", description="Denoising algorithm: 'bilateral' or 'fast_nl_means'")
    bilateral_d: int = Field(5, description="Diameter of each pixel neighborhood for bilateral filtering")
    bilateral_sigma_color: float = Field(50.0, description="Filter sigma in color space for bilateral filtering")
    bilateral_sigma_space: float = Field(50.0, description="Filter sigma in coordinate space for bilateral filtering")
    fast_nl_h: float = Field(3.0, description="Filter strength for Fast Non-Local Means")

    # Conservative deskewing settings
    deskew_enabled: bool = Field(False, description="Enable conservative rotational deskewing (disabled by default)")
    deskew_max_angle: float = Field(15.0, description="Maximum allowable rotation angle in degrees")
    deskew_min_angle: float = Field(0.5, description="Minimum angle threshold in degrees to trigger rotation")
    deskew_min_text_lines: int = Field(3, description="Minimum reliable text lines required to compute median skew")


# Re-export CVOCRConfig for centralized configuration access
from engines.cv_engine.ocr.config import CVOCRConfig
