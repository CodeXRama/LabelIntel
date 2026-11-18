"""
LabelIntel — Computer Vision OCR Engine and Parser Test Suite
Verifies PaddleOCR 3.x and legacy 2.x parsing, coordinate restoration, error handling,
deterministic mocked tests, and live genuine inference on synthetic packaging text.
"""

from unittest.mock import MagicMock, patch
import cv2
import numpy as np
import pytest

from engines.cv_engine.config import CVOCRConfig, CVPreprocessingConfig
from engines.cv_engine.ocr.engine import PaddleOCREngine, get_ocr_engine
from engines.cv_engine.ocr.parser import parse_ocr_results
from engines.cv_engine.preprocessors.pipeline import preprocess_image
from engines.cv_engine.schemas import BoundingBox, OCRTextBlock, Point2D, PreprocessingInfo


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def mock_paddlex_result() -> dict:
    """Simulates PaddleOCR 3.x / PaddleX dictionary output."""
    return {
        "rec_texts": ["MRP Rs. 120.00", "NET QTY: 500g"],
        "rec_scores": [0.9854, 0.9912],
        "rec_polys": [
            np.array([[20, 40], [200, 40], [200, 80], [20, 80]], dtype=np.int32),
            np.array([[20, 100], [180, 100], [180, 140], [20, 140]], dtype=np.int32),
        ],
        "rec_boxes": np.array([[20, 40, 200, 80], [20, 100, 180, 140]], dtype=np.int32),
    }


@pytest.fixture
def mock_legacy_result() -> list:
    """Simulates PaddleOCR 2.x legacy nested list output."""
    return [
        [
            [[[20.0, 40.0], [200.0, 40.0], [200.0, 80.0], [20.0, 80.0]], ("MRP Rs. 120.00", 0.9854)],
            [[[20.0, 100.0], [180.0, 100.0], [180.0, 140.0], [20.0, 140.0]], ("NET QTY: 500g", 0.9912)],
        ]
    ]


# =====================================================================
# 1. OCR Parser Tests (Deterministic Mocked)
# =====================================================================

def test_ocr_parser_paddlex_format(mock_paddlex_result: dict):
    """Verify parsing of PaddleOCR 3.x dictionary structure."""
    blocks, warnings = parse_ocr_results(mock_paddlex_result, source_image_ref="sample.jpg")

    assert len(blocks) == 2
    assert len(warnings) == 0

    # First block
    assert blocks[0].block_id == "ocr_block_0001"
    assert blocks[0].text == "MRP Rs. 120.00"
    assert blocks[0].confidence == 0.9854
    assert len(blocks[0].polygon) == 4
    assert blocks[0].bounding_box == BoundingBox(x_min=20.0, y_min=40.0, x_max=200.0, y_max=80.0)
    assert blocks[0].source_image_ref == "sample.jpg"

    # Second block
    assert blocks[1].block_id == "ocr_block_0002"
    assert blocks[1].text == "NET QTY: 500g"
    assert blocks[1].confidence == 0.9912


def test_ocr_parser_legacy_format(mock_legacy_result: list):
    """Verify parsing of PaddleOCR 2.x legacy nested list structure."""
    blocks, warnings = parse_ocr_results(mock_legacy_result, source_image_ref="legacy_sample.png")

    assert len(blocks) == 2
    assert blocks[0].text == "MRP Rs. 120.00"
    assert blocks[0].confidence == 0.9854
    assert blocks[1].text == "NET QTY: 500g"


def test_ocr_parser_empty_result():
    """Verify graceful handling of empty or None output."""
    blocks_none, warnings_none = parse_ocr_results(None)
    assert blocks_none == []

    blocks_empty_list, _ = parse_ocr_results([])
    assert blocks_empty_list == []

    blocks_empty_dict, _ = parse_ocr_results({})
    assert blocks_empty_dict == []


def test_ocr_parser_malformed_result():
    """Verify robust handling of corrupted or unexpected structures."""
    malformed_dict = {
        "rec_texts": ["Unmatched text"],
        "rec_scores": [0.95],
        "rec_polys": [],  # Mismatched length
    }
    blocks, warnings = parse_ocr_results(malformed_dict)
    assert blocks == []
    assert any("mismatched" in w.lower() for w in warnings)


def test_ocr_parser_confidence_filter(mock_paddlex_result: dict):
    """Verify confidence filtering threshold."""
    # min_confidence=0.99 should exclude block 1 (0.9854) and keep block 2 (0.9912)
    blocks, _ = parse_ocr_results(mock_paddlex_result, min_confidence=0.99)
    assert len(blocks) == 1
    assert blocks[0].text == "NET QTY: 500g"


# =====================================================================
# 2. Coordinate Restoration Invariant Tests
# =====================================================================

def test_coordinate_restoration_resized_image():
    """
    Original Image: 1000x600.
    Resized by 0.5 to: 500x300.
    OCR detection on processed image at [50, 30, 200, 70].
    Expected original coordinate mapping: [100, 60, 400, 140].
    """
    # Create synthetic preprocessing metadata representing 0.5 scale
    scale = 0.5
    sx, sy = scale, scale
    M_fwd = [[sx, 0.0, 0.0], [0.0, sy, 0.0], [0.0, 0.0, 1.0]]
    M_inv = [[1.0 / sx, 0.0, 0.0], [0.0, 1.0 / sy, 0.0], [0.0, 0.0, 1.0]]

    prep_info = PreprocessingInfo(
        original_size=(1000, 600),
        processed_size=(500, 300),
        scale_factor_x=sx,
        scale_factor_y=sy,
        applied_operations=["aspect_preserving_resize"],
        forward_matrix=M_fwd,
        inverse_matrix=M_inv,
    )

    raw_output = {
        "rec_texts": ["BATCH 2026"],
        "rec_scores": [0.97],
        "rec_polys": [
            np.array([[50, 30], [200, 30], [200, 70], [50, 70]], dtype=np.float32)
        ],
    }

    blocks, _ = parse_ocr_results(raw_output, preprocessing_info=prep_info)
    assert len(blocks) == 1

    # Coordinates in restored original space must be scaled by 2.0
    bbox = blocks[0].bounding_box
    assert bbox.x_min == 100.0
    assert bbox.y_min == 60.0
    assert bbox.x_max == 400.0
    assert bbox.y_max == 140.0


