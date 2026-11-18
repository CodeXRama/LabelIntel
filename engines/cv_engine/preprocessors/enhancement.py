"""
LabelIntel — Computer Vision Contrast Enhancement Module (CLAHE)
Applies Contrast Limited Adaptive Histogram Equalization to the luminance (L) channel
in LAB color space to boost local text contrast without corrupting chromatic packaging tones.
"""

from typing import Tuple
import cv2
import numpy as np


def apply_clahe(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: Tuple[int, int] = (8, 8),
) -> Tuple[np.ndarray, bool]:
    """
    Apply Contrast Limited Adaptive Histogram Equalization (CLAHE).

    For color images (3 channels BGR), the image is converted to the CIELAB color space.
    CLAHE is applied exclusively to the Lightness (L*) channel before returning to BGR.
    This improves text-to-substrate contrast under non-uniform illumination while strictly
    preserving chromatic packaging brand colors.

    For grayscale images (1 channel), CLAHE is applied directly.

    Technical Limitations & Caveats:
        1. Noise Amplification: Excessively high clip limits (> 3.0) amplify sensor noise
           in dark underexposed regions, creating spurious speckles.
        2. Substrate Mottling: Text printed on textured substrates (kraft paper, corrugated fiberboard)
           may have background fiber textures accentuated, potentially confusing OCR binarization.
        3. Tile Boundary Artifacts: Extreme illumination gradients across tile boundaries (e.g. 8x8)
           can occasionally produce subtle haloing around high-contrast edges.

    Args:
        image: Input uint8 numpy array (H, W, 3) or (H, W).
        clip_limit: Threshold for contrast limiting (default: 2.0).
        tile_grid_size: Grid size for local histogram equalization (default: (8, 8)).

    Returns:
        Tuple of (enhanced_image: np.ndarray, was_applied: bool)
    """
    if image is None or image.size == 0 or image.ndim < 2:
        raise ValueError("Invalid image provided to apply_clahe.")

    if clip_limit <= 0.0:
        return image.copy(), False

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)

    if image.ndim == 2:
        # Grayscale single-channel image
        enhanced = clahe.apply(image)
        return enhanced, True

    elif image.ndim == 3 and image.shape[2] == 3:
        # BGR 3-channel color image
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        enhanced_l = clahe.apply(l_channel)
        enhanced_lab = cv2.merge([enhanced_l, a_channel, b_channel])
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        return enhanced_bgr, True

    elif image.ndim == 3 and image.shape[2] == 4:
        # BGRA 4-channel image
        b, g, r, a = cv2.split(image)
        bgr = cv2.merge([b, g, r])
        enhanced_bgr, _ = apply_clahe(bgr, clip_limit=clip_limit, tile_grid_size=tile_grid_size)
        eb, eg, er = cv2.split(enhanced_bgr)
        return cv2.merge([eb, eg, er, a]), True

    else:
        # Fallback for unexpected channel counts: return copy
        return image.copy(), False
