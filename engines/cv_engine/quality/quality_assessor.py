"""
LabelIntel — Computer Vision Image Quality Assessment Module
Computes sharpness (Laplacian variance), luminance, contrast, and histogram clipping
to identify underexposed, overexposed, blurry, or low-contrast packaging captures.
"""

from typing import List, Optional
import cv2
import numpy as np

from engines.cv_engine.config import CVQualityConfig
from engines.cv_engine.schemas import ImageQualityMetrics


def assess_image_quality(
    image: np.ndarray,
    config: Optional[CVQualityConfig] = None,
) -> ImageQualityMetrics:
    """
    Assess quality of a decoded image array for downstream OCR suitability.

    The assessment does NOT mutate the input array. All measurements are advisory:
    an image with low quality metrics generates non-blocking warnings so downstream
    engines and operators can make informed decisions.

    Args:
        image: BGR or Grayscale uint8 numpy array.
        config: Optional quality configuration thresholds.

    Returns:
        ImageQualityMetrics instance containing numerical scores, booleans, and warnings.

    Raises:
        ValueError: If image is None, empty, or has an invalid dimensionality.
    """
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("Cannot assess quality: input image is None or an empty numpy array.")

    if image.ndim < 2:
        raise ValueError(f"Cannot assess quality: input array has insufficient dimensions ({image.ndim}).")

    cfg = config or CVQualityConfig()
    warnings: List[str] = []

    # 1. Grayscale Conversion (Preserves original image unchanged)
    if image.ndim == 3:
        channels = image.shape[2]
        if channels == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif channels == 4:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        elif channels == 1:
            gray = image[:, :, 0]
        else:
            raise ValueError(f"Unsupported number of image channels: {channels}")
    else:
        gray = image

    total_pixels = gray.size
    if total_pixels == 0:
        raise ValueError("Image matrix has zero total pixels.")

    # 2. Blur Estimation via Modified Laplacian Variance
    # Note: Laplacian variance measures high-frequency edge variance. It is a heuristic:
    # solid-color packaging or minimalistic designs naturally exhibit lower edge counts
    # without necessarily being out-of-focus.
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blur_var = float(laplacian.var())
    is_blurry = blur_var < cfg.blur_laplacian_threshold

    if is_blurry:
        warnings.append(
            f"Low sharpness score (Laplacian variance: {blur_var:.1f} < threshold {cfg.blur_laplacian_threshold:.1f}). "
            "Image may suffer from defocus or motion blur, which can degrade OCR precision."
        )

    # 3. Luminance (Mean Brightness)
    brightness_mean = float(np.mean(gray))
    is_under_exposed = brightness_mean < cfg.brightness_low_threshold
    is_over_exposed = brightness_mean > cfg.brightness_high_threshold

    if is_under_exposed:
        warnings.append(
            f"Underexposed capture (mean luminance: {brightness_mean:.1f} < threshold {cfg.brightness_low_threshold:.1f}). "
            "Low ambient light reduces contrast between text and packaging background."
        )
    elif is_over_exposed:
        warnings.append(
            f"Overexposed capture (mean luminance: {brightness_mean:.1f} > threshold {cfg.brightness_high_threshold:.1f}). "
            "Excessive illumination or specular glare may wash out statutory text."
        )

    # 4. Contrast (Standard Deviation of Luminance)
    contrast_std = float(np.std(gray))
    if contrast_std < cfg.contrast_low_threshold:
        warnings.append(
            f"Low contrast (luminance std: {contrast_std:.1f} < threshold {cfg.contrast_low_threshold:.1f}). "
            "Text markings may blend into the package substrate."
        )

    # 5. Histogram Clipping Analysis
    # Analyzes saturation at the dynamic range extremes:
    # - Shadow clipping: pixels in [low_bin_min, low_bin_max] (near black)
    # - Highlight clipping: pixels in [high_bin_min, high_bin_max] (near white, glare)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()

    low_min, low_max = cfg.clipping_low_bin_range
    high_min, high_max = cfg.clipping_high_bin_range

    clipping_low_count = int(np.sum(hist[low_min : low_max + 1]))
    clipping_high_count = int(np.sum(hist[high_min : high_max + 1]))

    clipping_low_pct = round(float(clipping_low_count) / total_pixels, 4)
    clipping_high_pct = round(float(clipping_high_count) / total_pixels, 4)

    if clipping_low_pct > cfg.clipping_low_threshold_pct:
        warnings.append(
            f"Significant shadow clipping: {clipping_low_pct * 100:.1f}% of pixels are crushed "
            f"near pure black (threshold: {cfg.clipping_low_threshold_pct * 100:.1f}%)."
        )

    if clipping_high_pct > cfg.clipping_high_threshold_pct:
        warnings.append(
            f"Significant highlight clipping: {clipping_high_pct * 100:.1f}% of pixels are saturated "
            f"near pure white (threshold: {cfg.clipping_high_threshold_pct * 100:.1f}%). Possible flash reflection."
        )

    return ImageQualityMetrics(
        blur_laplacian_variance=round(blur_var, 2),
        is_blurry=is_blurry,
        brightness_mean=round(brightness_mean, 2),
        contrast_std=round(contrast_std, 2),
        clipping_low_pct=clipping_low_pct,
        clipping_high_pct=clipping_high_pct,
        is_under_exposed=is_under_exposed,
        is_over_exposed=is_over_exposed,
        quality_warnings=warnings,
    )
