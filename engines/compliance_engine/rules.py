"""
LabelIntel — Compliance Rule Implementations
Deterministic heuristic checks based on Legal Metrology (Packaged Commodities) Rules, 2011
and FSSAI (Labelling and Display) Regulations, 2020.

PROVENANCE SAFETY AND HEURISTIC NOTICE:
These checks provide automated, visual-semantic heuristic evaluations for packaging triage.
Statutory references are provided as unverified references (`source_status="unverified_reference"`)
to standard packaging conventions and are NOT authoritative legal determinations.
"""

import re
from typing import List, Optional
from engines.compliance_engine.schemas import (
    ComplianceStatus,
    FieldComplianceAssessment,
    RuleProvenance,
)
from engines.fusion.schemas import FusedDeclaration
from engines.nlp_engine.schemas import DeclarationType


# Static Heuristic Rule Definitions with Unverified Reference Status
RULE_LM_MRP = RuleProvenance(
    rule_id="LM-2011-RULE-06-1-C",
    statute_name="Legal Metrology (Packaged Commodities) Rules, 2011",
    rule_reference="Rule 6(1)(c)",
    title="Retail Sale Price (MRP) Declaration",
    summary="Retail sale price declaration (MRP) including tax status statement.",
    source_status="unverified_reference",
)

RULE_LM_NET_QTY = RuleProvenance(
    rule_id="LM-2011-RULE-06-1-B",
    statute_name="Legal Metrology (Packaged Commodities) Rules, 2011",
    rule_reference="Rule 6(1)(b) & Rule 11",
    title="Net Quantity in Standard Units",
    summary="Net quantity declaration in standard metric units (g, kg, ml, l) or numerical count.",
    source_status="unverified_reference",
)

RULE_LM_MANUFACTURER = RuleProvenance(
    rule_id="LM-2011-RULE-06-1-A",
    statute_name="Legal Metrology (Packaged Commodities) Rules, 2011",
    rule_reference="Rule 6(1)(a)",
    title="Manufacturer / Packer Identity & Address",
    summary="Name and address declaration of the manufacturer, packer, or importer.",
    source_status="unverified_reference",
)

RULE_LM_DATE = RuleProvenance(
    rule_id="LM-2011-RULE-06-1-D",
    statute_name="Legal Metrology (Packaged Commodities) Rules, 2011",
    rule_reference="Rule 6(1)(d)",
    title="Month and Year of Manufacture / Packing",
    summary="Month and year of manufacture, packing, or import declaration.",
    source_status="unverified_reference",
)

RULE_LM_CONSUMER_CARE = RuleProvenance(
    rule_id="LM-2011-RULE-06-1-F",
    statute_name="Legal Metrology (Packaged Commodities) Rules, 2011",
    rule_reference="Rule 6(1)(f)",
    title="Consumer Care Grievance Redressal Mechanism",
    summary="Consumer care contact channel (address, telephone, or email).",
    source_status="unverified_reference",
)

RULE_FSSAI_LICENSE = RuleProvenance(
    rule_id="FSSAI-2020-REG-05-4",
    statute_name="FSSAI (Labelling and Display) Regulations, 2020",
    rule_reference="Regulation 5(4)",
    title="FSSAI Logo and 14-Digit License / Registration",
    summary="FSSAI logo and 14-digit registration/license declaration for food items.",
    source_status="unverified_reference",
)