def test_coordinate_restoration_rotated_image():
    """
    Verify coordinates are correctly unrotated back to original image orientation.
    """
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    cfg = CVPreprocessingConfig(resize_enabled=False, clahe_enabled=False)
    # Rotate by 90 degrees clockwise for simple orthogonal test
    _, prep_info, _, _ = preprocess_image(img, config=cfg, force_deskew_angle=90.0)

    # Point at center (200, 200) in processed space
    proc_pt = Point2D(x=200.0, y=200.0)
    orig_pt = prep_info.transform_polygon_to_original([proc_pt])[0]

    # Center remains invariant under center rotation
    assert abs(orig_pt.x - 200.0) < 1.0
    assert abs(orig_pt.y - 200.0) < 1.0


def test_coordinate_clamping_to_original_bounds():
    """Ensure coordinates do not exceed raw image boundaries due to numerical rounding."""
    prep_info = PreprocessingInfo(
        original_size=(100, 100),
        processed_size=(100, 100),
        scale_factor_x=1.0,
        scale_factor_y=1.0,
        forward_matrix=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        inverse_matrix=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    )
    raw_output = {
        "rec_texts": ["EDGE TEXT"],
        "rec_scores": [0.99],
        "rec_polys": [
            np.array([[-5, -10], [105, -10], [105, 115], [-5, 115]], dtype=np.float32)
        ],
    }
    blocks, _ = parse_ocr_results(raw_output, preprocessing_info=prep_info)
    assert len(blocks) == 1
    bbox = blocks[0].bounding_box
    # Clamped within [0, 100]
    assert bbox.x_min == 0.0
    assert bbox.y_min == 0.0
    assert bbox.x_max == 100.0
    assert bbox.y_max == 100.0


# =====================================================================
# 3. OCR Engine Lifecycle & Error Handling Tests
# =====================================================================

def test_engine_singleton_reuse():
    """Verify get_ocr_engine() returns the same reusable instance."""
    engine1 = get_ocr_engine()
    engine2 = get_ocr_engine()
    assert engine1 is engine2


def test_engine_invalid_image_handling():
    """Verify graceful handling when None or invalid array is passed to predict."""
    engine = PaddleOCREngine()
    blocks, warnings, errors = engine.predict(None)  # type: ignore
    assert blocks == []
    assert len(errors) > 0
    assert any("invalid image" in e.lower() for e in errors)


def test_engine_initialization_failure_handling():
    """Verify structured error returned when PaddleOCR initialization fails."""
    engine = PaddleOCREngine()
    with patch("paddleocr.PaddleOCR", side_effect=RuntimeError("Simulated missing model weights")):
        engine._is_initialized = False
        engine._ocr = None
        blocks, warnings, errors = engine.predict(np.zeros((100, 100, 3), dtype=np.uint8))
        assert blocks == []
        assert any("initialization failed" in e.lower() for e in errors)


def test_engine_no_text_image_handling():
    """Verify an image containing zero text returns empty list without error."""
    engine = PaddleOCREngine()
    mock_ocr = MagicMock()
    # Mocking PaddleOCR predict() returning empty list (no text found)
    mock_ocr.predict.return_value = []
    engine._ocr = mock_ocr
    engine._is_initialized = True

    blocks, warnings, errors = engine.predict(np.ones((200, 200, 3), dtype=np.uint8))
    assert blocks == []
    assert len(errors) == 0
    assert any("detected zero text" in w.lower() for w in warnings)


# =====================================================================
# 4. Live Genuine OCR Inference Smoke Test (Synthetic Text)
# =====================================================================

def test_live_genuine_ocr_inference_synthetic_label():
    """
    Live genuine end-to-end inference test using the actual installed PaddleOCR model.
    Note: Evaluated on a deterministic synthetic packaging text image.
    Real-world packaging evaluation is pending acquisition of physical samples.
    """
    # 1. Create a clean synthetic packaging label image
    img = np.ones((200, 600, 3), dtype=np.uint8) * 255
    cv2.putText(img, "MRP Rs. 75.00", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(img, "NET QTY: 1 kg", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)

    # 2. Execute inference through PaddleOCREngine
    engine = get_ocr_engine(CVOCRConfig(device="cpu", enable_mkldnn=False))
    blocks, warnings, errors = engine.predict(img, source_image_ref="synthetic_smoke_test.png")

    assert len(errors) == 0, f"Inference errors: {errors}"
    assert len(blocks) >= 2, f"Expected at least 2 text blocks, got {len(blocks)}"

    extracted_texts = [b.text for b in blocks]
    assert any("MRP" in t for t in extracted_texts)
    assert any("75.00" in t or "75" in t for t in extracted_texts)
    assert any("NET" in t for t in extracted_texts)

    # Verify high recognition confidence
    for b in blocks:
        assert b.confidence > 0.85
        assert len(b.polygon) == 4
        assert b.bounding_box.width > 0
        assert b.bounding_box.height > 0
