"""
LabelIntel — NLP Engine Main Orchestrator
Processes OCR text blocks to extract, classify, and normalize packaged commodity declarations.
"""

import time
from typing import Any, Dict, List, Optional
from engines.cv_engine.schemas import OCRTextBlock
from engines.nlp_engine.extractors import extract_entity_from_ocr_block
from engines.nlp_engine.schemas import DeclarationType, ExtractedEntity, NLPInspectionResult

# Mandatory packaged commodity declarations under Legal Metrology Rules, 2011 (Rule 6)
MANDATORY_LEGAL_METROLOGY_FIELDS = [
    DeclarationType.MRP,
    DeclarationType.NET_QUANTITY,
    DeclarationType.MFG_DATE,
    DeclarationType.MANUFACTURER,
    DeclarationType.CONSUMER_CARE,
]


class NLPEngine:
    """
    Orchestrates entity extraction, classification, and normalization across OCR results.
    """

    def __init__(self, mandatory_fields: Optional[List[DeclarationType]] = None):
        self.mandatory_fields = mandatory_fields or MANDATORY_LEGAL_METROLOGY_FIELDS

    def extract_declarations(
        self,
        ocr_blocks: List[OCRTextBlock],
    ) -> NLPInspectionResult:
        """
        Extracts structured packaged commodity declarations from OCR blocks.
        Preserves block provenance for every entity.
        """
        t0 = time.perf_counter()
        entities: List[ExtractedEntity] = []
        entity_counter = 1

        for block in ocr_blocks:
            entity = extract_entity_from_ocr_block(
                block_id=block.block_id,
                text=block.text,
                confidence=block.confidence,
                entity_index=entity_counter,
            )
            if entity:
                entities.append(entity)
                entity_counter += 1

        # Identify unique detected declaration types
        detected_types = list({e.declaration_type for e in entities})

        # Calculate missing mandatory fields
        missing_fields = [
            req for req in self.mandatory_fields
            if req not in detected_types
        ]

        duration_ms = (time.perf_counter() - t0) * 1000.0

        return NLPInspectionResult(
            total_entities_detected=len(entities),
            entities=entities,
            detected_declaration_types=detected_types,
            missing_mandatory_fields=missing_fields,
            extraction_time_ms=round(duration_ms, 2),
        )


_nlp_engine_instance: Optional[NLPEngine] = None


def get_nlp_engine() -> NLPEngine:
    """Returns singleton instance of NLPEngine."""
    global _nlp_engine_instance
    if _nlp_engine_instance is None:
        _nlp_engine_instance = NLPEngine()
    return _nlp_engine_instance
