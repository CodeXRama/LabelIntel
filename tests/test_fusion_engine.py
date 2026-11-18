"""
LabelIntel — Unit Tests for Fusion Engine
Tests OCR-to-NLP spatial and semantic evidence fusion.
"""

from engines.cv_engine.schemas import BoundingBox, OCRTextBlock, Point2D
from engines.fusion.fusion_engine import get_fusion_engine
from engines.nlp_engine.schemas import DeclarationType, ExtractedEntity, NLPInspectionResult


def test_evidence_fusion_mapping_and_envelopes():
    engine = get_fusion_engine()

    block1 = OCRTextBlock(
        block_id="ocr_101",
        text="MRP Rs. 250.00",
        confidence=0.96,
        polygon=[Point2D(x=50.0, y=100.0), Point2D(x=200.0, y=100.0), Point2D(x=200.0, y=140.0), Point2D(x=50.0, y=140.0)],
        bounding_box=BoundingBox(x_min=50.0, y_min=100.0, x_max=200.0, y_max=140.0),
        source_image_ref="sample_box.jpg",
    )
    block2 = OCRTextBlock(
        block_id="ocr_102",
        text="(incl. of all taxes)",
        confidence=0.94,
        polygon=[Point2D(x=52.0, y=145.0), Point2D(x=210.0, y=145.0), Point2D(x=210.0, y=170.0), Point2D(x=52.0, y=170.0)],
        bounding_box=BoundingBox(x_min=52.0, y_min=145.0, x_max=210.0, y_max=170.0),
        source_image_ref="sample_box.jpg",
    )
    block3 = OCRTextBlock(
        block_id="ocr_103",
        text="BRAND LOGO",
        confidence=0.99,
        polygon=[Point2D(x=10.0, y=10.0), Point2D(x=100.0, y=10.0), Point2D(x=100.0, y=50.0), Point2D(x=10.0, y=50.0)],
        bounding_box=BoundingBox(x_min=10.0, y_min=10.0, x_max=100.0, y_max=50.0),
        source_image_ref="sample_box.jpg",
    )

    nlp_result = NLPInspectionResult(
        total_entities_detected=1,
        entities=[
            ExtractedEntity(
                entity_id="ent_001",
                declaration_type=DeclarationType.MRP,
                raw_text="MRP Rs. 250.00 (incl. of all taxes)",
                confidence=0.95,
                source_ocr_block_ids=["ocr_101", "ocr_102"],
                normalized_data={"amount": 250.0, "currency": "INR", "is_inclusive_of_taxes": True},
            )
        ],
        detected_declaration_types=[DeclarationType.MRP],
        missing_mandatory_fields=[],
    )

    fusion_res = engine.fuse(
        ocr_blocks=[block1, block2, block3],
        nlp_result=nlp_result,
        source_image_ref="sample_box.jpg",
    )

    assert fusion_res.total_declarations == 1
    decl = fusion_res.declarations[0]
    assert decl.declaration_type == DeclarationType.MRP
    assert decl.display_title == "Maximum Retail Price (MRP)"
    assert len(decl.evidence_ocr_blocks) == 2

    # Envelope must span min to max of both blocks
    assert decl.bounding_box.x_min == 50.0
    assert decl.bounding_box.y_min == 100.0
    assert decl.bounding_box.x_max == 210.0
    assert decl.bounding_box.y_max == 170.0

    # block3 should remain unfused
    assert "ocr_103" in fusion_res.unfused_ocr_block_ids
    assert "ocr_101" not in fusion_res.unfused_ocr_block_ids
