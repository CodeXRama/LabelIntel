"""
LabelIntel — Unit Tests for NLP Engine
Tests entity classification, regex parsing, normalization, and provenance tracking.
"""

import pytest
from engines.cv_engine.schemas import BoundingBox, OCRTextBlock, Point2D
from engines.nlp_engine.engine import NLPEngine, get_nlp_engine
from engines.nlp_engine.normalizers import (
    normalize_consumer_contact,
    normalize_date,
    normalize_fssai,
    normalize_mrp,
    normalize_net_quantity,
)
from engines.nlp_engine.schemas import DeclarationType


def test_normalize_mrp():
    # Test standard format with taxes
    mrp1 = normalize_mrp("MRP Rs. 150.00 (incl. of all taxes)")
    assert mrp1 is not None
    assert mrp1.amount == 150.0
    assert mrp1.is_inclusive_of_taxes is True
    assert mrp1.currency == "INR"

    # Test Rupee symbol format
    mrp2 = normalize_mrp("M.R.P. ₹ 85.50")
    assert mrp2 is not None
    assert mrp2.amount == 85.50
    assert mrp2.is_inclusive_of_taxes is False

    # Test with Unit Sale Price
    mrp3 = normalize_mrp("MRP: ₹ 120.00 (Rs. 1.20/g)")
    assert mrp3 is not None
    assert mrp3.amount == 120.0
    assert mrp3.unit_price == 1.20

    # Test non-price string
    assert normalize_mrp("Keep away from sunlight") is None


def test_normalize_net_quantity():
    # Test grams
    q1 = normalize_net_quantity("Net Wt.: 500 g")
    assert q1 is not None
    assert q1.value == 500.0
    assert q1.unit == "g"
    assert q1.standard_value == 500.0
    assert q1.standard_unit == "g"

    # Test kilograms conversion
    q2 = normalize_net_quantity("Net Quantity: 1.5 kg")
    assert q2 is not None
    assert q2.value == 1.5
    assert q2.unit == "kg"
    assert q2.standard_value == 1500.0
    assert q2.standard_unit == "g"

    # Test volume in litres
    q3 = normalize_net_quantity("Net Volume: 1 Litre")
    assert q3 is not None
    assert q3.value == 1.0
    assert q3.unit == "l"
    assert q3.standard_value == 1000.0
    assert q3.standard_unit == "ml"

    # Test volume in millilitres
    q4 = normalize_net_quantity("250 ml")
    assert q4 is not None
    assert q4.value == 250.0
    assert q4.unit == "ml"
    assert q4.standard_value == 250.0
    assert q4.standard_unit == "ml"


def test_normalize_date():
    # Full date DD/MM/YYYY
    d1 = normalize_date("MFG: 15/08/2026")
    assert d1 is not None
    assert d1.day == 15
    assert d1.month == 8
    assert d1.year == 2026
    assert d1.iso_date == "2026-08-15"

    # Month-Year MM/YYYY
    d2 = normalize_date("EXP: 11/2027", context_type="expiry")
    assert d2 is not None
    assert d2.month == 11
    assert d2.year == 2027
    assert d2.iso_date == "2027-11"

    # Named Month
    d3 = normalize_date("Packed: OCT 2026")
    assert d3 is not None
    assert d3.month == 10
    assert d3.year == 2026

    # Shelf life period
    d4 = normalize_date("BEST BEFORE 12 MONTHS FROM PACKAGING")
    assert d4 is not None
    assert d4.date_type == "best_before"
    assert d4.shelf_life_months == 12


def test_normalize_fssai():
    # Valid 14 digit
    f1 = normalize_fssai("fssai Lic. No. 10012022000277")
    assert f1 is not None
    assert f1.license_number == "10012022000277"
    assert f1.is_valid_format is True

    # Invalid non-14 digit
    assert normalize_fssai("No license found here") is None


def test_normalize_consumer_contact():
    c1 = normalize_consumer_contact("Consumer Care: care@brand.com")
    assert c1 is not None
    assert c1.contact_type == "email"
    assert c1.value == "care@brand.com"

    c2 = normalize_consumer_contact("Toll Free: 1800-200-1234")
    assert c2 is not None
    assert c2.contact_type == "phone"
    assert c2.value == "18002001234"


def test_nlp_engine_declarations_extraction():
    engine = get_nlp_engine()

    dummy_poly = [
        Point2D(x=10.0, y=10.0),
        Point2D(x=100.0, y=10.0),
        Point2D(x=100.0, y=30.0),
        Point2D(x=10.0, y=30.0),
    ]
    dummy_bbox = BoundingBox(x_min=10.0, y_min=10.0, x_max=100.0, y_max=30.0)

    blocks = [
        OCRTextBlock(
            block_id="ocr_001",
            text="MRP Rs. 99.00 (inclusive of all taxes)",
            confidence=0.98,
            polygon=dummy_poly,
            bounding_box=dummy_bbox,
            source_image_ref="sample.jpg",
        ),
        OCRTextBlock(
            block_id="ocr_002",
            text="Net Wt: 400 g",
            confidence=0.99,
            polygon=dummy_poly,
            bounding_box=dummy_bbox,
            source_image_ref="sample.jpg",
        ),
        OCRTextBlock(
            block_id="ocr_003",
            text="Mfg Date: 05/2026",
            confidence=0.95,
            polygon=dummy_poly,
            bounding_box=dummy_bbox,
            source_image_ref="sample.jpg",
        ),
        OCRTextBlock(
            block_id="ocr_004",
            text="Manufactured by: ABC Foods Ltd, Mumbai",
            confidence=0.94,
            polygon=dummy_poly,
            bounding_box=dummy_bbox,
            source_image_ref="sample.jpg",
        ),
        OCRTextBlock(
            block_id="ocr_005",
            text="Customer Care: care@abcfoods.in",
            confidence=0.96,
            polygon=dummy_poly,
            bounding_box=dummy_bbox,
            source_image_ref="sample.jpg",
        ),
        OCRTextBlock(
            block_id="ocr_006",
            text="Just some promotional slogans here",
            confidence=0.90,
            polygon=dummy_poly,
            bounding_box=dummy_bbox,
            source_image_ref="sample.jpg",
        ),
    ]

    result = engine.extract_declarations(blocks)
    assert result.total_entities_detected == 5
    assert DeclarationType.MRP in result.detected_declaration_types
    assert DeclarationType.NET_QUANTITY in result.detected_declaration_types
    assert DeclarationType.MFG_DATE in result.detected_declaration_types
    assert DeclarationType.MANUFACTURER in result.detected_declaration_types
    assert DeclarationType.CONSUMER_CARE in result.detected_declaration_types
    assert len(result.missing_mandatory_fields) == 0

    # Verify provenance
    mrp_ent = next(e for e in result.entities if e.declaration_type == DeclarationType.MRP)
    assert mrp_ent.source_ocr_block_ids == ["ocr_001"]
    assert mrp_ent.normalized_data["amount"] == 99.0
    assert mrp_ent.normalized_data["is_inclusive_of_taxes"] is True
