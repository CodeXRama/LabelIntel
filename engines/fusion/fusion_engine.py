"""
LabelIntel — Evidence Fusion Engine
Binds NLP semantic declarations directly to CV OCR bounding polygons and coordinates.
"""

import time
from typing import Dict, List, Optional
import numpy as np

from engines.cv_engine.schemas import BoundingBox, OCRTextBlock, Point2D
from engines.fusion.schemas import FusedDeclaration, FusionInspectionResult
from engines.nlp_engine.schemas import DeclarationType, NLPInspectionResult

DECLARATION_TITLES = {
    DeclarationType.MRP: "Maximum Retail Price (MRP)",
    DeclarationType.NET_QUANTITY: "Net Quantity / Weight",
    DeclarationType.MFG_DATE: "Date of Manufacture / Packing",
    DeclarationType.EXPIRY_DATE: "Expiry / Use By Date",
    DeclarationType.BEST_BEFORE: "Best Before Duration",
    DeclarationType.BATCH_NUMBER: "Batch / Lot Code",
    DeclarationType.MANUFACTURER: "Manufacturer Details",
    DeclarationType.PACKER: "Packer Details",
    DeclarationType.IMPORTER: "Importer Details",
    DeclarationType.CONSUMER_CARE: "Consumer Care Contact",
    DeclarationType.INGREDIENTS: "Ingredients Statement",
    DeclarationType.NUTRITION: "Nutritional Information",
    DeclarationType.COUNTRY_OF_ORIGIN: "Country of Origin",
    DeclarationType.GENERIC_NAME: "Generic Commodity Name",
    DeclarationType.FSSAI_LICENSE: "FSSAI License / Registration",
    DeclarationType.CAUTION_WARNING: "Safety Caution & Warning",
    DeclarationType.OTHER: "General Declaration",
}


class EvidenceFusionEngine:
    """
    Fuses textual semantic extractions with spatial coordinate evidence.
    """

    def fuse(
        self,
        ocr_blocks: List[OCRTextBlock],
        nlp_result: NLPInspectionResult,
        source_image_ref: str = "image.jpg",
    ) -> FusionInspectionResult:
        t0 = time.perf_counter()

        # Index OCR blocks by ID for O(1) retrieval
        ocr_by_id: Dict[str, OCRTextBlock] = {b.block_id: b for b in ocr_blocks}
        fused_declarations: List[FusedDeclaration] = []
        used_ocr_ids = set()

        for idx, entity in enumerate(nlp_result.entities, 1):
            matched_blocks: List[OCRTextBlock] = [
                ocr_by_id[b_id] for b_id in entity.source_ocr_block_ids
                if b_id in ocr_by_id
            ]

            if not matched_blocks:
                continue

            used_ocr_ids.update(entity.source_ocr_block_ids)

            # Compute unified bounding envelope
            x_min = min(b.bounding_box.x_min for b in matched_blocks)
            y_min = min(b.bounding_box.y_min for b in matched_blocks)
            x_max = max(b.bounding_box.x_max for b in matched_blocks)
            y_max = max(b.bounding_box.y_max for b in matched_blocks)

            unified_bbox = BoundingBox(
                x_min=round(x_min, 1),
                y_min=round(y_min, 1),
                x_max=round(x_max, 1),
                y_max=round(y_max, 1),
            )

            # 4-point enclosing polygon
            polygon = [
                Point2D(x=round(x_min, 1), y=round(y_min, 1)),
                Point2D(x=round(x_max, 1), y=round(y_min, 1)),
                Point2D(x=round(x_max, 1), y=round(y_max, 1)),
                Point2D(x=round(x_min, 1), y=round(y_max, 1)),
            ]

            # Harmonic mean / combined confidence
            ocr_conf = float(np.mean([b.confidence for b in matched_blocks]))
            combined_conf = round(entity.confidence * 0.4 + ocr_conf * 0.6, 4)

            title = DECLARATION_TITLES.get(entity.declaration_type, "Packaging Declaration")

            fused_decl = FusedDeclaration(
                declaration_id=f"fused_{idx:03d}_{entity.declaration_type.value}",
                declaration_type=entity.declaration_type,
                display_title=title,
                raw_text=entity.raw_text,
                normalized_data=entity.normalized_data,
                combined_confidence=combined_conf,
                evidence_ocr_blocks=matched_blocks,
                bounding_box=unified_bbox,
                polygon=polygon,
                provenance_notes=entity.parsing_notes + [
                    f"Evidence backed by {len(matched_blocks)} OCR textline(s). Original coords: [{x_min}, {y_min}, {x_max}, {y_max}]."
                ],
            )
            fused_declarations.append(fused_decl)

        unfused_ids = [b.block_id for b in ocr_blocks if b.block_id not in used_ocr_ids]
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return FusionInspectionResult(
            source_image=source_image_ref,
            total_declarations=len(fused_declarations),
            declarations=fused_declarations,
            unfused_ocr_block_ids=unfused_ids,
            fusion_time_ms=round(elapsed_ms, 2),
        )


_fusion_engine_instance: Optional[EvidenceFusionEngine] = None


def get_fusion_engine() -> EvidenceFusionEngine:
    global _fusion_engine_instance
    if _fusion_engine_instance is None:
        _fusion_engine_instance = EvidenceFusionEngine()
    return _fusion_engine_instance
