"""
LabelIntel — NLP Engine Schemas
Data models for text classification, entity extraction, and normalization of
packaged commodity declarations according to Indian Legal Metrology and FSSAI standards.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DeclarationType(str, Enum):
    """Canonical classification for packaged commodity declarations."""
    MRP = "mrp"
    NET_QUANTITY = "net_quantity"
    MFG_DATE = "mfg_date"
    EXPIRY_DATE = "expiry_date"
    BEST_BEFORE = "best_before"
    BATCH_NUMBER = "batch_number"
    MANUFACTURER = "manufacturer"
    PACKER = "packer"
    IMPORTER = "importer"
    CONSUMER_CARE = "consumer_care"
    INGREDIENTS = "ingredients"
    NUTRITION = "nutrition"
    COUNTRY_OF_ORIGIN = "country_of_origin"
    GENERIC_NAME = "generic_name"
    FSSAI_LICENSE = "fssai_license"
    CAUTION_WARNING = "caution_warning"
    OTHER = "other"


class NormalizedMRP(BaseModel):
    amount: float = Field(..., description="Numeric monetary value")
    currency: str = Field("INR", description="Currency code (e.g. INR)")
    is_inclusive_of_taxes: bool = Field(False, description="Whether 'inclusive of all taxes' was detected")
    unit_price: Optional[float] = Field(None, description="Unit sale price if specified (e.g. per g or ml)")
    raw_text: str = Field(..., description="Original raw text snippet")


class NormalizedNetQuantity(BaseModel):
    value: float = Field(..., description="Numeric quantity value")
    unit: str = Field(..., description="Detected unit (e.g. g, kg, ml, l, count)")
    standard_value: float = Field(..., description="Normalized value in base SI unit (g or ml or count)")
    standard_unit: str = Field(..., description="Base SI unit ('g', 'ml', or 'units')")
    raw_text: str = Field(..., description="Original raw text snippet")


class NormalizedDate(BaseModel):
    date_type: str = Field(..., description="'mfg', 'expiry', or 'best_before'")
    day: Optional[int] = Field(None, description="Calendar day if specified")
    month: Optional[int] = Field(None, description="Calendar month (1-12)")
    year: Optional[int] = Field(None, description="Calendar year (4 digits)")
    shelf_life_months: Optional[int] = Field(None, description="Shelf life period in months if duration-based")
    iso_date: Optional[str] = Field(None, description="ISO format date YYYY-MM or YYYY-MM-DD when complete")
    raw_text: str = Field(..., description="Original raw text snippet")


class NormalizedContact(BaseModel):
    contact_type: str = Field(..., description="'phone', 'email', 'address', or 'web'")
    value: str = Field(..., description="Extracted contact string")
    raw_text: str = Field(..., description="Original raw text snippet")


class NormalizedFSSAI(BaseModel):
    license_number: str = Field(..., description="14-digit FSSAI registration/license number")
    is_valid_format: bool = Field(..., description="Whether it satisfies the 14-digit numeric checksum/length")
    raw_text: str = Field(..., description="Original raw text snippet")


class ExtractedEntity(BaseModel):
    """An individual entity detected and classified from OCR text."""
    entity_id: str = Field(..., description="Unique entity identifier (e.g. ent_001)")
    declaration_type: DeclarationType = Field(..., description="Classified declaration category")
    raw_text: str = Field(..., description="Exact raw text span extracted")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction / classification confidence")
    source_ocr_block_ids: List[str] = Field(default_factory=list, description="IDs of CV OCR blocks contributing to this entity")
    normalized_data: Optional[Dict[str, Any]] = Field(None, description="Structured parsed representation")
    parsing_notes: List[str] = Field(default_factory=list, description="Parser heuristics or observations")


class NLPInspectionResult(BaseModel):
    """Aggregate output of the NLP analysis over all text declarations."""
    total_entities_detected: int = Field(0, description="Total count of recognized entities")
    entities: List[ExtractedEntity] = Field(default_factory=list, description="List of all extracted entities")
    detected_declaration_types: List[DeclarationType] = Field(default_factory=list, description="Unique categories found")
    missing_mandatory_fields: List[DeclarationType] = Field(default_factory=list, description="Mandatory declarations not found")
    extraction_time_ms: float = Field(0.0, description="Processing duration in milliseconds")
