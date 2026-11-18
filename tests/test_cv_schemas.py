"""
Tests for CV Engine Pydantic Schemas.
Verifies contract validation, computed fields, and serialization.
"""

import pytest
from engines.cv_engine.schemas import (
    Point2D,
    BoundingBox,
    ImageMetadata,
    ImageQualityMetrics,
    PreprocessingInfo,
    DetectionRegion,
    DetectorInfo,
    OCRTextBlock,
    GlyphMeasurement,
    PhysicalMeasurementResult,
    CVEngineOutput
)


def test_bounding_box_computed_dimensions():
    bbox = BoundingBox(x_min=10.0, y_min=20.0, x_max=110.0, y_max=80.0)
    assert bbox.width == 100.0
    assert bbox.height == 60.0


def test_cv_engine_output_contract():
    metadata = ImageMetadata(
        filename="biscuit_pack_label.jpg",
        source_path="/data/samples/biscuit_pack_label.jpg",
        file_size_bytes=245890,
        image_format="JPEG",
        width=1920,
        height=1080,
        channels=3,
        aspect_ratio=1.7778
    )

    quality = ImageQualityMetrics(
        blur_laplacian_variance=214.5,
        is_blurry=False,
        brightness_mean=142.3,
        contrast_std=58.2,
        clipping_low_pct=0.01,
        clipping_high_pct=0.03,
        is_under_exposed=False,
        is_over_exposed=False,
        quality_warnings=[]
    )

    preprocessing = PreprocessingInfo(
        original_size=(1920, 1080),
        processed_size=(1920, 1080),
        scale_factor_x=1.0,
        scale_factor_y=1.0,
        deskew_angle_degrees=-0.5,
        applied_operations=["aspect_preserving_resize", "clahe"]
    )

    detector = DetectorInfo(
        detector_available=True,
        model_name="yolo-metrology-roi",
        regions_detected=[
            DetectionRegion(
                region_id="reg_01",
                class_name="mrp_panel",
                confidence=0.88,
                bounding_box=BoundingBox(x_min=50.0, y_min=100.0, x_max=400.0, y_max=250.0),
                polygon=[
                    Point2D(x=50.0, y=100.0),
                    Point2D(x=400.0, y=100.0),
                    Point2D(x=400.0, y=250.0),
                    Point2D(x=50.0, y=250.0)
                ]
            )
        ]
    )

    ocr_blocks = [
        OCRTextBlock(
            block_id="ocr_01",
            text="MRP Rs. 50.00 (INCL. OF ALL TAXES)",
            confidence=0.96,
            polygon=[
                Point2D(x=55.0, y=110.0),
                Point2D(x=380.0, y=110.0),
                Point2D(x=380.0, y=145.0),
                Point2D(x=55.0, y=145.0)
            ],
            bounding_box=BoundingBox(x_min=55.0, y_min=110.0, x_max=380.0, y_max=145.0),
            source_image_ref="biscuit_pack_label.jpg",
            associated_region_id="reg_01",
            line_index=0
        )
    ]

    measurements = PhysicalMeasurementResult(
        aruco_detected=True,
        marker_id=42,
        marker_corners=[
            Point2D(x=10.0, y=10.0),
            Point2D(x=30.0, y=10.0),
            Point2D(x=30.0, y=30.0),
            Point2D(x=10.0, y=30.0)
        ],
        marker_size_specified_mm=20.0,
        pixels_per_mm=1.0,
        calibration_status="calibrated",
        glyph_measurements=[
            GlyphMeasurement(
                block_id="ocr_01",
                text_snippet="MRP Rs. 50.00",
                estimated_glyph_height_px=22.0,
                estimated_glyph_height_mm=22.0,
                uncertainty_mm=0.5
            )
        ],
        measurement_warnings=[]
    )

    output = CVEngineOutput(
        success=True,
        pipeline_version="1.0.0",
        metadata=metadata,
        quality=quality,
        preprocessing=preprocessing,
        detector=detector,
        ocr_blocks=ocr_blocks,
        physical_measurements=measurements,
        processing_warnings=[],
        errors=[]
    )

    # Serialization test
    output_dict = output.model_dump()
    assert output_dict["success"] is True
    assert len(output_dict["ocr_blocks"]) == 1
    assert output_dict["ocr_blocks"][0]["text"] == "MRP Rs. 50.00 (INCL. OF ALL TAXES)"
    assert output_dict["physical_measurements"]["calibration_status"] == "calibrated"


def test_ocr_fallback_contract():
    """Verify schema works in full-image OCR fallback mode when detector is unavailable."""
    metadata = ImageMetadata(
        filename="fallback_sample.png",
        file_size_bytes=1024,
        image_format="PNG",
        width=800,
        height=600,
        channels=3,
        aspect_ratio=1.333
    )
    quality = ImageQualityMetrics(
        blur_laplacian_variance=150.0,
        is_blurry=False,
        brightness_mean=120.0,
        contrast_std=40.0,
        clipping_low_pct=0.0,
        clipping_high_pct=0.0,
        is_under_exposed=False,
        is_over_exposed=False
    )
    preprocessing = PreprocessingInfo(
        original_size=(800, 600),
        processed_size=(800, 600)
    )
    # Detector unavailable
    detector = DetectorInfo(detector_available=False, model_name=None, regions_detected=[])

    output = CVEngineOutput(
        success=True,
        metadata=metadata,
        quality=quality,
        preprocessing=preprocessing,
        detector=detector,
        ocr_blocks=[]
    )
    assert output.detector.detector_available is False
    assert output.detector.regions_detected == []
