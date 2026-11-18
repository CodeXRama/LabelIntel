"""
LabelIntel — Computer Vision Output Contract
Defines the Pydantic schemas for the Computer Vision Engine pipeline output.
"""

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, computed_field


class Point2D(BaseModel):
    """2D coordinate point representation."""
    x: float = Field(..., description="X coordinate (horizontal pixel coordinate)")
    y: float = Field(..., description="Y coordinate (vertical pixel coordinate)")


class BoundingBox(BaseModel):
    """Axis-aligned bounding box representation in image coordinate space."""
    x_min: float = Field(..., description="Top-left X coordinate")
    y_min: float = Field(..., description="Top-left Y coordinate")
    x_max: float = Field(..., description="Bottom-right X coordinate")
    y_max: float = Field(..., description="Bottom-right Y coordinate")

    @computed_field
    @property
    def width(self) -> float:
        return max(0.0, self.x_max - self.x_min)

    @computed_field
    @property
    def height(self) -> float:
        return max(0.0, self.y_max - self.y_min)


class ImageMetadata(BaseModel):
    """Metadata regarding the input image."""
    filename: str = Field(..., description="Base filename of the image")
    source_path: Optional[str] = Field(None, description="Absolute or relative path of the source image")
    file_size_bytes: int = Field(..., description="File size in bytes")
    image_format: str = Field(..., description="Image file format (e.g., JPEG, PNG)")
    width: int = Field(..., description="Original image width in pixels")
    height: int = Field(..., description="Original image height in pixels")
    channels: int = Field(..., description="Number of color channels (e.g., 3 for BGR/RGB, 1 for Grayscale)")
    aspect_ratio: float = Field(..., description="Width-to-height ratio (width / height)")


class ImageQualityMetrics(BaseModel):
    """Image quality assessment results to prevent false readings on degraded inputs."""
    blur_laplacian_variance: float = Field(..., description="Laplacian variance score (higher means sharper)")
    is_blurry: bool = Field(..., description="True if blur score is below threshold")
    brightness_mean: float = Field(..., description="Mean pixel luminance across grayscale representation (0-255)")
    contrast_std: float = Field(..., description="Standard deviation of pixel luminance (0-255)")
    clipping_low_pct: float = Field(..., description="Percentage of pixels clipped near black (underexposure)")
    clipping_high_pct: float = Field(..., description="Percentage of pixels clipped near white (overexposure)")
    is_under_exposed: bool = Field(..., description="True if underexposure exceeds acceptable threshold")
    is_over_exposed: bool = Field(..., description="True if overexposure exceeds acceptable threshold")
    quality_warnings: List[str] = Field(default_factory=list, description="Quality alert messages for operator")


class ValidationResult(BaseModel):
    """Result of image format and dimension validation."""
    is_valid: bool = Field(..., description="True if the image meets all structural and format requirements")
    metadata: Optional[ImageMetadata] = Field(None, description="Extracted image metadata if valid")
    errors: List[str] = Field(default_factory=list, description="Validation failure error messages")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal validation warnings")


class ImageAssessmentResult(BaseModel):
    """Composite result of Stage 1 (Validation) and Stage 2 (Quality Assessment)."""
    validation: ValidationResult = Field(..., description="Validation outcome and image metadata")
    quality: Optional[ImageQualityMetrics] = Field(
        None,
        description="Quality assessment metrics (None if image validation failed)"
    )


