"""
LabelIntel — Statutory Compliance Rule Implementations
Deterministic rule checks for Legal Metrology (Packaged Commodities) Rules, 2011
and FSSAI (Labelling and Display) Regulations, 2020.
"""

from typing import List, Optional
from engines.compliance_engine.schemas import (
    ComplianceStatus,
    FieldComplianceAssessment,
    RuleProvenance,
)
from engines.fusion.schemas import FusedDeclaration, FusionInspectionResult
from engines.nlp_engine.schemas import DeclarationType


# Static Statutory Rule Definitions
RULE_LM_MRP = RuleProvenance(
    rule_id="LM-2011-RULE-06-1-C",
    statute_name="Legal Metrology (Packaged Commodities) Rules, 2011",
    rule_reference="Rule 6(1)(c)",
    title="Retail Sale Price (MRP) Declaration",
    summary="Retail sale price shall be declared as 'Maximum Retail Price' or 'MRP' inclusive of all taxes.",
)

RULE_LM_NET_QTY = RuleProvenance(
    rule_id="LM-2011-RULE-06-1-B",
    statute_name="Legal Metrology (Packaged Commodities) Rules, 2011",
    rule_reference="Rule 6(1)(b) & Rule 11",
    title="Net Quantity in Standard Units",
    summary="Net quantity shall be declared in terms of standard metric units (g, kg, ml, l) or numerical count.",
)

RULE_LM_MANUFACTURER = RuleProvenance(
    rule_id="LM-2011-RULE-06-1-A",
    statute_name="Legal Metrology (Packaged Commodities) Rules, 2011",
    rule_reference="Rule 6(1)(a)",
    title="Manufacturer / Packer Identity & Address",
    summary="The name and complete physical address of the manufacturer, packer, or importer must be clearly declared.",
)

RULE_LM_DATE = RuleProvenance(
    rule_id="LM-2011-RULE-06-1-D",
    statute_name="Legal Metrology (Packaged Commodities) Rules, 2011",
    rule_reference="Rule 6(1)(d)",
    title="Month and Year of Manufacture / Packing",
    summary="Month and year in which the commodity is manufactured, packed, or imported must be stated.",
)

RULE_LM_CONSUMER_CARE = RuleProvenance(
    rule_id="LM-2011-RULE-06-1-F",
    statute_name="Legal Metrology (Packaged Commodities) Rules, 2011",
    rule_reference="Rule 6(1)(f)",
    title="Consumer Care Grievance Redressal Mechanism",
    summary="Name, address, telephone number, or email address of the consumer care contact must be provided.",
)

RULE_FSSAI_LICENSE = RuleProvenance(
    rule_id="FSSAI-2020-REG-05-4",
    statute_name="FSSAI (Labelling and Display) Regulations, 2020",
    rule_reference="Regulation 5(4)",
    title="FSSAI Logo and 14-Digit License / Registration",
    summary="Every food package shall carry the FSSAI logo and 14-digit license number of the manufacturing / marketing unit.",
)


def evaluate_mrp_rule(declarations: List[FusedDeclaration]) -> FieldComplianceAssessment:
    """Evaluates compliance with Rule 6(1)(c) — MRP."""
    mrp_decls = [d for d in declarations if d.declaration_type == DeclarationType.MRP]

    if not mrp_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_lm_mrp",
            rule=RULE_LM_MRP,
            status=ComplianceStatus.NON_COMPLIANT,
            findings=["No Maximum Retail Price (MRP) declaration detected in visible OCR text."],
            cautions_and_recommendations=[
                "Statutory violation under Rule 6(1)(c). Ensure MRP is legibly printed with 'inclusive of all taxes'."
            ],
        )

    decl = mrp_decls[0]
    norm = decl.normalized_data or {}
    amount = norm.get("amount")
    is_inclusive = norm.get("is_inclusive_of_taxes", False)

    findings = [f"Detected MRP: {decl.raw_text} (Extracted Amount: ₹{amount})."]
    recommendations = []
    status = ComplianceStatus.COMPLIANT

    if not is_inclusive:
        findings.append("Mandatory phrase 'inclusive of all taxes' or 'incl. of all taxes' was not clearly verified.")
        recommendations.append("Verify packaging explicitly includes the statutory 'incl. of all taxes' text.")
        status = ComplianceStatus.FLAGGED_FOR_REVIEW

    if decl.combined_confidence < 0.80:
        findings.append(f"Low OCR confidence ({decl.combined_confidence:.2f}) on price text.")
        recommendations.append("Inspect physical package directly to confirm numeral clarity.")
        status = ComplianceStatus.FLAGGED_FOR_REVIEW

    return FieldComplianceAssessment(
        assessment_id="eval_lm_mrp",
        rule=RULE_LM_MRP,
        status=status,
        evidence_declaration_id=decl.declaration_id,
        findings=findings,
        cautions_and_recommendations=recommendations,
    )


def evaluate_net_quantity_rule(declarations: List[FusedDeclaration]) -> FieldComplianceAssessment:
    """Evaluates compliance with Rule 6(1)(b) — Net Quantity."""
    qty_decls = [d for d in declarations if d.declaration_type == DeclarationType.NET_QUANTITY]

    if not qty_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_lm_net_qty",
            rule=RULE_LM_NET_QTY,
            status=ComplianceStatus.NON_COMPLIANT,
            findings=["No Net Quantity declaration detected on evaluated packaging surface."],
            cautions_and_recommendations=[
                "Rule 6(1)(b) mandates clear net quantity declaration in standard SI units (g, kg, ml, l)."
            ],
        )

    decl = qty_decls[0]
    norm = decl.normalized_data or {}
    unit = norm.get("unit")
    val = norm.get("value")

    status = ComplianceStatus.COMPLIANT
    findings = [f"Detected Net Quantity: {decl.raw_text} (Normalized: {val} {unit})."]
    recs = []

    if unit not in ("g", "kg", "ml", "l", "units"):
        findings.append(f"Non-standard or unverified metric unit '{unit}'.")
        recs.append("Ensure unit strictly conforms to Schedule II standard metric designations.")
        status = ComplianceStatus.FLAGGED_FOR_REVIEW

    return FieldComplianceAssessment(
        assessment_id="eval_lm_net_qty",
        rule=RULE_LM_NET_QTY,
        status=status,
        evidence_declaration_id=decl.declaration_id,
        findings=findings,
        cautions_and_recommendations=recs,
    )