def evaluate_mrp_rule(declarations: List[FusedDeclaration]) -> FieldComplianceAssessment:
    """Evaluates presence and clarity of Retail Sale Price (MRP) declaration."""
    mrp_decls = [d for d in declarations if d.declaration_type == DeclarationType.MRP]

    if not mrp_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_lm_mrp",
            rule=RULE_LM_MRP,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            findings=["MRP was not detected by OCR on this image; this does not establish that the package omits it."],
            cautions_and_recommendations=[
                "MRP declaration not detected under automated heuristic evaluation. Verify whether retail sale price is printed on another panel with 'inclusive of all taxes'."
            ],
        )

    decl = mrp_decls[0]
    norm = decl.normalized_data or {}
    amount = norm.get("amount")
    is_inclusive = norm.get("is_inclusive_of_taxes", False)

    if amount is None:
        return FieldComplianceAssessment(
            assessment_id="eval_lm_mrp",
            rule=RULE_LM_MRP,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            evidence_declaration_id=decl.declaration_id,
            findings=[f"MRP-like text was detected ({decl.raw_text}), but a readable price amount was not extracted."],
            cautions_and_recommendations=["Inspect the printed price and tax statement directly; an OCR label alone is not evidence of a complete declaration."],
        )

    findings = [f"Detected MRP: {decl.raw_text} (Extracted Amount: ₹{amount})."]
    recommendations = []
    status = ComplianceStatus.COMPLIANT

    if not is_inclusive:
        findings.append("Phrase 'inclusive of all taxes' or 'incl. of all taxes' was not detected in visible OCR text.")
        recommendations.append("Verify packaging explicitly includes the expected 'incl. of all taxes' statement.")
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
    """Evaluates presence and metric units of Net Quantity declaration."""
    qty_decls = [d for d in declarations if d.declaration_type == DeclarationType.NET_QUANTITY]

    if not qty_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_lm_net_qty",
            rule=RULE_LM_NET_QTY,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            findings=["Net quantity was not detected by OCR on this image; verify the visible package directly."],
            cautions_and_recommendations=[
                "Net quantity was not detected under automated heuristic check. Guidelines typically expect standard metric units (g, kg, ml, l, units)."
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
        recs.append("Unit could not be verified against standard metric designations (g, kg, ml, l, units). Check package manually.")
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
    """Evaluates presence of Manufacturer or Packer declaration."""
    mfg_decls = [d for d in declarations if d.declaration_type in (DeclarationType.MANUFACTURER, DeclarationType.PACKER)]

    if not mfg_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_lm_mfg",
            rule=RULE_LM_MANUFACTURER,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            findings=["No explicit 'Manufactured by' or 'Packed by' entity detected on this panel."],
            cautions_and_recommendations=[
                "Manufacturer or packer details not detected on this surface. Verify whether manufacturer address is declared on another face of the package."
            ],
        )

    decl = mfg_decls[0]
    entity_text = re.sub(
        r"^\s*(?:(?:manufactured|marketed|produced|packed|mfg\.?|imported)\s+by)\s*[:\-]?\s*",
        "",
        decl.raw_text,
        flags=re.IGNORECASE,
    ).strip(" :,-.")
    if not re.search(r"[A-Za-z]{2,}", entity_text):
        return FieldComplianceAssessment(
            assessment_id="eval_lm_mfg",
            rule=RULE_LM_MANUFACTURER,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            evidence_declaration_id=decl.declaration_id,
            findings=["A manufacturer/packer label was detected, but a readable business name was not extracted."],
            cautions_and_recommendations=["Verify the printed business name and full address on the package."],
        )

    has_address_signal = bool(
        re.search(r"\b\d{6}\b", entity_text)
        or re.search(r"\b(?:road|street|sector|village|district|floor|plot|phase|nagar)\b", entity_text, re.IGNORECASE)
    )
    return FieldComplianceAssessment(
        assessment_id="eval_lm_mfg",
        rule=RULE_LM_MANUFACTURER,
        status=ComplianceStatus.COMPLIANT if has_address_signal else ComplianceStatus.FLAGGED_FOR_REVIEW,
        evidence_declaration_id=decl.declaration_id,
        findings=[f"Detected business name text: {entity_text}."],
        cautions_and_recommendations=[] if has_address_signal else ["A business name was detected, but a complete address could not be confirmed from this OCR evidence."],
    )


