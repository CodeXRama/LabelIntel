"""
LabelIntel — Fusion Engine Package
"""

from engines.fusion.schemas import FusedDeclaration, FusionInspectionResult
from engines.fusion.fusion_engine import EvidenceFusionEngine, get_fusion_engine

__all__ = [
    "FusedDeclaration",
    "FusionInspectionResult",
    "EvidenceFusionEngine",
    "get_fusion_engine",
]
