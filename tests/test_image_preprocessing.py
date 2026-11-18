"""
LabelIntel — Stage 3 Preprocessing Test Suite
Verifies aspect-preserving resizing, CLAHE enhancement, denoising, conservative deskewing,
and forward/inverse homogeneous coordinate transformation mapping contracts.
"""

import cv2
import numpy as np
import pytest

from engines.cv_engine.config import CVPreprocessingConfig
from engines.cv_engine.preprocessors.denoising import apply_denoising
from engines.cv_engine.preprocessors.deskew import (
    apply_deskew,
    estimate_dominant_skew_angle,
    rotate_image_with_matrix,
)
from engines.cv_engine.preprocessors.enhancement import apply_clahe
from engines.cv_engine.preprocessors.pipeline import preprocess_image
from engines.cv_engine.preprocessors.resize import aspect_preserving_resize
from engines.cv_engine.schemas import Point2D, PreprocessingInfo


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def synthetic_label_image() -> np.ndarray:
    """Creates an 800x500 synthetic packaged label with sharp text and borders."""
    img = np.ones((500, 800, 3), dtype=np.uint8) * 220
    cv2.putText(img, "ORGANIC WHEAT FLOUR", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
    cv2.putText(img, "NET QUANTITY: 1 kg", (50, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2)
    cv2.putText(img, "MRP Rs. 85.00 (INCL. TAXES)", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2)
    cv2.putText(img, "MFG DATE: 10/2026", (50, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.rectangle(img, (30, 30), (770, 470), (10, 10, 10), 3)
    return img


# =====================================================================
# 1. Aspect-Preserving Resize Tests
# =====================================================================

def test_resize_within_target_dimensions(synthetic_label_image: np.ndarray):
    """Images already within bounds should not be resized or re-interpolated."""
    resized, orig_sz, proc_sz, sx, sy, matrix, was_resized = aspect_preserving_resize(
        synthetic_label_image,
        max_width=1920,
        max_height=1920,
        allow_upscaling=False,
    )
    assert was_resized is False
    assert orig_sz == (800, 500)
    assert proc_sz == (800, 500)
    assert sx == 1.0
    assert sy == 1.0
    assert np.allclose(matrix, np.eye(3))
    assert resized.shape == synthetic_label_image.shape


def test_resize_large_landscape_downscaling():
    """3000x1500 landscape image (2:1 aspect ratio) resized to max 1920x1920."""
    large_img = np.zeros((1500, 3000, 3), dtype=np.uint8)
    resized, orig_sz, proc_sz, sx, sy, matrix, was_resized = aspect_preserving_resize(
        large_img,
        max_width=1920,
        max_height=1920,
    )
    assert was_resized is True
    assert orig_sz == (3000, 1500)
    assert proc_sz == (1920, 960)
    # Ratio strictly preserved: 1920 / 960 == 2.0 == 3000 / 1500
    assert abs((proc_sz[0] / proc_sz[1]) - (orig_sz[0] / orig_sz[1])) < 1e-4
    assert sx == 1920 / 3000.0
    assert sy == 960 / 1500.0
    assert resized.shape == (960, 1920, 3)


def test_resize_large_portrait_downscaling():
    """1500x3000 portrait image (1:2 aspect ratio) resized to max 1920x1920."""
    portrait_img = np.zeros((3000, 1500, 3), dtype=np.uint8)
    resized, orig_sz, proc_sz, sx, sy, matrix, was_resized = aspect_preserving_resize(
        portrait_img,
        max_width=1920,
        max_height=1920,
    )
    assert was_resized is True
    assert orig_sz == (1500, 3000)
    assert proc_sz == (960, 1920)
    assert abs((proc_sz[0] / proc_sz[1]) - (orig_sz[0] / orig_sz[1])) < 1e-4
    assert resized.shape == (1920, 960, 3)


def test_resize_aspect_ratio_preservation_arbitrary():
    """Verify aspect ratio is never distorted on non-standard ratios (e.g. 16:9)."""
    img_16_9 = np.zeros((1350, 2400, 3), dtype=np.uint8)
    resized, orig_sz, proc_sz, _, _, _, was_resized = aspect_preserving_resize(
        img_16_9,
        max_width=1200,
        max_height=1200,
    )
    assert was_resized is True
    assert proc_sz == (1200, 675)
    assert round(proc_sz[0] / proc_sz[1], 4) == round(2400 / 1350, 4)


def test_resize_upscaling_disabled_by_default(synthetic_label_image: np.ndarray):
    """Small image with large max bounds is NOT upscaled unless explicitly requested."""
    resized, orig_sz, proc_sz, sx, sy, _, was_resized = aspect_preserving_resize(
        synthetic_label_image,  # 800x500
        max_width=2400,
        max_height=2400,
        allow_upscaling=False,
    )
    assert was_resized is False
    assert proc_sz == (800, 500)


def test_resize_upscaling_when_enabled(synthetic_label_image: np.ndarray):
    """Small image with allow_upscaling=True scales proportionally to fill envelope."""
    resized, orig_sz, proc_sz, sx, sy, matrix, was_resized = aspect_preserving_resize(
        synthetic_label_image,  # 800x500
        max_width=1600,
        max_height=1600,
        allow_upscaling=True,
    )
    assert was_resized is True
    assert proc_sz == (1600, 1000)
    assert sx == 2.0
    assert sy == 2.0
    assert resized.shape == (1000, 1600, 3)


# =====================================================================
# 2. CLAHE Contrast Enhancement Tests
# =====================================================================

def test_clahe_execution_color_image(synthetic_label_image: np.ndarray):
    """CLAHE modifies luminance in LAB space while preserving shape and dimensions."""
    enhanced, was_applied = apply_clahe(synthetic_label_image, clip_limit=2.0, tile_grid_size=(8, 8))
    assert was_applied is True
    assert enhanced.shape == synthetic_label_image.shape
    assert enhanced.dtype == np.uint8
    # Content has been locally equalized: pixel values differ from raw
    assert not np.array_equal(enhanced, synthetic_label_image)


def test_clahe_execution_grayscale_image():
    """CLAHE executes directly on 2D single-channel images."""
    gray = np.full((200, 200), 100, dtype=np.uint8)
    gray[50:150, 50:150] = 160
    enhanced, was_applied = apply_clahe(gray, clip_limit=3.0)
    assert was_applied is True
    assert enhanced.shape == (200, 200)


def test_clahe_disabled_returns_copy(synthetic_label_image: np.ndarray):
    """When clip_limit <= 0, CLAHE is safely bypassed."""
    unmodified, was_applied = apply_clahe(synthetic_label_image, clip_limit=0.0)
    assert was_applied is False
    assert np.array_equal(unmodified, synthetic_label_image)


# =====================================================================
# 3. Denoising Tests
# =====================================================================

def test_denoising_bilateral(synthetic_label_image: np.ndarray):
    """Bilateral filter smooths textures while preserving high-contrast text strokes."""
    denoised, was_applied = apply_denoising(
        synthetic_label_image,
        method="bilateral",
        bilateral_d=5,
        bilateral_sigma_color=40.0,
        bilateral_sigma_space=40.0,
    )
    assert was_applied is True
    assert denoised.shape == synthetic_label_image.shape


def test_denoising_fast_nl_means(synthetic_label_image: np.ndarray):
    """Fast Non-Local Means filter operates correctly on color images."""
    denoised, was_applied = apply_denoising(
        synthetic_label_image,
        method="fast_nl_means",
        fast_nl_h=3.0,
    )
    assert was_applied is True
    assert denoised.shape == synthetic_label_image.shape


# =====================================================================
# 4. Deskewing Tests
# =====================================================================

def test_rotate_image_with_matrix_expansion():
    """Verify rotation expands bounds and returns valid 3x3 homogeneous affine matrix."""
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    rotated, M_3x3 = rotate_image_with_matrix(img, angle_degrees=10.0, expand_bounds=True)

    assert M_3x3.shape == (3, 3)
    assert np.isclose(M_3x3[2, 2], 1.0)
    assert np.isclose(M_3x3[2, 0], 0.0)
    assert np.isclose(M_3x3[2, 1], 0.0)
    # Canvas expanded to hold rotated rectangle without corner clipping
    assert rotated.shape[1] > 600
    assert rotated.shape[0] > 400


def test_deskew_forced_rotation(synthetic_label_image: np.ndarray):
    """Test deskew execution when angle is explicitly provided or detected."""
    deskewed, applied_angle, M_rot, status, was_rotated = apply_deskew(
        synthetic_label_image,
        force_angle=3.5,
        max_angle_degrees=15.0,
        min_angle_threshold=0.5,
    )
    assert was_rotated is True
    assert applied_angle == 3.5
    assert "applied_deskew" in status
    assert M_rot.shape == (3, 3)


def test_deskew_noop_on_sub_threshold_angle(synthetic_label_image: np.ndarray):
    """Rotation angles below min_angle_threshold (e.g. 0.3 deg) should be ignored."""
    deskewed, applied_angle, M_rot, status, was_rotated = apply_deskew(
        synthetic_label_image,
        force_angle=0.2,
        min_angle_threshold=0.5,
    )
    assert was_rotated is False
    assert applied_angle == 0.0
    assert "below min threshold" in status
    assert np.allclose(M_rot, np.eye(3))


def test_deskew_noop_on_excessive_angle(synthetic_label_image: np.ndarray):
    """Angles exceeding max_angle_degrees (e.g. 25 deg) should be skipped to prevent wild rotations."""
    deskewed, applied_angle, M_rot, status, was_rotated = apply_deskew(
        synthetic_label_image,
        force_angle=25.0,
        max_angle_degrees=15.0,
    )
    assert was_rotated is False
    assert applied_angle == 0.0
    assert "exceeds max allowable" in status


def test_deskew_noop_unreliable_estimation():
    """Blank or uniform texture yields no text lines and safely skips rotation."""
    blank_img = np.full((300, 300, 3), 255, dtype=np.uint8)
    angle, reason = estimate_dominant_skew_angle(blank_img, min_text_lines=3)
    assert angle is None
    assert "insufficient_text_lines" in reason


# =====================================================================
# 5. Coordinate Mapping & Transformation Matrix Invariants
# =====================================================================

def test_transformation_matrix_correctness_and_inversion(synthetic_label_image: np.ndarray):
    """
    Verify forward and inverse homogeneous transformation matrices:
    M_inverse @ M_forward must equal Identity (3x3) within floating-point tolerance.
    """
    cfg = CVPreprocessingConfig(
        resize_enabled=True,
        max_width=400,   # Forces downscaling: 800x500 -> 400x250 (scale = 0.5)
        max_height=400,
        deskew_enabled=False,
    )
    _, info, _, _ = preprocess_image(synthetic_label_image, config=cfg)

    M_fwd = np.array(info.forward_matrix, dtype=np.float64)
    M_inv = np.array(info.inverse_matrix, dtype=np.float64)

    product = M_inv @ M_fwd
    identity = np.eye(3, dtype=np.float64)

    assert np.allclose(product, identity, atol=1e-5), f"Matrix inversion failed: product={product}"


def test_coordinate_roundtrip_mapping_points(synthetic_label_image: np.ndarray):
    """
    Verify mapping point from original -> processed -> original returns exact initial coordinates.
    """
    cfg = CVPreprocessingConfig(
        resize_enabled=True,
        max_width=500,
        max_height=500,
        clahe_enabled=True,
    )
    # Test with forced rotation + resize composite
    _, info, _, _ = preprocess_image(synthetic_label_image, config=cfg, force_deskew_angle=5.0)

    test_points = [
        (50.0, 80.0),    # Text origin 1
        (200.0, 160.0),  # Text origin 2
        (400.0, 250.0),  # Image center
        (750.0, 450.0),  # Bottom-right region
    ]

    for orig_x, orig_y in test_points:
        proc_x, proc_y = info.map_to_processed(orig_x, orig_y)
        restored_x, restored_y = info.map_to_original(proc_x, proc_y)

        assert abs(restored_x - orig_x) < 0.05, f"X mismatch: {restored_x} vs {orig_x}"
        assert abs(restored_y - orig_y) < 0.05, f"Y mismatch: {restored_y} vs {orig_y}"


def test_polygon_coordinate_mapping(synthetic_label_image: np.ndarray):
    """
    OCR modules extract 4-point bounding polygons in processed space.
    Verify they can be transformed back to original space and restored seamlessly.
    """
    cfg = CVPreprocessingConfig(
        resize_enabled=True,
        max_width=600,
        max_height=600,
    )
    _, info, _, _ = preprocess_image(synthetic_label_image, config=cfg, force_deskew_angle=4.0)

    # Simulated bounding polygon in original space
    orig_polygon = [
        Point2D(x=50.0, y=100.0),
        Point2D(x=350.0, y=100.0),
        Point2D(x=350.0, y=140.0),
        Point2D(x=50.0, y=140.0),
    ]

    # Map to processed coordinates (simulates what OCR engine sees)
    proc_polygon = info.transform_polygon_to_processed(orig_polygon)
    assert len(proc_polygon) == 4

    # Map back to raw original space (simulates coordinate preservation contract)
    restored_polygon = info.transform_polygon_to_original(proc_polygon)
    assert len(restored_polygon) == 4

    for orig_pt, rest_pt in zip(orig_polygon, restored_polygon):
        assert abs(rest_pt.x - orig_pt.x) < 0.05
        assert abs(rest_pt.y - orig_pt.y) < 0.05


# =====================================================================
# 6. Safety & Immutability Tests
# =====================================================================

def test_original_image_remains_unmodified(synthetic_label_image: np.ndarray):
    """Guarantee that the input image array is never modified in-place."""
    original_copy = synthetic_label_image.copy()
    cfg = CVPreprocessingConfig(
        resize_enabled=True,
        max_width=400,
        clahe_enabled=True,
        denoise_enabled=True,
        deskew_enabled=False,
    )
    processed, _, _, _ = preprocess_image(synthetic_label_image, config=cfg)

    # Processed image differs
    assert not np.array_equal(processed, synthetic_label_image)
    # Source image remains bit-for-bit identical to copy
    assert np.array_equal(synthetic_label_image, original_copy)


def test_invalid_input_rejections():
    """Verify graceful rejection of None or zero-element arrays."""
    with pytest.raises(ValueError, match="Invalid image"):
        aspect_preserving_resize(None)  # type: ignore

    with pytest.raises(ValueError, match="Invalid image"):
        apply_clahe(np.array([], dtype=np.uint8))

    with pytest.raises(ValueError, match="Invalid image"):
        apply_denoising(None)  # type: ignore

    with pytest.raises(ValueError, match="Invalid image"):
        apply_deskew(np.array([1, 2, 3], dtype=np.uint8))

    with pytest.raises(ValueError, match="Invalid image"):
        preprocess_image(None)  # type: ignore


# =====================================================================
# 7. Combined Preprocessing Pipeline Tests
# =====================================================================

def test_combined_preprocessing_pipeline_defaults(synthetic_label_image: np.ndarray):
    """Test full default pipeline execution (resize enabled, CLAHE enabled, denoise/deskew disabled)."""
    cfg = CVPreprocessingConfig()
    processed_img, info, warnings, errors = preprocess_image(synthetic_label_image, config=cfg)

    assert isinstance(info, PreprocessingInfo)
    assert len(errors) == 0
    assert info.original_size == (800, 500)
    assert info.processed_size == (800, 500)
    assert any("clahe" in op.lower() for op in info.applied_operations)
    assert any("denoising (disabled_in_config)" in op.lower() for op in info.skipped_operations)
    assert any("deskew (disabled_in_config)" in op.lower() for op in info.skipped_operations)
    assert processed_img.shape == (500, 800, 3)