class PreprocessingInfo(BaseModel):
    """Record of preprocessing transformations applied before OCR/detection."""
    original_size: Tuple[int, int] = Field(..., description="(width, height) of raw input")
    processed_size: Tuple[int, int] = Field(..., description="(width, height) passed to OCR engine")
    scale_factor_x: float = Field(1.0, description="Horizontal scaling factor applied")
    scale_factor_y: float = Field(1.0, description="Vertical scaling factor applied")
    deskew_angle_degrees: float = Field(0.0, description="Rotational deskew angle applied in degrees")
    applied_operations: List[str] = Field(
        default_factory=list,
        description="List of applied filter names, e.g. ['aspect_resize', 'clahe', 'denoise', 'deskew']"
    )
    skipped_operations: List[str] = Field(
        default_factory=list,
        description="List of operations evaluated but skipped with reason"
    )
    forward_matrix: List[List[float]] = Field(
        default_factory=lambda: [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        description="3x3 homogeneous transformation matrix from raw to processed coordinates"
    )
    inverse_matrix: List[List[float]] = Field(
        default_factory=lambda: [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        description="3x3 homogeneous inverse matrix from processed to raw coordinates"
    )

    def map_to_processed(self, x: float, y: float) -> Tuple[float, float]:
        """Transform a 2D point from original raw image coordinates to processed image coordinates."""
        m = self.forward_matrix
        new_x = m[0][0] * x + m[0][1] * y + m[0][2]
        new_y = m[1][0] * x + m[1][1] * y + m[1][2]
        w = m[2][0] * x + m[2][1] * y + m[2][2]
        if abs(w - 1.0) > 1e-7 and abs(w) > 1e-9:
            new_x /= w
            new_y /= w
        return (round(new_x, 4), round(new_y, 4))

    def map_to_original(self, x: float, y: float) -> Tuple[float, float]:
        """Transform a 2D point from processed image coordinates back to original raw image coordinates."""
        inv = self.inverse_matrix
        orig_x = inv[0][0] * x + inv[0][1] * y + inv[0][2]
        orig_y = inv[1][0] * x + inv[1][1] * y + inv[1][2]
        w = inv[2][0] * x + inv[2][1] * y + inv[2][2]
        if abs(w - 1.0) > 1e-7 and abs(w) > 1e-9:
            orig_x /= w
            orig_y /= w
        return (round(orig_x, 4), round(orig_y, 4))

    def transform_polygon_to_original(self, polygon: List[Point2D]) -> List[Point2D]:
        """Invert all vertices of a polygon from processed coordinates back to original coordinates."""
        mapped = []
        for pt in polygon:
            ox, oy = self.map_to_original(pt.x, pt.y)
            mapped.append(Point2D(x=ox, y=oy))
        return mapped

    def transform_polygon_to_processed(self, polygon: List[Point2D]) -> List[Point2D]:
        """Map all vertices of a polygon from original coordinates to processed coordinates."""
        mapped = []
        for pt in polygon:
            px, py = self.map_to_processed(pt.x, pt.y)
            mapped.append(Point2D(x=px, y=py))
        return mapped


class DetectionRegion(BaseModel):
    """Declaration region localized by an optional object detector (e.g. YOLO/contour)."""
    region_id: str = Field(..., description="Unique identifier for the detected region")
    class_name: str = Field(..., description="Detected category (e.g. mrp_panel, date_cluster, nutrition_box)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detector confidence score")
    bounding_box: BoundingBox = Field(..., description="Axis-aligned bounding box in original image coordinates")
    polygon: Optional[List[Point2D]] = Field(None, description="Oriented polygon boundary if available")


class DetectorInfo(BaseModel):
    """Status and detections of optional declaration region detectors."""
    detector_available: bool = Field(False, description="True if a secondary region detector was executed")
    model_name: Optional[str] = Field(None, description="Identifier of the detector model used")
    regions_detected: List[DetectionRegion] = Field(default_factory=list, description="Localized declaration regions")


class OCRTextBlock(BaseModel):
    """An individual text block extracted via PaddleOCR."""
    block_id: str = Field(..., description="Unique identifier for this OCR block")
    text: str = Field(..., description="Raw decoded text recognized by OCR")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR recognition confidence score")
    polygon: List[Point2D] = Field(..., description="4-point bounding polygon in original unscaled coordinates")
    bounding_box: BoundingBox = Field(..., description="Enclosing bounding box in original unscaled coordinates")
    source_image_ref: str = Field(..., description="Source image identifier or filename")
    associated_region_id: Optional[str] = Field(
        None,
        description="ID of enclosing DetectionRegion if localized within one, else None"
    )
    line_index: Optional[int] = Field(None, description="Sequential reading order line index")


class GlyphMeasurement(BaseModel):
    """Physical character height estimation for Legal Metrology font-size compliance."""
    block_id: str = Field(..., description="Associated OCRTextBlock block_id")
    text_snippet: str = Field(..., description="Extracted text snippet measured")
    estimated_glyph_height_px: float = Field(..., description="Estimated median font height in pixels (not box height)")
    estimated_glyph_height_mm: Optional[float] = Field(
        None,
        description="Estimated glyph height in millimeters (requires optical calibration)"
    )
    uncertainty_mm: Optional[float] = Field(
        None,
        description="Estimated measurement uncertainty margin in millimeters (+/-)"
    )


class PhysicalMeasurementResult(BaseModel):
    """ArUco-based optical calibration and physical font dimension measurement status."""
    aruco_detected: bool = Field(False, description="True if an ArUco calibration marker was found in the scene")
    marker_id: Optional[int] = Field(None, description="Identified ArUco marker ID")
    marker_corners: Optional[List[Point2D]] = Field(None, description="Detected 4 corners of the reference marker")
    marker_size_specified_mm: Optional[float] = Field(
        None,
        description="Physical reference dimension of marker in mm (e.g. 20.0 mm)"
    )
    pixels_per_mm: Optional[float] = Field(
        None,
        description="Computed optical scale factor (pixels per physical millimeter)"
    )
    calibration_status: str = Field(
        "uncalibrated",
        description="Calibration state: 'calibrated', 'uncalibrated', 'perspective_skewed', or 'uncertain'"
    )
    glyph_measurements: List[GlyphMeasurement] = Field(
        default_factory=list,
        description="Character height estimates for text blocks"
    )
    measurement_warnings: List[str] = Field(
        default_factory=list,
        description="Uncertainty caveats, e.g. 'marker not on same plane as declaration label'"
    )


class CVEngineOutput(BaseModel):
    """
    Unified contract returned by the Computer Vision Engine to downstream modules
    (NLP Engine, Fusion Engine, Compliance Engine).
    """
    success: bool = Field(..., description="Overall CV processing success status")
    pipeline_version: str = Field("1.0.0", description="CV pipeline release version")
    metadata: ImageMetadata = Field(..., description="Image format and dimension attributes")
    quality: ImageQualityMetrics = Field(..., description="Image quality metrics and degradation flags")
    preprocessing: PreprocessingInfo = Field(..., description="Applied normalization and geometric transforms")
    detector: DetectorInfo = Field(..., description="Declaration region detector output")
    ocr_blocks: List[OCRTextBlock] = Field(default_factory=list, description="Extracted OCR text blocks")
    physical_measurements: PhysicalMeasurementResult = Field(
        default_factory=PhysicalMeasurementResult,
        description="Physical dimensions and optical calibration data"
    )
    processing_warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings encountered")
    errors: List[str] = Field(default_factory=list, description="Fatal errors encountered during processing")
