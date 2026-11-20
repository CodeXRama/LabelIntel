"""
LabelIntel — End-to-End Pipeline Service
Orchestrates CV Stages 1-4, NLP Extraction, Evidence Fusion, Compliance Checks,
and SQLite persistence.
"""

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
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
from engines.cv_engine.schemas import OCRTextBlock
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


def inspection_record_to_response(record: InspectionModel, reused_existing: bool = False) -> Dict[str, Any]:
    """Convert a persisted inspection into the same contract as a fresh run."""
    quality = json.loads(record.quality_json) if record.quality_json else {}
    ocr_blocks = json.loads(record.ocr_blocks_json) if record.ocr_blocks_json else []
    declarations = json.loads(record.fused_declarations_json) if record.fused_declarations_json else []
    compliance = json.loads(record.compliance_json) if record.compliance_json else {}
    confidences = [float(block.get("confidence", 0.0)) for block in ocr_blocks]
    return {
        "id": record.id,
        "filename": record.filename,
        "category": record.category,
        "status": record.status,
        "metadata": {
            "width": record.width,
            "height": record.height,
            "file_size_bytes": record.file_size_bytes,
            "image_format": Path(record.filename).suffix.lower().lstrip(".") or "unknown",
        },
        "quality": quality,
        "timing_ms": {"total_pipeline_ms": 0.0, "nlp_extraction_ms": 0.0, "fusion_ms": 0.0, "compliance_ms": 0.0},
        "ocr_summary": {
            "total_blocks": len(ocr_blocks),
            "high_confidence_blocks": sum(1 for confidence in confidences if confidence >= 0.85),
            "average_confidence": round(float(np.mean(confidences)), 4) if confidences else 0.0,
        },
        "ocr_blocks": ocr_blocks,
        "fused_declarations": declarations,
        "compliance_report": compliance,
        "reused_existing": reused_existing,
        "ocr_reused": None,
        "image_url": f"/api/inspections/{record.id}/image",
        "annotated_url": f"/api/inspections/{record.id}/annotated",
        "reused_existing": reused_existing,
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


def render_ocr_overlay(source_bgr: np.ndarray, ocr_blocks: list, output_path: Path) -> Path:
    """Render every OCR text region with tight, confidence-coded polygons."""
    image = source_bgr.copy()
    for block in ocr_blocks:
        color = (40, 210, 80) if block.confidence >= 0.85 else (20, 165, 245)
        points = np.array([[round(p.x), round(p.y)] for p in block.polygon], dtype=np.int32)
        if len(points) < 3:
            continue
        cv2.polylines(image, [points], True, color, 2, cv2.LINE_AA)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), image)
    return output_path


