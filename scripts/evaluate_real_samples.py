"""
LabelIntel — Real-World Packaged Commodity OCR Evaluation Script
Executes Stages 1 to 4 on all genuine samples in data/samples/, generates structured JSON
reports, creates annotated visual overlays, and runs comparative preprocessing ablation.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import time
import cv2
import numpy as np

from engines.cv_engine.config import CVPreprocessingConfig
from engines.cv_engine.ocr.config import CVOCRConfig
from engines.cv_engine.ocr.engine import get_ocr_engine
from engines.cv_engine.preprocessors.pipeline import preprocess_image
from engines.cv_engine.quality.quality_assessor import assess_image_quality
from engines.cv_engine.validators.image_validator import validate_image_input


def run_evaluation():
    samples_dir = Path("data/samples")
    output_dir = Path("data/processed/ocr_evaluation")
    annotated_dir = output_dir / "annotated"
    output_dir.mkdir(parents=True, exist_ok=True)
    annotated_dir.mkdir(parents=True, exist_ok=True)

    image_paths = sorted([
        p for p in samples_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
    ])

    print(f"Discovered {len(image_paths)} image files in {samples_dir}.")

    # Initialize OCR engine once
    t0_init = time.perf_counter()
    ocr_engine = get_ocr_engine(CVOCRConfig(device="cpu", enable_mkldnn=False))
    ocr_engine.initialize()
    init_time_sec = time.perf_counter() - t0_init
    print(f"PaddleOCR Engine initialized in {init_time_sec:.2f} s")

    summary_records = []

    # Process all genuine photographs
    for idx, img_path in enumerate(image_paths, 1):
        rel_path = img_path.relative_to(samples_dir)
        category = rel_path.parts[0] if len(rel_path.parts) > 1 else "root"
        file_name = img_path.name
        stem_name = img_path.stem

        print(f"\n[{idx}/{len(image_paths)}] Processing: {rel_path} (Category: {category})")

        total_t0 = time.perf_counter()

        # 1. Validation
        val_t0 = time.perf_counter()
        val_res, decoded_img = validate_image_input(str(img_path))
        val_ms = (time.perf_counter() - val_t0) * 1000

        if not val_res.is_valid or decoded_img is None:
            print(f"  [REJECTED] Validation failed: {val_res.errors}")
            eval_record = {
                "file_name": file_name,
                "relative_path": str(rel_path),
                "category": category,
                "validation_status": False,
                "validation_errors": val_res.errors,
                "validation_warnings": val_res.warnings,
            }
            summary_records.append(eval_record)
            with open(output_dir / f"{stem_name}_eval.json", "w", encoding="utf-8") as f:
                json.dump(eval_record, f, indent=2)
            continue

        metadata = val_res.metadata

        # 2. Quality Assessment
        qual_t0 = time.perf_counter()
        quality_metrics = assess_image_quality(decoded_img)
        qual_ms = (time.perf_counter() - qual_t0) * 1000

        # 3. Preprocessing (Default Configuration)
        prep_t0 = time.perf_counter()
        prep_cfg = CVPreprocessingConfig()
        preprocessed_img, prep_info, prep_warnings, prep_errors = preprocess_image(
            decoded_img, config=prep_cfg
        )
        prep_ms = (time.perf_counter() - prep_t0) * 1000

        # 4. PaddleOCR Inference & Coordinate Restoration
        ocr_t0 = time.perf_counter()
        ocr_blocks, ocr_warnings, ocr_errors = ocr_engine.predict(
            preprocessed_img,
            source_image_ref=file_name,
            preprocessing_info=prep_info,
        )
        ocr_ms = (time.perf_counter() - ocr_t0) * 1000
        total_ms = (time.perf_counter() - total_t0) * 1000

        print(f"  Dims: {metadata.width}x{metadata.height} | Detected Blocks: {len(ocr_blocks)} | OCR: {ocr_ms:.1f}ms | Total: {total_ms:.1f}ms")

        # 5. Build Detailed Evaluation Record
        blocks_data = [b.model_dump() for b in ocr_blocks]
        high_conf_blocks = [b for b in ocr_blocks if b.confidence >= 0.85]
        low_conf_blocks = [b for b in ocr_blocks if b.confidence < 0.85]

        eval_record = {
            "file_name": file_name,
            "relative_path": str(rel_path),
            "category": category,
            "metadata": metadata.model_dump(),
            "quality": quality_metrics.model_dump(),
            "preprocessing": prep_info.model_dump(),
            "timings_ms": {
                "validation_ms": round(val_ms, 2),
                "quality_ms": round(qual_ms, 2),
                "preprocessing_ms": round(prep_ms, 2),
                "ocr_ms": round(ocr_ms, 2),
                "total_pipeline_ms": round(total_ms, 2),
            },
            "detection_summary": {
                "total_blocks": len(ocr_blocks),
                "high_confidence_blocks": len(high_conf_blocks),
                "low_confidence_blocks": len(low_conf_blocks),
                "average_confidence": round(float(np.mean([b.confidence for b in ocr_blocks])), 4) if ocr_blocks else 0.0,
            },
            "ocr_blocks": blocks_data,
            "warnings": val_res.warnings + quality_metrics.quality_warnings + prep_warnings + ocr_warnings,
            "errors": prep_errors + ocr_errors,
        }

        with open(output_dir / f"{stem_name}_eval.json", "w", encoding="utf-8") as f:
            json.dump(eval_record, f, indent=2)

        # 6. Generate Annotated Review Image
        annotated_img = decoded_img.copy()
        for b in ocr_blocks:
            pts = np.array([[int(pt.x), int(pt.y)] for pt in b.polygon], dtype=np.int32)
            # Green polygon for high confidence, Orange for lower confidence
            color = (0, 220, 0) if b.confidence >= 0.85 else (0, 165, 255)
            cv2.polylines(annotated_img, [pts], isClosed=True, color=color, thickness=2)

            # Draw concise text tag above box
            min_x = min(pt.x for pt in b.polygon)
            min_y = min(pt.y for pt in b.polygon)
            tag = f"{b.text[:20]} ({b.confidence:.2f})"
            cv2.putText(
                annotated_img,
                tag,
                (int(min_x), max(15, int(min_y) - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                color,
                1,
                cv2.LINE_AA,
            )

        annotated_path = annotated_dir / f"{stem_name}_annotated.jpg"
        cv2.imwrite(str(annotated_path), annotated_img)

        summary_records.append({
            "file_name": file_name,
            "category": category,
            "width": metadata.width,
            "height": metadata.height,
            "blocks_count": len(ocr_blocks),
            "high_conf_count": len(high_conf_blocks),
            "avg_conf": eval_record["detection_summary"]["average_confidence"],
            "ocr_ms": round(ocr_ms, 1),
            "annotated_path": str(annotated_path),
        })

    # Save summary report
    with open(output_dir / "evaluation_summary.json", "w", encoding="utf-8") as f:
        json.dump({
            "initialization_time_sec": round(init_time_sec, 2),
            "total_images_evaluated": len(image_paths),
            "samples": summary_records,
        }, f, indent=2)

    print(f"\nAll evaluations complete. Results saved to {output_dir}")

    # -------------------------------------------------------------
    # 7. Preprocessing Comparison on Representative Subset
    # -------------------------------------------------------------
    subset_targets = ["mango_juice_back.jpg", "food_001.jpg", "household_001.jpg"]
    comparison_results = {}

    print("\n=== RUNNING PREPROCESSING COMPARISON (A vs B vs C) ===")
    for target_name in subset_targets:
        match_paths = [p for p in image_paths if p.name == target_name]
        if not match_paths:
            continue
        p = match_paths[0]
        _, raw_img = validate_image_input(str(p))
        if raw_img is None:
            continue

        print(f"\nComparing pipelines for {target_name}:")

        # Pipeline A: Raw image directly to PaddleOCR (No Preprocessing)
        t0_a = time.perf_counter()
        blocks_a, _, _ = ocr_engine.predict(raw_img, source_image_ref=f"{target_name}_raw")
        ms_a = (time.perf_counter() - t0_a) * 1000

        # Pipeline B: Default Preprocessing (Aspect Resize + CLAHE) to PaddleOCR
        t0_b = time.perf_counter()
        prep_b, info_b, _, _ = preprocess_image(raw_img, config=CVPreprocessingConfig())
        blocks_b, _, _ = ocr_engine.predict(prep_b, source_image_ref=f"{target_name}_default", preprocessing_info=info_b)
        ms_b = (time.perf_counter() - t0_b) * 1000

        # Pipeline C: Preprocessing with CLAHE disabled (Resize only) to PaddleOCR
        t0_c = time.perf_counter()
        prep_c, info_c, _, _ = preprocess_image(raw_img, config=CVPreprocessingConfig(clahe_enabled=False))
        blocks_c, _, _ = ocr_engine.predict(prep_c, source_image_ref=f"{target_name}_no_clahe", preprocessing_info=info_c)
        ms_c = (time.perf_counter() - t0_c) * 1000

        print(f"  Pipeline A (Raw):       {len(blocks_a)} blocks, {ms_a:.1f}ms")
        print(f"  Pipeline B (Default):   {len(blocks_b)} blocks, {ms_b:.1f}ms")
        print(f"  Pipeline C (No CLAHE):  {len(blocks_c)} blocks, {ms_c:.1f}ms")

        comparison_results[target_name] = {
            "pipeline_a_raw": {
                "blocks_count": len(blocks_a),
                "latency_ms": round(ms_a, 1),
                "texts": [b.text for b in blocks_a[:10]],
                "avg_confidence": round(float(np.mean([b.confidence for b in blocks_a])), 4) if blocks_a else 0.0,
            },
            "pipeline_b_default": {
                "blocks_count": len(blocks_b),
                "latency_ms": round(ms_b, 1),
                "texts": [b.text for b in blocks_b[:10]],
                "avg_confidence": round(float(np.mean([b.confidence for b in blocks_b])), 4) if blocks_b else 0.0,
            },
            "pipeline_c_no_clahe": {
                "blocks_count": len(blocks_c),
                "latency_ms": round(ms_c, 1),
                "texts": [b.text for b in blocks_c[:10]],
                "avg_confidence": round(float(np.mean([b.confidence for b in blocks_c])), 4) if blocks_c else 0.0,
            },
        }

    with open(output_dir / "preprocessing_comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison_results, f, indent=2)

    print(f"\nPreprocessing comparison complete. Saved to {output_dir / 'preprocessing_comparison.json'}")


if __name__ == "__main__":
    run_evaluation()
