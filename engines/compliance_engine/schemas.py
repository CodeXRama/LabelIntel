"""
LabelIntel — Compliance Engine Schemas
Data contracts for deterministic regulatory assessments with statutory rule provenance.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

LEGAL_ADVICE_DISCLAIMER = (
    "DISCLAIMER: LabelIntel provides automated visual and semantic heuristic checks "
    "for quality assurance purposes only. This assessment does not constitute formal "
    "legal counsel, statutory verification, or official metrology certification. "
    "Regulatory compliance must be independently validated by authorized legal counsel "
    "or licensed Legal Metrology officers."
)


class ComplianceStatus(str, Enum):
    """Categorical compliance status with conservative grading."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    FLAGGED_FOR_REVIEW = "flagged_for_review"
    NOT_APPLICABLE = "not_applicable"


class RuleProvenance(BaseModel):
    """Explicit statutory reference and citation for each evaluated rule."""
    rule_id: str = Field(..., description="Unique internal rule identifier")
    statute_name: str = Field(..., description="Statute or regulatory code name")
    rule_reference: str = Field(..., description="Specific rule or section number")
    title: str = Field(..., description="Short descriptive title of the regulation")
    summary: str = Field(..., description="Summary of statutory requirement")


class FieldComplianceAssessment(BaseModel):
    """Individual rule evaluation outcome backed by visual evidence."""
    assessment_id: str = Field(..., description="Unique assessment ID")
    rule: RuleProvenance = Field(..., description="Statutory rule provenance")
    status: ComplianceStatus = Field(..., description="Evaluation outcome")
    evidence_declaration_id: Optional[str] = Field(None, description="Linked FusedDeclaration ID if evidence was found")
    findings: List[str] = Field(default_factory=list, description="Specific factual findings and observations")
    cautions_and_recommendations: List[str] = Field(default_factory=list, description="Recommended remediation or cautionary notes")
    cautious_disclaimer: str = Field(LEGAL_ADVICE_DISCLAIMER, description="Non-legal advice disclaimer")


class OverallComplianceReport(BaseModel):
    """Consolidated compliance report across all evaluated rules."""
    overall_status: ComplianceStatus = Field(..., description="Worst-case aggregate compliance status")
    total_rules_evaluated: int = Field(0, description="Total rules assessed")
    compliant_count: int = Field(0, description="Number of rules fully satisfied")
    non_compliant_count: int = Field(0, description="Number of rules violated")
    flagged_count: int = Field(0, description="Number of rules requiring manual verification")
    assessments: List[FieldComplianceAssessment] = Field(default_factory=list, description="Itemized assessments")
    legal_disclaimer: str = Field(LEGAL_ADVICE_DISCLAIMER, description="Prominent global legal disclaimer")
    evaluation_time_ms: float = Field(0.0, description="Compliance execution duration in ms")
