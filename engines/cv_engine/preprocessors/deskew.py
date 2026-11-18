"""
LabelIntel — Computer Vision Conservative Deskewing Module
Estimates dominant text orientation and corrects planar skew while preserving
all image boundaries, with full 3x3 homogeneous transformation matrix tracking.
"""

from typing import List, Optional, Tuple
import cv2
import numpy as np


def estimate_dominant_skew_angle(
    image: np.ndarray,
    min_text_lines: int = 3,
    max_angle_degrees: float = 15.0,
    min_aspect_ratio: float = 2.5,
) -> Tuple[Optional[float], str]:
    """
    Conservatively estimate dominant text orientation angle using horizontal line morphology.

    Returns:
        Tuple of (estimated_angle_degrees or None, status_description)
    """
    if image is None or image.size == 0 or image.ndim < 2:
        return None, "invalid_image"

    # 1. Grayscale Conversion
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 2. Otsu Binarization (inverted so text foreground is white)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 3. Horizontal Line Dilation
    # Uses a wide rectangular structuring element to merge adjacent characters in a line
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    # 4. Contour Extraction
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    angles: List[float] = []
    min_width = max(40, int(image.shape[1] * 0.05))

    for cnt in contours:
        if cv2.contourArea(cnt) < 150:
            continue

        rect = cv2.minAreaRect(cnt)
        (cx, cy), (w, h), raw_angle = rect

        # Normalize width and height orientation
        if w < h:
            w, h = h, w
            rect_angle = raw_angle + 90.0
        else:
            rect_angle = raw_angle

        # Normalize to [-45, 45] degrees relative to horizontal
        if rect_angle > 45.0:
            rect_angle -= 90.0
        elif rect_angle < -45.0:
            rect_angle += 90.0

        # Filter strictly for horizontal text-like aspect ratios
        aspect_ratio = w / float(max(h, 1))
        if w >= min_width and aspect_ratio >= min_aspect_ratio:
            if abs(rect_angle) <= max_angle_degrees:
                angles.append(rect_angle)

    # 5. Reliability Evaluation
    if len(angles) < min_text_lines:
        return None, f"insufficient_text_lines ({len(angles)} found, minimum {min_text_lines} required)"

    std_dev = float(np.std(angles))
    if std_dev > 4.0:
        return None, f"high_angular_variance (std={std_dev:.2f} deg, angles inconsistent across lines)"

    median_angle = float(np.median(angles))
    return median_angle, "reliable_estimation"


def rotate_image_with_matrix(
    image: np.ndarray,
    angle_degrees: float,
    expand_bounds: bool = True,
    border_mode: int = cv2.BORDER_REPLICATE,
    border_value: Tuple[int, int, int] = (255, 255, 255),
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Rotates an image by angle_degrees and returns the transformed image along with
    the exact 3x3 homogeneous affine matrix mapping original coords to rotated coords.

    Args:
        image: Source image numpy array.
        angle_degrees: Rotation angle (positive = counter-clockwise in Cartesian,
                       clockwise in standard OpenCV image coordinates).
        expand_bounds: If True, expands destination canvas to prevent clipping corners.
        border_mode: cv2.BORDER_REPLICATE, cv2.BORDER_CONSTANT, etc.
        border_value: Color fill when border_mode is BORDER_CONSTANT.

    Returns:
        Tuple of (rotated_image: np.ndarray, forward_matrix_3x3: np.ndarray)
    """
    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0

    # OpenCV 2x3 rotation matrix (angle in degrees, counterclockwise is positive)
    M = cv2.getRotationMatrix2D((cx, cy), angle_degrees, 1.0)

    if expand_bounds:
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])

        new_w = int(np.ceil((h * sin) + (w * cos)))
        new_h = int(np.ceil((h * cos) + (w * sin)))

        # Shift center to new bounding box center
        M[0, 2] += (new_w / 2.0) - cx
        M[1, 2] += (new_h / 2.0) - cy
    else:
        new_w, new_h = w, h

    # Execute geometric affine warp
    rotated = cv2.warpAffine(
        image,
        M,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=border_mode,
        borderValue=border_value,
    )

    # Convert 2x3 affine matrix to 3x3 homogeneous matrix
    M_3x3 = np.array([
        [M[0, 0], M[0, 1], M[0, 2]],
        [M[1, 0], M[1, 1], M[1, 2]],
        [0.0,      0.0,      1.0    ]
    ], dtype=np.float64)

    return rotated, M_3x3


def apply_deskew(
    image: np.ndarray,
    max_angle_degrees: float = 15.0,
    min_angle_threshold: float = 0.5,
    min_text_lines: int = 3,
    force_angle: Optional[float] = None,
) -> Tuple[np.ndarray, float, np.ndarray, str, bool]:
    """
    Conservatively deskew an image.

    Guarantees:
        1. If skew estimation is uncertain, returns original image untouched.
        2. If angle is below min_angle_threshold, returns original image untouched.
        3. If angle exceeds max_angle_degrees, returns original image untouched.
        4. When rotated, returns full 3x3 homogeneous transformation matrix.

    Returns:
        Tuple of (deskewed_image, applied_angle_degrees, forward_matrix_3x3, status_message, was_rotated)
    """
    if image is None or image.size == 0 or image.ndim < 2:
        raise ValueError("Invalid image provided to apply_deskew.")

    identity_3x3 = np.eye(3, dtype=np.float64)

    # 1. Determine Angle
    if force_angle is not None:
        target_angle = float(force_angle)
        status = "forced_angle"
    else:
        estimated, reason = estimate_dominant_skew_angle(
            image,
            min_text_lines=min_text_lines,
            max_angle_degrees=max_angle_degrees,
        )
        if estimated is None:
            return image.copy(), 0.0, identity_3x3, f"skipped: {reason}", False
        target_angle = estimated
        status = f"auto_estimated ({reason})"

    # 2. Angle Threshold Guards
    abs_angle = abs(target_angle)
    if abs_angle < min_angle_threshold:
        return image.copy(), 0.0, identity_3x3, f"skipped: angle {target_angle:.2f} deg below min threshold {min_angle_threshold:.2f} deg", False

    if abs_angle > max_angle_degrees:
        return image.copy(), 0.0, identity_3x3, f"skipped: angle {target_angle:.2f} deg exceeds max allowable {max_angle_degrees:.2f} deg", False

    # 3. Rotate Image
    # In OpenCV, rotating counterclockwise by angle requires warpAffine with positive angle
    rotated_img, matrix_3x3 = rotate_image_with_matrix(image, target_angle, expand_bounds=True)

    return rotated_img, target_angle, matrix_3x3, f"applied_deskew: {target_angle:.2f} deg ({status})", True
