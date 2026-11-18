"""
LabelIntel — End-to-End Pipeline Service
Orchestrates CV Stages 1-4, NLP Extraction, Evidence Fusion, Compliance Checks,
and SQLite persistence.
"""

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import cv2
import numpy as np

from backend.database import SessionLocal
from backend.models import InspectionModel
from engines.compliance_engine.engine import get_compliance_engine
from engines.cv_engine.config import CVPreprocessingConfig
from engines.cv_engine.ocr.config import CVOCRConfig
from engines.cv_engine.ocr.engine import get_ocr_engine
from engines.cv_engine.preprocessors.pipeline import preprocess_image
from engines.cv_engine.quality.quality_assessor import assess_image_quality
from engines.cv_engine.validators.image_validator import validate_image_input
from engines.fusion.fusion_engine import get_fusion_engine
from engines.nlp_engine.engine import get_nlp_engine

# Distinct colors (BGR) for visual overlay annotations by DeclarationType
DECLARATION_COLORS_BGR = {
    "mrp": (0, 200, 0),             # Green
    "net_quantity": (255, 140, 0),   # Deep Sky Blue
    "mfg_date": (0, 165, 255),       # Orange
    "expiry_date": (0, 0, 220),      # Red
    "best_before": (0, 100, 255),    # Amber
    "manufacturer": (180, 105, 255), # Pink/Purple
    "packer": (180, 105, 255),
    "consumer_care": (255, 200, 0),  # Cyan
    "fssai_license": (50, 205, 50),  # Lime
    "ingredients": (200, 200, 0),    # Teal
    "nutrition": (220, 120, 0),      # Blue
    "caution_warning": (0, 0, 255),  # Crimson Red
    "other": (128, 128, 128),        # Gray
}


def render_annotated_image(
    source_bgr: np.ndarray,
    fused_declarations: list,
    output_path: Path,
) -> Path:
    """Draws color-coded bounding polygons and text labels on a copy of the original image."""
    annotated = source_bgr.copy()

    for decl in fused_declarations:
        decl_type_val = decl.declaration_type.value if hasattr(decl.declaration_type, "value") else str(decl.declaration_type)
        color = DECLARATION_COLORS_BGR.get(decl_type_val, (0, 220, 0))

        pts = np.array([[int(pt.x), int(pt.y)] for pt in decl.polygon], dtype=np.int32)
        cv2.polylines(annotated, [pts], isClosed=True, color=color, thickness=2)

        # Label badge above bounding box
        x_min = int(decl.bounding_box.x_min)
        y_min = int(decl.bounding_box.y_min)
        badge = f"{decl.display_title}: {decl.raw_text[:25]}"

        # Background tag rectangle for readability
        (w, h), _ = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        tag_y = max(h + 6, y_min - 4)
        cv2.rectangle(annotated, (x_min, tag_y - h - 4), (x_min + w + 6, tag_y + 2), (20, 20, 20), -1)
        cv2.putText(annotated, badge, (x_min + 3, tag_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), annotated)
    return output_path


def process_inspection(
    file_bytes: bytes,
    filename: str,
    category_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes the complete LabelIntel pipeline on input image bytes.
    Saves the original and annotated images to disk and records to SQLite.
    """
    inspection_id = f"insp_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    t0_start = time.perf_counter()

    uploads_dir = Path("data/uploads").resolve()
    processed_dir = Path("data/processed").resolve()
    uploads_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. Validation (Stage 1)
    val_res, decoded_bgr = validate_image_input(file_bytes, filename=filename)
    if not val_res.is_valid or decoded_bgr is None:
        return {
            "id": inspection_id,
            "filename": filename,
            "status": "FAILED",
            "validation_errors": val_res.errors,
            "validation_warnings": val_res.warnings,
        }

    meta = val_res.metadata

    # Save original raw image
    raw_saved_path = uploads_dir / f"{inspection_id}_{filename}"
    raw_saved_path.write_bytes(file_bytes)

    # 2. Quality Assessment (Stage 2)
    quality_metrics = assess_image_quality(decoded_bgr)

    # 3. Preprocessing (Stage 3)
    preprocessed_bgr, prep_info, _, _ = preprocess_image(decoded_bgr, CVPreprocessingConfig())

    # 4. PaddleOCR (Stage 4)
    ocr_engine = get_ocr_engine(CVOCRConfig(device="cpu", enable_mkldnn=False))
    ocr_blocks, _, _ = ocr_engine.predict(
        preprocessed_bgr,
        source_image_ref=filename,
        preprocessing_info=prep_info,
    )

    # 5. NLP Declarations Extraction
    nlp_engine = get_nlp_engine()
    nlp_result = nlp_engine.extract_declarations(ocr_blocks)

    # 6. Evidence Fusion
    fusion_engine = get_fusion_engine()
    fused_result = fusion_engine.fuse(
        ocr_blocks=ocr_blocks,
        nlp_result=nlp_result,
        source_image_ref=filename,
    )

    # 7. Compliance Engine
    compliance_engine = get_compliance_engine()
    compliance_report = compliance_engine.evaluate_compliance(
        fused_result=fused_result,
        category_hint=category_hint,
    )

    # 8. Render Annotated Overlay Image
    annotated_path = processed_dir / f"{inspection_id}_annotated.jpg"
    render_annotated_image(decoded_bgr, fused_result.declarations, annotated_path)

    total_pipeline_ms = (time.perf_counter() - t0_start) * 1000.0

    # 9. SQLite Persistence
    db = SessionLocal()
    try:
        record = InspectionModel(
            id=inspection_id,
            filename=filename,
            category=category_hint,
            status="COMPLETED",
            width=meta.width,
            height=meta.height,
            file_size_bytes=meta.file_size_bytes,
            image_path=str(raw_saved_path),
            annotated_path=str(annotated_path),
            quality_json=quality_metrics.model_dump_json(),
            ocr_blocks_json=json.dumps([b.model_dump() for b in ocr_blocks]),
            fused_declarations_json=json.dumps([d.model_dump() for d in fused_result.declarations]),
            compliance_json=compliance_report.model_dump_json(),
        )
        db.add(record)
        db.commit()
    finally:
        db.close()

    # Build response payload
    return {
        "id": inspection_id,
        "filename": filename,
        "category": category_hint,
        "status": "COMPLETED",
        "metadata": meta.model_dump(),
        "quality": quality_metrics.model_dump(),
        "timing_ms": {
            "total_pipeline_ms": round(total_pipeline_ms, 1),
            "nlp_extraction_ms": nlp_result.extraction_time_ms,
            "fusion_ms": fused_result.fusion_time_ms,
            "compliance_ms": compliance_report.evaluation_time_ms,
        },
        "ocr_summary": {
            "total_blocks": len(ocr_blocks),
            "high_confidence_blocks": sum(1 for b in ocr_blocks if b.confidence >= 0.85),
            "average_confidence": round(float(np.mean([b.confidence for b in ocr_blocks])), 4) if ocr_blocks else 0.0,
        },
        "fused_declarations": [d.model_dump() for d in fused_result.declarations],
        "compliance_report": compliance_report.model_dump(),
        "image_url": f"/api/inspections/{inspection_id}/image",
        "annotated_url": f"/api/inspections/{inspection_id}/annotated",
    }
