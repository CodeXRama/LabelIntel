"""
LabelIntel — Computer Vision Denoising Module
Provides controlled edge-preserving noise reduction using Bilateral Filtering
or Fast Non-Local Means (FastNLM) to prevent destroying fine typographical strokes.
"""

from typing import Tuple
import cv2
import numpy as np


def apply_denoising(
    image: np.ndarray,
    method: str = "bilateral",
    bilateral_d: int = 5,
    bilateral_sigma_color: float = 50.0,
    bilateral_sigma_space: float = 50.0,
    fast_nl_h: float = 3.0,
) -> Tuple[np.ndarray, bool]:
    """
    Applies edge-preserving noise reduction.

    Practical OCR Considerations:
        - Fine Glyphs: Small statutory declarations (e.g. 1.0mm font, batch codes)
          feature fine strokes and critical punctuation (decimal points in 'Rs. 50.00',
          hyphens in dates). Over-filtering can dissolve these details.
        - Default Recommendation: Bilateral filtering is the preferred default when denoising
          is required, as it selectively smooths flat color regions while strictly preserving
          high-gradient text edges. Fast Non-Local Means is significantly more compute-intensive
          (typically 10-20x slower) and should be reserved for high-ISO grainy captures.

    Args:
        image: Source uint8 numpy array.
        method: Denoising technique: 'bilateral' (fast, edge-preserving) or 'fast_nl_means'.
        bilateral_d: Neighborhood diameter for bilateral filtering (default: 5).
        bilateral_sigma_color: Filter sigma in color space (default: 50.0).
        bilateral_sigma_space: Filter sigma in coordinate space (default: 50.0).
        fast_nl_h: Filter strength parameter for Fast Non-Local Means (default: 3.0).

    Returns:
        Tuple of (denoised_image: np.ndarray, was_applied: bool)
    """
    if image is None or image.size == 0 or image.ndim < 2:
        raise ValueError("Invalid image provided to apply_denoising.")

    clean_method = method.lower().strip()

    if clean_method == "bilateral":
        # Bilateral filter works natively on 1, 3, or 4 channels
        denoised = cv2.bilateralFilter(
            image,
            d=bilateral_d,
            sigmaColor=bilateral_sigma_color,
            sigmaSpace=bilateral_sigma_space,
        )
        return denoised, True

    elif clean_method == "fast_nl_means":
        if image.ndim == 2:
            # Grayscale single-channel
            denoised = cv2.fastNlMeansDenoising(
                image,
                None,
                h=fast_nl_h,
                templateWindowSize=7,
                searchWindowSize=21,
            )
            return denoised, True
        elif image.ndim == 3 and image.shape[2] == 3:
            # BGR 3-channel
            denoised = cv2.fastNlMeansDenoisingColored(
                image,
                None,
                h=fast_nl_h,
                hColor=fast_nl_h,
                templateWindowSize=7,
                searchWindowSize=21,
            )
            return denoised, True
        elif image.ndim == 3 and image.shape[2] == 4:
            # BGRA: denoise BGR channels and retain alpha
            bgr = image[:, :, :3]
            alpha = image[:, :, 3:]
            denoised_bgr = cv2.fastNlMeansDenoisingColored(
                bgr,
                None,
                h=fast_nl_h,
                hColor=fast_nl_h,
                templateWindowSize=7,
                searchWindowSize=21,
            )
            return np.concatenate([denoised_bgr, alpha], axis=2), True
        else:
            return image.copy(), False

    else:
        # Unknown method: return unmodified copy
        return image.copy(), False
