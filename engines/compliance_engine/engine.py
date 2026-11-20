"""
LabelIntel — Compliance Engine Main Orchestrator
Aggregates deterministic heuristic rule evaluations into a consolidated, evidence-backed report.

All evaluated rules include explicit `source_status="unverified_reference"` citations
and cautious heuristic phrasing. These assessments do not constitute formal legal counsel.
"""

import time
from typing import List, Optional

from engines.compliance_engine.rules import (
    evaluate_consumer_care_rule,
    evaluate_date_rule,
    evaluate_fssai_rule,
    evaluate_manufacturer_rule,
    evaluate_mrp_rule,
    evaluate_net_quantity_rule,
)
from engines.compliance_engine.schemas import (
    ComplianceStatus,
    FieldComplianceAssessment,
    OverallComplianceReport,
)
from engines.fusion.schemas import FusedDeclaration, FusionInspectionResult


class ComplianceEngine:
    """
    Evaluates fused declarations against Legal Metrology and FSSAI rules.
    """

    def evaluate_compliance(
        self,
        fused_result: FusionInspectionResult,
        category_hint: Optional[str] = None,
    ) -> OverallComplianceReport:
        t0 = time.perf_counter()
        decls: List[FusedDeclaration] = fused_result.declarations
        weak_ocr = not decls or len(fused_result.unfused_ocr_block_ids) > 0 and len(decls) < 4

        assessments: List[FieldComplianceAssessment] = [
            evaluate_mrp_rule(decls),
            evaluate_net_quantity_rule(decls),
            evaluate_manufacturer_rule(decls),
            evaluate_date_rule(decls),
            evaluate_consumer_care_rule(decls),
            evaluate_fssai_rule(decls, category_hint=category_hint),
        ]

        # A weak extraction makes absence claims unreliable. Downgrade any
        # missing-field failure to review instead of asserting non-compliance.
        if weak_ocr:
            for assessment in assessments:
                if assessment.status == ComplianceStatus.NON_COMPLIANT:
                    assessment.status = ComplianceStatus.FLAGGED_FOR_REVIEW
                    assessment.findings = [
                        "OCR coverage is incomplete; this image cannot establish that the required declaration is absent."
                    ] + assessment.findings

        # Compute summary counts
        comp_count = sum(1 for a in assessments if a.status == ComplianceStatus.COMPLIANT)
        non_comp_count = sum(1 for a in assessments if a.status == ComplianceStatus.NON_COMPLIANT)
        flagged_count = sum(1 for a in assessments if a.status == ComplianceStatus.FLAGGED_FOR_REVIEW)

        # Conservative overall status
        if non_comp_count > 0:
            overall_status = ComplianceStatus.NON_COMPLIANT
        elif flagged_count > 0:
            overall_status = ComplianceStatus.FLAGGED_FOR_REVIEW
        else:
            overall_status = ComplianceStatus.COMPLIANT

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return OverallComplianceReport(
            overall_status=overall_status,
            total_rules_evaluated=len(assessments),
            compliant_count=comp_count,
            non_compliant_count=non_comp_count,
            flagged_count=flagged_count,
            assessments=assessments,
            evaluation_time_ms=round(elapsed_ms, 2),
        )


_compliance_engine_instance: Optional[ComplianceEngine] = None


def get_compliance_engine() -> ComplianceEngine:
    global _compliance_engine_instance
    if _compliance_engine_instance is None:
        _compliance_engine_instance = ComplianceEngine()
    return _compliance_engine_instance
