"""
Tests for Image Validation and Image Quality Assessment Modules.
Verifies format validation, dimension checks, aspect ratios, corruption guards,
Laplacian sharpness scoring, luminance, contrast, and histogram clipping.
"""

from pathlib import Path
import cv2
import numpy as np
import pytest

from engines.cv_engine.config import CVQualityConfig, CVValidationConfig
from engines.cv_engine.quality.quality_assessor import assess_image_quality
from engines.cv_engine.schemas import ImageAssessmentResult, ValidationResult
from engines.cv_engine.validators.image_validator import (
    detect_format_from_bytes,
    validate_image_input,
)
from engines.cv_engine import assess_image


# =====================================================================
# Fixtures for Synthetic Test Images
# =====================================================================

@pytest.fixture
def normal_bgr_image() -> np.ndarray:
    """Generate a sharp, well-balanced synthetic image with text and edges."""
    img = np.ones((400, 600, 3), dtype=np.uint8) * 200  # Light gray substrate
    # Add dark shapes and text for high-contrast edges
    cv2.putText(img, "LABELINTEL SAMPLE", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 3)
    cv2.putText(img, "NET QTY: 500g", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
    cv2.putText(img, "MRP Rs 150.00", (50, 260), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
    cv2.rectangle(img, (40, 40), (560, 360), (20, 20, 20), 2)
    return img


@pytest.fixture
def valid_jpeg_bytes(normal_bgr_image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".jpg", normal_bgr_image)
    assert success
    return encoded.tobytes()


@pytest.fixture
def valid_png_bytes(normal_bgr_image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".png", normal_bgr_image)
    assert success
    return encoded.tobytes()


# =====================================================================
# Stage 1: Image Validation Tests
# =====================================================================

def test_validate_valid_jpeg_bytes(valid_jpeg_bytes: bytes):
    result, img = validate_image_input(valid_jpeg_bytes, filename="test_sample.jpg")
    assert result.is_valid is True
    assert result.metadata is not None
    assert result.metadata.image_format == "JPEG"
    assert result.metadata.width == 600
    assert result.metadata.height == 400
    assert result.metadata.channels == 3
    assert result.metadata.aspect_ratio == 1.5
    assert len(result.errors) == 0
    assert img is not None
    assert img.shape == (400, 600, 3)


def test_validate_valid_png_bytes(valid_png_bytes: bytes):
    result, img = validate_image_input(valid_png_bytes, filename="test_sample.png")
    assert result.is_valid is True
    assert result.metadata is not None
    assert result.metadata.image_format == "PNG"
    assert result.metadata.width == 600
    assert result.metadata.height == 400
    assert result.metadata.channels == 3
    assert img is not None


def test_validate_valid_image_file_path(tmp_path: Path, valid_jpeg_bytes: bytes):
    file_path = tmp_path / "packaged_item.jpg"
    file_path.write_bytes(valid_jpeg_bytes)

    result, img = validate_image_input(str(file_path))
    assert result.is_valid is True
    assert result.metadata is not None
    assert result.metadata.filename == "packaged_item.jpg"
    assert result.metadata.source_path == str(file_path.resolve())
    assert result.metadata.file_size_bytes == len(valid_jpeg_bytes)
    assert img is not None


def test_validate_png_with_alpha_channel():
    """Verify 4-channel BGRA images are converted to 3-channel BGR with a warning."""
    bgra = np.zeros((300, 300, 4), dtype=np.uint8)
    bgra[:, :, :3] = 128
    bgra[:, :, 3] = 255  # Fully opaque alpha
    success, encoded = cv2.imencode(".png", bgra)
    assert success

    result, img = validate_image_input(encoded.tobytes(), filename="transparent_label.png")
    assert result.is_valid is True
    assert result.metadata.channels == 3
    assert any("alpha channel" in w.lower() for w in result.warnings)
    assert img is not None
    assert img.shape == (300, 300, 3)


def test_validate_corrupted_image_header():
    """Header has JPEG magic bytes, but remainder is invalid truncated bytes."""
    corrupted_data = b"\xff\xd8\xff\xe0" + b"\x00" * 20
    result, img = validate_image_input(corrupted_data, filename="corrupted.jpg")
    assert result.is_valid is False
    assert img is None
    assert any("corrupted" in e.lower() or "failed to decode" in e.lower() for e in result.errors)


def test_validate_unsupported_file_format():
    """Plain text content disguised as a .jpg filename."""
    text_content = b"This is a text document, not a JPEG image."
    result, img = validate_image_input(text_content, filename="fake_image.jpg")
    assert result.is_valid is False
    assert img is None
    assert any("unsupported or unrecognized" in e.lower() for e in result.errors)


def test_validate_extremely_small_image():
    """Image below the 100x100 min_dimension threshold."""
    tiny_img = np.zeros((64, 64, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".png", tiny_img)
    assert success

    result, img = validate_image_input(encoded.tobytes(), filename="tiny.png")
    assert result.is_valid is False
    assert img is None
    assert any("below minimum threshold" in e.lower() for e in result.errors)


def test_validate_extreme_aspect_ratio():
    """Image with 1:12 aspect ratio (1800x150), exceeding max_aspect_ratio 10.0 while >= min_dimension."""
    ribbon_img = np.zeros((150, 1800, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".png", ribbon_img)
    assert success

    result, img = validate_image_input(encoded.tobytes(), filename="ribbon.png")
    assert result.is_valid is False
    assert img is None
    assert any("extreme aspect ratio" in e.lower() for e in result.errors)


def test_validate_nonexistent_file():
    result, img = validate_image_input("D:/nonexistent_path/absent_label.jpg")
    assert result.is_valid is False
    assert img is None
    assert any("not found" in e.lower() for e in result.errors)


def test_validate_empty_file(tmp_path: Path):
    empty_file = tmp_path / "empty.jpg"
    empty_file.write_bytes(b"")

    result, img = validate_image_input(empty_file)
    assert result.is_valid is False
    assert img is None
    assert any("empty" in e.lower() for e in result.errors)


def test_detect_format_from_bytes():
    assert detect_format_from_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF") == "JPEG"
    assert detect_format_from_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR") == "PNG"
    assert detect_format_from_bytes(b"RIFF\x20\x00\x00\x00WEBPVP8 ") == "WEBP"
    assert detect_format_from_bytes(b"\x00\x00\x00\x20ftypavif\x00\x00\x00\x00") == "AVIF"
    assert detect_format_from_bytes(b"GIF89a\x01\x00") is None
    assert detect_format_from_bytes(b"short") is None


# =====================================================================
# Stage 2: Image Quality Assessment Tests
# =====================================================================

def test_quality_normal_sharp_image(normal_bgr_image: np.ndarray):
    metrics = assess_image_quality(normal_bgr_image)
    assert metrics.is_blurry is False
    assert metrics.blur_laplacian_variance > 100.0
    assert metrics.is_under_exposed is False
    assert metrics.is_over_exposed is False
    assert metrics.contrast_std > 25.0
    assert metrics.quality_warnings == []


def test_quality_blurry_image(normal_bgr_image: np.ndarray):
    """Heavy Gaussian blur applied to sharp text image."""
    blurry = cv2.GaussianBlur(normal_bgr_image, (51, 51), 25.0)
    metrics = assess_image_quality(blurry)
    assert metrics.is_blurry is True
    assert metrics.blur_laplacian_variance < 100.0
    assert any("sharpness" in w.lower() or "blur" in w.lower() for w in metrics.quality_warnings)


def test_quality_low_light_underexposed():
    """Dark image simulating dim warehouse or shadow."""
    dark_img = np.full((300, 300, 3), 20, dtype=np.uint8)
    metrics = assess_image_quality(dark_img)
    assert metrics.is_under_exposed is True
    assert metrics.brightness_mean < 40.0
    assert any("underexposed" in w.lower() for w in metrics.quality_warnings)


def test_quality_overexposed():
    """Bright washed out image simulating direct flash or sunlight."""
    bright_img = np.full((300, 300, 3), 235, dtype=np.uint8)
    metrics = assess_image_quality(bright_img)
    assert metrics.is_over_exposed is True
    assert metrics.brightness_mean > 220.0
    assert any("overexposed" in w.lower() for w in metrics.quality_warnings)


def test_quality_low_contrast():
    """Low dynamic range image (near-uniform gray)."""
    flat_gray = np.full((300, 300, 3), 128, dtype=np.uint8)
    # Add very faint variation
    flat_gray[:50, :50] = 130
    metrics = assess_image_quality(flat_gray)
    assert metrics.contrast_std < 25.0
    assert any("low contrast" in w.lower() for w in metrics.quality_warnings)


def test_quality_shadow_clipping():
    """Image with 20% pure black pixels (clipped shadows)."""
    img = np.full((100, 100, 3), 100, dtype=np.uint8)
    img[:20, :] = 0  # 20% pure black
    metrics = assess_image_quality(img)
    assert metrics.clipping_low_pct >= 0.20
    assert any("shadow clipping" in w.lower() for w in metrics.quality_warnings)


def test_quality_highlight_clipping():
    """Image with 20% pure white pixels (glare/overexposed saturation)."""
    img = np.full((100, 100, 3), 100, dtype=np.uint8)
    img[:20, :] = 255  # 20% pure white
    metrics = assess_image_quality(img)
    assert metrics.clipping_high_pct >= 0.20
    assert any("highlight clipping" in w.lower() for w in metrics.quality_warnings)


def test_quality_preserves_original_image(normal_bgr_image: np.ndarray):
    """Guarantee that quality assessment does not mutate original pixel data."""
    original_copy = normal_bgr_image.copy()
    _ = assess_image_quality(normal_bgr_image)
    assert np.array_equal(normal_bgr_image, original_copy)


def test_quality_invalid_inputs():
    with pytest.raises(ValueError, match="None or an empty"):
        assess_image_quality(None)  # type: ignore

    with pytest.raises(ValueError, match="None or an empty"):
        assess_image_quality(np.array([], dtype=np.uint8))

    with pytest.raises(ValueError, match="insufficient dimensions"):
        assess_image_quality(np.array([1, 2, 3], dtype=np.uint8))


def test_quality_configurable_thresholds(normal_bgr_image: np.ndarray):
    """Test custom configuration override."""
    custom_cfg = CVQualityConfig(
        blur_laplacian_threshold=5000.0,  # Unreasonably high threshold
        brightness_low_threshold=220.0,   # Set above image's mean (~190) to force underexposure flag
    )
    metrics = assess_image_quality(normal_bgr_image, config=custom_cfg)
    assert metrics.is_blurry is True  # Flagged under strict custom threshold
    assert metrics.is_under_exposed is True


# =====================================================================
# Stage 1 + 2: Composite Assessment Tests
# =====================================================================

def test_combined_assess_image_success(valid_jpeg_bytes: bytes):
    assessment = assess_image(valid_jpeg_bytes, filename="biscuit_pack.jpg")
    assert isinstance(assessment, ImageAssessmentResult)
    assert assessment.validation.is_valid is True
    assert assessment.validation.metadata.filename == "biscuit_pack.jpg"
    assert assessment.quality is not None
    assert assessment.quality.is_blurry is False


def test_combined_assess_image_failure():
    assessment = assess_image(b"not an image", filename="garbage.jpg")
    assert isinstance(assessment, ImageAssessmentResult)
    assert assessment.validation.is_valid is False
    assert assessment.quality is None
    assert len(assessment.validation.errors) > 0

def test_validate_large_image_warning():
    """Image exceeding max_dimension triggers downscaling warning while remaining valid."""
    large_img = np.zeros((4500, 1000, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".png", large_img)
    assert success

    result, img = validate_image_input(encoded.tobytes(), filename="huge_packaging.png")
    assert result.is_valid is True
    assert img is not None
    assert any("exceed standard limit" in w.lower() for w in result.warnings)


def test_quality_grayscale_single_channel_input():
    """Verify quality assessment supports direct 1-channel 2D and 3D grayscale matrices."""
    gray_2d = np.full((200, 200), 120, dtype=np.uint8)
    metrics_2d = assess_image_quality(gray_2d)
    assert metrics_2d.brightness_mean == 120.0

    gray_3d = np.full((200, 200, 1), 120, dtype=np.uint8)
    metrics_3d = assess_image_quality(gray_3d)
    assert metrics_3d.brightness_mean == 120.0


def test_validate_numpy_array_input_directly(normal_bgr_image: np.ndarray):
    """Test validating an already-loaded numpy array."""
    result, img = validate_image_input(normal_bgr_image, filename="direct_array")
    assert result.is_valid is True
    assert result.metadata.image_format == "NUMPY_ARRAY"
    assert result.metadata.width == 600
    assert result.metadata.height == 400
    assert img is not None
