"""
LabelIntel Computer Vision Engine Package.
Provides image validation, quality metrics, preprocessing, detection, OCR,
and physical character measurement contracts.
"""

from engines.cv_engine.config import CVValidationConfig, CVQualityConfig
from engines.cv_engine.schemas import (
    Point2D,
    BoundingBox,
    ImageMetadata,
    ImageQualityMetrics,
    ValidationResult,
    ImageAssessmentResult,
    PreprocessingInfo,
    DetectionRegion,
    DetectorInfo,
    OCRTextBlock,
    GlyphMeasurement,
    PhysicalMeasurementResult,
    CVEngineOutput,
)
from engines.cv_engine.validators import validate_image_input, detect_format_from_bytes
from engines.cv_engine.quality import assess_image_quality


def assess_image(
    source,
    filename=None,
    validation_config=None,
    quality_config=None,
) -> ImageAssessmentResult:
    """
    Combined convenience executor for Stages 1 and 2 (Validation + Quality Assessment).
    Decodes the image once and reuses the matrix for quality analysis to maximize throughput.
    """
    val_res, decoded_img = validate_image_input(source, filename=filename, config=validation_config)
    if not val_res.is_valid or decoded_img is None:
        return ImageAssessmentResult(validation=val_res, quality=None)

    quality_res = assess_image_quality(decoded_img, config=quality_config)
    return ImageAssessmentResult(validation=val_res, quality=quality_res)


__all__ = [
    "CVValidationConfig",
    "CVQualityConfig",
    "Point2D",
    "BoundingBox",
    "ImageMetadata",
    "ImageQualityMetrics",
    "ValidationResult",
    "ImageAssessmentResult",
    "PreprocessingInfo",
    "DetectionRegion",
    "DetectorInfo",
    "OCRTextBlock",
    "GlyphMeasurement",
    "PhysicalMeasurementResult",
    "CVEngineOutput",
    "validate_image_input",
    "detect_format_from_bytes",
    "assess_image_quality",
    "assess_image",
]
