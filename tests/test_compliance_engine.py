"""
LabelIntel — Unit Tests for Compliance Engine
Tests deterministic rule evaluations, cautious classifications, and legal provenance.
"""

from engines.compliance_engine.engine import get_compliance_engine
from engines.compliance_engine.schemas import ComplianceStatus
from engines.cv_engine.schemas import BoundingBox, Point2D
from engines.fusion.schemas import FusedDeclaration, FusionInspectionResult
from engines.nlp_engine.schemas import DeclarationType


def make_dummy_decl(
    decl_id: str,
    decl_type: DeclarationType,
    raw_text: str,
    normalized: dict,
    confidence: float = 0.95,
) -> FusedDeclaration:
    bbox = BoundingBox(x_min=10.0, y_min=10.0, x_max=100.0, y_max=50.0)
    poly = [Point2D(x=10.0, y=10.0), Point2D(x=100.0, y=10.0), Point2D(x=100.0, y=50.0), Point2D(x=10.0, y=50.0)]
    return FusedDeclaration(
        declaration_id=decl_id,
        declaration_type=decl_type,
        display_title="Test Decl",
        raw_text=raw_text,
        normalized_data=normalized,
        combined_confidence=confidence,
        evidence_ocr_blocks=[],
        bounding_box=bbox,
        polygon=poly,
    )


def test_compliance_all_mandatory_satisfied():
    engine = get_compliance_engine()

    decls = [
        make_dummy_decl("d1", DeclarationType.MRP, "MRP Rs. 100 (incl. of all taxes)", {"amount": 100.0, "is_inclusive_of_taxes": True}),
        make_dummy_decl("d2", DeclarationType.NET_QUANTITY, "Net Wt: 500 g", {"value": 500.0, "unit": "g"}),
        make_dummy_decl("d3", DeclarationType.MANUFACTURER, "Manufactured by XYZ Ltd", {}),
        make_dummy_decl("d4", DeclarationType.MFG_DATE, "Mfg: 12/2026", {"month": 12, "year": 2026}),
        make_dummy_decl("d5", DeclarationType.CONSUMER_CARE, "Customer Care: 1800-111-222", {"value": "1800111222"}),
    ]

    fusion_res = FusionInspectionResult(
        source_image="test.jpg",
        total_declarations=len(decls),
        declarations=decls,
        unfused_ocr_block_ids=[],
    )

    report = engine.evaluate_compliance(fusion_res, category_hint="household")
    assert report.non_compliant_count == 0
    # For household, FSSAI is not applicable
    assert any(a.rule.rule_id == "LM-2011-RULE-06-1-C" and a.status == ComplianceStatus.COMPLIANT for a in report.assessments)
    assert any(a.rule.rule_id == "LM-2011-RULE-06-1-B" and a.status == ComplianceStatus.COMPLIANT for a in report.assessments)
    assert any(a.rule.rule_id == "FSSAI-2020-REG-05-4" and a.status == ComplianceStatus.NOT_APPLICABLE for a in report.assessments)
    assert "DISCLAIMER" in report.legal_disclaimer


def test_compliance_missing_mrp_violates_rule():
    engine = get_compliance_engine()

    # Net quantity only, no MRP
    decls = [
        make_dummy_decl("d2", DeclarationType.NET_QUANTITY, "Net Wt: 500 g", {"value": 500.0, "unit": "g"}),
    ]

    fusion_res = FusionInspectionResult(
        source_image="test.jpg",
        total_declarations=len(decls),
        declarations=decls,
        unfused_ocr_block_ids=[],
    )

    report = engine.evaluate_compliance(fusion_res)
    assert report.non_compliant_count >= 1
    mrp_eval = next(a for a in report.assessments if a.rule.rule_id == "LM-2011-RULE-06-1-C")
    assert mrp_eval.status == ComplianceStatus.NON_COMPLIANT
    assert report.overall_status == ComplianceStatus.NON_COMPLIANT


def test_compliance_mrp_without_inclusive_of_taxes_is_flagged():
    engine = get_compliance_engine()

    # MRP present but is_inclusive_of_taxes is False
    decls = [
        make_dummy_decl("d1", DeclarationType.MRP, "MRP Rs. 100", {"amount": 100.0, "is_inclusive_of_taxes": False}),
        make_dummy_decl("d2", DeclarationType.NET_QUANTITY, "Net Wt: 500 g", {"value": 500.0, "unit": "g"}),
    ]

    fusion_res = FusionInspectionResult(
        source_image="test.jpg",
        total_declarations=len(decls),
        declarations=decls,
        unfused_ocr_block_ids=[],
    )

    report = engine.evaluate_compliance(fusion_res)
    mrp_eval = next(a for a in report.assessments if a.rule.rule_id == "LM-2011-RULE-06-1-C")
    assert mrp_eval.status == ComplianceStatus.FLAGGED_FOR_REVIEW
