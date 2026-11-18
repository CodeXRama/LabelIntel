"""
LabelIntel — Compliance Engine Package
Deterministic heuristic checks based on Legal Metrology and FSSAI packaging guidelines.

Statutory citations are provided for informational benchmarking only with `source_status="unverified_reference"`,
and must NOT be interpreted as formal legal advice or authoritative regulatory determinations.
"""

from engines.compliance_engine.schemas import (
    LEGAL_ADVICE_DISCLAIMER,
    ComplianceStatus,
    FieldComplianceAssessment,
    OverallComplianceReport,
    RuleProvenance,
)
from engines.compliance_engine.engine import ComplianceEngine, get_compliance_engine

__all__ = [
    "LEGAL_ADVICE_DISCLAIMER",
    "ComplianceStatus",
    "FieldComplianceAssessment",
    "OverallComplianceReport",
    "RuleProvenance",
    "ComplianceEngine",
    "get_compliance_engine",
]