def process_inspection(
    file_bytes: bytes,
    filename: str,
    category_hint: Optional[str] = None,
    force_refresh: bool = False,
    sample_relative_path: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Executes the complete LabelIntel pipeline on input image bytes.
    Saves the original and annotated images to disk and records to SQLite.
    Uses content-hash caching. Precomputed OCR is only eligible for a trusted bundled
    sample explicitly selected by the demo endpoint, never for an arbitrary upload.
    """
    def report_progress(stage: str) -> None:
        if progress_callback is None:
            return
        try:
            progress_callback(stage)
        except Exception:
            # Progress reporting must never interrupt an inspection.
            pass

    report_progress("checking_cache")
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Fast cache check: return existing completed audit if file already inspected
    if not force_refresh:
        db = SessionLocal()
        try:
            cached = (
                db.query(InspectionModel)
                .filter(
                    InspectionModel.file_hash == file_hash
                )
                .filter(InspectionModel.status == "COMPLETED")
                .order_by(InspectionModel.created_at.desc())
                .first()
            )
            if cached and Path(cached.image_path).exists() and cached.annotated_path and Path(cached.annotated_path).exists():
                report_progress("complete")
                return inspection_record_to_response(cached, reused_existing=True)
        finally:
            db.close()

    inspection_id = f"insp_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    t0_start = time.perf_counter()

    uploads_dir = Path("data/uploads").resolve()
    processed_dir = Path("data/processed").resolve()
    uploads_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. Validation (Stage 1)
    report_progress("validation")
    val_res, decoded_bgr = validate_image_input(file_bytes, filename=filename)
    if not val_res.is_valid or decoded_bgr is None:
        report_progress("failed")
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
    report_progress("quality")
    quality_metrics = assess_image_quality(decoded_bgr)

    # 3. Preprocessing (Stage 3). RapidOCR uses a smaller fixed inference
    # frame for predictable CPU latency; original coordinates are restored.
    ocr_config = CVOCRConfig(device="cpu", enable_mkldnn=False)
    preprocessing_config = CVPreprocessingConfig(
        max_width=ocr_config.rapidocr_max_side_len,
        max_height=ocr_config.rapidocr_max_side_len,
        clahe_enabled=False,
    ) if ocr_config.backend == "rapidocr" else CVPreprocessingConfig()
    report_progress("preprocessing")
    preprocessed_bgr, prep_info, _, _ = preprocess_image(decoded_bgr, preprocessing_config)

    # 4. PaddleOCR (Stage 4) with sample evaluation fast-fallback
    eval_dir = Path("data/processed/ocr_evaluation")
    stem = Path(filename).stem
    eval_ocr_blocks = None
    if sample_relative_path:
        # Evaluation snapshots are a demo optimization, not an OCR shortcut for
        # uploads that happen to share a filename. Bind the snapshot to both the
        # selected sample path and its byte size before reusing its OCR regions.
        cand = eval_dir / f"{stem}_eval.json"
        if cand.exists():
            try:
                data = json.loads(cand.read_text(encoding="utf-8"))
                evaluation_path = str(data.get("relative_path", "")).replace("\\", "/")
                evaluation_size = (data.get("metadata") or {}).get("file_size_bytes")
                if (
                    evaluation_path == sample_relative_path.replace("\\", "/")
                    and data.get("file_name") == filename
                    and evaluation_size == len(file_bytes)
                    and data.get("ocr_blocks")
                ):
                    eval_ocr_blocks = [OCRTextBlock(**b) for b in data["ocr_blocks"]]
            except Exception:
                pass

    if eval_ocr_blocks is not None:
        report_progress("ocr_reused")
        ocr_blocks = eval_ocr_blocks
        ocr_warnings = ["OCR regions reused from the evaluation snapshot for this exact bundled sample."]
    else:
        report_progress("ocr")
        ocr_engine = get_ocr_engine(ocr_config)
        ocr_blocks, ocr_warnings, ocr_errors = ocr_engine.predict(
            preprocessed_bgr,
            source_image_ref=filename,
            preprocessing_info=prep_info,
        )
        if ocr_errors and ocr_config.backend == "rapidocr":
            # Preserve the existing PaddleOCR path as a safe compatibility
            # fallback if ONNX runtime/model loading is unavailable.
            fallback = get_ocr_engine(CVOCRConfig(backend="paddle", device="cpu", enable_mkldnn=False))
            ocr_blocks, fallback_warnings, fallback_errors = fallback.predict(
                preprocessed_bgr,
                source_image_ref=filename,
                preprocessing_info=prep_info,
            )
            ocr_warnings = ocr_warnings + ["RapidOCR failed; the PaddleOCR compatibility fallback was attempted."] + fallback_warnings
            if fallback_errors:
                report_progress("failed")
                return {
                    "id": inspection_id,
                    "filename": filename,
                    "status": "FAILED",
                    "processing_errors": ocr_errors + fallback_errors,
                    "processing_warnings": ocr_warnings,
                }

    # 5. NLP Declarations Extraction
    report_progress("nlp")
    nlp_engine = get_nlp_engine()
    nlp_result = nlp_engine.extract_declarations(ocr_blocks)

    # 6. Evidence Fusion
    report_progress("fusion")
    fusion_engine = get_fusion_engine()
    fused_result = fusion_engine.fuse(
        ocr_blocks=ocr_blocks,
        nlp_result=nlp_result,
        source_image_ref=filename,
    )

    # 7. Compliance Engine
    report_progress("compliance")
    compliance_engine = get_compliance_engine()
    compliance_report = compliance_engine.evaluate_compliance(
        fused_result=fused_result,
        category_hint=category_hint,
    )

    # 8. Render Annotated Overlay Image
    report_progress("rendering")
    annotated_path = processed_dir / f"{inspection_id}_annotated.jpg"
    render_ocr_overlay(decoded_bgr, ocr_blocks, annotated_path)

    total_pipeline_ms = (time.perf_counter() - t0_start) * 1000.0

    # 9. SQLite Persistence
    report_progress("persistence")
    db = SessionLocal()
    try:
        record = InspectionModel(
            id=inspection_id,
            filename=filename,
            file_hash=file_hash,
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

    report_progress("complete")

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
        "processing_warnings": ocr_warnings,
        "ocr_reused": eval_ocr_blocks is not None,
        "ocr_blocks": [b.model_dump() for b in ocr_blocks],
        "fused_declarations": [d.model_dump() for d in fused_result.declarations],
        "compliance_report": compliance_report.model_dump(),
        "image_url": f"/api/inspections/{inspection_id}/image",
        "annotated_url": f"/api/inspections/{inspection_id}/annotated",
    }
