"""
LabelIntel — Computer Vision OCR Configuration
Defines runtime parameters, thresholds, and engine settings for PaddleOCR text detection
and recognition on CPU.
"""

from typing import Optional
from pydantic import BaseModel, Field


class CVOCRConfig(BaseModel):
    """Configuration parameters for PaddleOCR inference engine."""
    lang: str = Field("en", description="Target language code (e.g., 'en', 'ch')")
    device: str = Field("cpu", description="Execution device: 'cpu' or 'gpu'")
    enable_mkldnn: bool = Field(
        False,
        description="Enable oneDNN/MKL-DNN acceleration. Must be False on Windows Paddle 3.3.1 CPU "
                    "to prevent PIR double-attribute conversion runtime exceptions."
    )
    use_textline_orientation: bool = Field(
        True,
        description="Whether to run textline direction classifier (PP-LCNet orientation model)"
    )
    use_doc_orientation_classify: bool = Field(
        False,
        description="Whether to execute whole-document orientation classifier"
    )
    use_doc_unwarping: bool = Field(
        False,
        description="Whether to execute document geometric unwarping (UVDoc)"
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
        4,
        ge=1,
        le=32,
        description="Number of CPU computation threads allocated for inference"
    )
