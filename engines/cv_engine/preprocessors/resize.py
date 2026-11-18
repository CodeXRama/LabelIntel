"""
LabelIntel — Computer Vision Aspect-Preserving Resize Module
Provides geometric rescaling constrained strictly by aspect ratio preservation,
with explicit tracking of scale factors and 3x3 homogeneous affine matrices.
"""

from typing import Tuple
import cv2
import numpy as np


def aspect_preserving_resize(
    image: np.ndarray,
    max_width: int = 1920,
    max_height: int = 1920,
    allow_upscaling: bool = False,
) -> Tuple[np.ndarray, Tuple[int, int], Tuple[int, int], float, float, np.ndarray, bool]:
    """
    Resizes an image while strictly maintaining its original aspect ratio.

    Never distorts or stretches the image to force rectangular target dimensions.

    Args:
        image: Source image numpy array (H, W, C) or (H, W).
        max_width: Maximum allowable horizontal pixel dimension.
        max_height: Maximum allowable vertical pixel dimension.
        allow_upscaling: If True, small images will be enlarged to fit within bounds;
                         if False, images smaller than max bounds are left untouched.

    Returns:
        Tuple of:
            - processed_image: Resized (or untouched) numpy array.
            - original_size: (width, height) of the input.
            - processed_size: (width, height) of the output.
            - scale_factor_x: Horizontal scale factor (processed_width / original_width).
            - scale_factor_y: Vertical scale factor (processed_height / original_height).
            - transform_matrix: 3x3 homogeneous matrix mapping original to processed coords.
            - was_resized: Boolean indicating if a resize operation was executed.
    """
    if image is None or image.size == 0 or image.ndim < 2:
        raise ValueError("Invalid image provided to aspect_preserving_resize.")

    orig_height, orig_width = image.shape[:2]
    original_size = (orig_width, orig_height)

    # Check if image already fits within the envelope
    fits_within_envelope = (orig_width <= max_width) and (orig_height <= max_height)
    if fits_within_envelope and not allow_upscaling:
        identity_3x3 = np.eye(3, dtype=np.float64)
        return image.copy(), original_size, original_size, 1.0, 1.0, identity_3x3, False

    # Calculate aspect-preserving scale factor
    scale_w = max_width / float(orig_width)
    scale_h = max_height / float(orig_height)
    scale = min(scale_w, scale_h)

    # Compute target integer dimensions
    target_width = max(1, int(round(orig_width * scale)))
    target_height = max(1, int(round(orig_height * scale)))
    processed_size = (target_width, target_height)

    # If rounded dimensions equal original, no transformation needed
    if processed_size == original_size:
        identity_3x3 = np.eye(3, dtype=np.float64)
        return image.copy(), original_size, original_size, 1.0, 1.0, identity_3x3, False

    # Select appropriate interpolation:
    # cv2.INTER_AREA is optimal for moire-free downsampling;
    # cv2.INTER_CUBIC preserves edge sharpness during upsampling.
    if scale < 1.0:
        interpolation = cv2.INTER_AREA
    else:
        interpolation = cv2.INTER_CUBIC

    resized_image = cv2.resize(image, (target_width, target_height), interpolation=interpolation)

    # Compute exact actual scale factors
    actual_sx = target_width / float(orig_width)
    actual_sy = target_height / float(orig_height)

    # Construct 3x3 homogeneous scaling matrix
    # [ [sx,  0, 0],
    #   [ 0, sy, 0],
    #   [ 0,  0, 1] ]
    transform_matrix = np.array([
        [actual_sx, 0.0, 0.0],
        [0.0, actual_sy, 0.0],
        [0.0, 0.0, 1.0]
    ], dtype=np.float64)

    return resized_image, original_size, processed_size, actual_sx, actual_sy, transform_matrix, True
