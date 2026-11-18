"""
LabelIntel — Fusion Engine Schemas
Data structures linking extracted field entities with exact OCR visual evidence (polygons & bounding boxes).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from engines.cv_engine.schemas import BoundingBox, OCRTextBlock, Point2D
from engines.nlp_engine.schemas import DeclarationType, ExtractedEntity


class FusedDeclaration(BaseModel):
    """A semantic packaged commodity declaration bound directly to its visual bounding evidence."""
    declaration_id: str = Field(..., description="Unique identifier for this fused declaration")
    declaration_type: DeclarationType = Field(..., description="Semantic declaration category")
    display_title: str = Field(..., description="Human-readable title (e.g. 'Maximum Retail Price')")
    raw_text: str = Field(..., description="Original raw text span extracted")
    normalized_data: Optional[Dict[str, Any]] = Field(None, description="Normalized attributes (amount, date, qty, etc.)")
    combined_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score combining OCR and classification")
    evidence_ocr_blocks: List[OCRTextBlock] = Field(default_factory=list, description="Original OCR blocks providing visual evidence")
    bounding_box: BoundingBox = Field(..., description="Enclosing bounding box in original image coordinates")
    polygon: List[Point2D] = Field(..., description="4-point polygon enclosing the declaration in original coordinates")
    provenance_notes: List[str] = Field(default_factory=list, description="Audit trail and parsing provenance")


class FusionInspectionResult(BaseModel):
    """Comprehensive fused representation ready for compliance checks and visual rendering."""
    source_image: str = Field(..., description="Filename or path of evaluated image")
    total_declarations: int = Field(0, description="Count of successfully fused declarations")
    declarations: List[FusedDeclaration] = Field(default_factory=list, description="List of fused declarations")
    unfused_ocr_block_ids: List[str] = Field(default_factory=list, description="OCR block IDs not mapped to regulatory declarations")
    fusion_time_ms: float = Field(0.0, description="Fusion execution time in milliseconds")
