"""
LabelIntel — Computer Vision OCR Configuration
Defines runtime parameters, thresholds, and engine settings for PaddleOCR text detection
and recognition on CPU.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class CVOCRConfig(BaseModel):
    """Configuration parameters for PaddleOCR inference engine."""
    backend: Literal["rapidocr", "paddle"] = Field(
        "rapidocr",
        description="OCR runtime. RapidOCR/ONNX is the fast CPU path; PaddleOCR is the compatibility fallback.",
    )
    lang: str = Field("en", description="Target language code (e.g., 'en', 'ch')")
    ocr_version: str = Field("PP-OCRv4", description="PaddleOCR model version ('PP-OCRv4' or 'PP-OCRv6')")
    device: str = Field("cpu", description="Execution device: 'cpu' or 'gpu'")
    enable_mkldnn: bool = Field(
        False,
        description="Enable oneDNN/MKL-DNN acceleration. Must be False on Windows Paddle 3.3.1 CPU "
                    "to prevent PIR double-attribute conversion runtime exceptions."
    )
    use_textline_orientation: bool = Field(
        False,
        description="Whether to run textline direction classifier (PP-LCNet orientation model). Disabled for high-speed CPU inference."
    )
    use_doc_orientation_classify: bool = Field(
        False,
        description="Whether to execute whole-document orientation classifier"
    )
    use_doc_unwarping: bool = Field(
        False,
        description="Whether to execute document geometric unwarping (UVDoc)"
    )
    text_det_limit_side_len: int = Field(
        960,
        ge=320,
        le=4000,
        description="Max side length for detection image resizing"
    )
    text_recognition_batch_size: int = Field(
        16,
        ge=1,
        le=64,
        description="Batch size for text recognition inference"
    )
    text_det_thresh: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="DBNet pixel binarization probability threshold"
    )
    text_det_box_thresh: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="DBNet text box average probability score threshold"
    )
    text_rec_score_thresh: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Recognition score threshold within PaddleOCR pipeline (0.0 keeps all candidates)"
    )
    min_confidence_filter: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Post-parsing confidence filter threshold (defaults to 0.0 to avoid dropping statutory text)"
    )
    cpu_threads: int = Field(
        8,
        ge=1,
        le=32,
        description="Number of CPU computation threads allocated for inference"
    )
    rapidocr_max_side_len: int = Field(
        960,
        ge=320,
        le=2048,
        description="Maximum side length for the RapidOCR CPU frame.",
    )