def evaluate_date_rule(declarations: List[FusedDeclaration]) -> FieldComplianceAssessment:
    """Evaluates presence of Manufacturing, Expiry, or Best Before date declaration."""
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
                "Date declaration not detected in this view. Check for ink-jet stamped, embossed, or seal flap date codes."
            ],
        )

    decl = date_decls[0]
    norm = decl.normalized_data or {}
    if not (norm.get("iso_date") or norm.get("shelf_life_months")):
        return FieldComplianceAssessment(
            assessment_id="eval_lm_date",
            rule=RULE_LM_DATE,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            evidence_declaration_id=decl.declaration_id,
            findings=[f"A date label was detected ({decl.raw_text}), but no readable date or shelf-life value was extracted."],
            cautions_and_recommendations=["Check the inkjet, seal, or printed date value directly; a label alone does not confirm the declaration."],
        )
    return FieldComplianceAssessment(
        assessment_id="eval_lm_date",
        rule=RULE_LM_DATE,
        status=ComplianceStatus.COMPLIANT,
        evidence_declaration_id=decl.declaration_id,
        findings=[f"Detected date declaration: {decl.raw_text}."],
        cautions_and_recommendations=[],
    )


def evaluate_consumer_care_rule(declarations: List[FusedDeclaration]) -> FieldComplianceAssessment:
    """Evaluates presence of Consumer Care grievance contact information."""
    care_decls = [d for d in declarations if d.declaration_type == DeclarationType.CONSUMER_CARE]

    if not care_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_lm_care",
            rule=RULE_LM_CONSUMER_CARE,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            findings=["Consumer care helpline or email was not detected in this image view."],
            cautions_and_recommendations=[
                "Consumer care contact details not detected under automated heuristic evaluation. Check alternate faces of the package."
            ],
        )

    decl = care_decls[0]
    norm = decl.normalized_data or {}
    if not norm.get("value"):
        return FieldComplianceAssessment(
            assessment_id="eval_lm_care",
            rule=RULE_LM_CONSUMER_CARE,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            evidence_declaration_id=decl.declaration_id,
            findings=[f"A consumer-care label was detected ({decl.raw_text}), but no readable contact value was extracted."],
            cautions_and_recommendations=["Verify that a working contact channel is printed and legible."],
        )
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
    """Evaluates presence and format of FSSAI license declaration for food/beverage commodities."""
    is_food = category_hint in ("food", "beverages") if category_hint else False

    fssai_decls = [d for d in declarations if d.declaration_type == DeclarationType.FSSAI_LICENSE]

    if not is_food and not fssai_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_fssai_lic",
            rule=RULE_FSSAI_LICENSE,
            status=ComplianceStatus.NOT_APPLICABLE,
            findings=["Non-food category commodity; FSSAI license check is not applicable."],
            cautions_and_recommendations=[],
        )

    if not fssai_decls:
        return FieldComplianceAssessment(
            assessment_id="eval_fssai_lic",
            rule=RULE_FSSAI_LICENSE,
            status=ComplianceStatus.FLAGGED_FOR_REVIEW,
            findings=["Food/beverage commodity category indicated, but 14-digit FSSAI license was not recognized in visible OCR text."],
            cautions_and_recommendations=[
                "FSSAI license was not detected on this visible panel. Verify whether FSSAI logo and 14-digit registration appear on an alternate display panel."
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
            findings=[f"FSSAI reference found ({decl.raw_text}), but 14-digit format validation was inconclusive."],
            cautions_and_recommendations=["Inspect package directly to confirm complete 14-digit registration number."],
        )

    return FieldComplianceAssessment(
        assessment_id="eval_fssai_lic",
        rule=RULE_FSSAI_LICENSE,
        status=ComplianceStatus.COMPLIANT,
        evidence_declaration_id=decl.declaration_id,
        findings=[f"FSSAI 14-digit license verified: {norm.get('license_number')}."],
        cautions_and_recommendations=[],
    )