def evaluate_manufacturer_rule(declarations: List[FusedDeclaration]) -> FieldComplianceAssessment:
    """Evaluates compliance with Rule 6(1)(a) — Manufacturer."""
    mfg_decls = [d for d in declarations if d.declaration_type in (DeclarationType.MANUFACTURER, DeclarationType.PACKER)]

    if not mfg_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_lm_mfg",
            rule=RULE_LM_MANUFACTURER,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            findings=["No explicit 'Manufactured by' or 'Packed by' entity found on this panel."],
            cautions_and_recommendations=[
                "Verify whether manufacturer address is declared on another face of the package."
            ],
        )

    decl = mfg_decls[0]
    return FieldComplianceAssessment(
        assessment_id="eval_lm_mfg",
        rule=RULE_LM_MANUFACTURER,
        status=ComplianceStatus.COMPLIANT,
        evidence_declaration_id=decl.declaration_id,
        findings=[f"Identified entity: {decl.raw_text}."],
        cautions_and_recommendations=[],
    )


def evaluate_date_rule(declarations: List[FusedDeclaration]) -> FieldComplianceAssessment:
    """Evaluates compliance with Rule 6(1)(d) — Manufacturing / Expiry Date."""
    date_decls = [
        d for d in declarations
        if d.declaration_type in (DeclarationType.MFG_DATE, DeclarationType.EXPIRY_DATE, DeclarationType.BEST_BEFORE)
    ]

    if not date_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_lm_date",
            rule=RULE_LM_DATE,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            findings=["No manufacturing date, packing date, or best-before period detected on this surface."],
            cautions_and_recommendations=[
                "Check for ink-jet stamped or embossed date on package bottom, rim, or seal flap."
            ],
        )

    decl = date_decls[0]
    return FieldComplianceAssessment(
        assessment_id="eval_lm_date",
        rule=RULE_LM_DATE,
        status=ComplianceStatus.COMPLIANT,
        evidence_declaration_id=decl.declaration_id,
        findings=[f"Detected date declaration: {decl.raw_text}."],
        cautions_and_recommendations=[],
    )


def evaluate_consumer_care_rule(declarations: List[FusedDeclaration]) -> FieldComplianceAssessment:
    """Evaluates compliance with Rule 6(1)(f) — Consumer Care."""
    care_decls = [d for d in declarations if d.declaration_type == DeclarationType.CONSUMER_CARE]

    if not care_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_lm_care",
            rule=RULE_LM_CONSUMER_CARE,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            findings=["Consumer care helpline or email was not detected in this image view."],
            cautions_and_recommendations=[
                "Rule 6(1)(f) mandates consumer care contact. Check alternate faces of the package."
            ],
        )

    decl = care_decls[0]
    return FieldComplianceAssessment(
        assessment_id="eval_lm_care",
        rule=RULE_LM_CONSUMER_CARE,
        status=ComplianceStatus.COMPLIANT,
        evidence_declaration_id=decl.declaration_id,
        findings=[f"Consumer grievance channel identified: {decl.raw_text}."],
        cautions_and_recommendations=[],
    )


def evaluate_fssai_rule(
    declarations: List[FusedDeclaration],
    category_hint: Optional[str] = None,
) -> FieldComplianceAssessment:
    """Evaluates compliance with FSSAI regulations for food and beverage items."""
    is_food = category_hint in ("food", "beverages") if category_hint else False

    fssai_decls = [d for d in declarations if d.declaration_type == DeclarationType.FSSAI_LICENSE]

    if not is_food and not fssai_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_fssai_lic",
            rule=RULE_FSSAI_LICENSE,
            status=ComplianceStatus.NOT_APPLICABLE,
            findings=["Non-food category commodity; FSSAI license regulation is not applicable."],
            cautions_and_recommendations=[],
        )

    if not fssai_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_fssai_lic",
            rule=RULE_FSSAI_LICENSE,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            findings=["Food/beverage commodity identified, but 14-digit FSSAI license was not recognized."],
            cautions_and_recommendations=[
                "Verify whether FSSAI logo and 14-digit license are printed on the front or side display panel."
            ],
        )

    decl = fssai_decls[0]
    norm = decl.normalized_data or {}
    is_valid = norm.get("is_valid_format", False)

    if not is_valid:
        return FieldComplianceAssessment(
            assessment_id="eval_fssai_lic",
            rule=RULE_FSSAI_LICENSE,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            evidence_declaration_id=decl.declaration_id,
            findings=[f"FSSAI reference found ({decl.raw_text}), but format validation was inconclusive."],
            cautions_and_recommendations=["Inspect package to ensure complete 14-digit registration number."],
        )

    return FieldComplianceAssessment(
        assessment_id="eval_fssai_lic",
        rule=RULE_FSSAI_LICENSE,
        status=ComplianceStatus.COMPLIANT,
        evidence_declaration_id=decl.declaration_id,
        findings=[f"FSSAI 14-digit license verified: {norm.get('license_number')}."],
        cautions_and_recommendations=[],
    )
