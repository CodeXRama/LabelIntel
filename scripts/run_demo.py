"""
LabelIntel — Reproducible End-to-End Demo Script
Executes the full inspection workflow on a real packaging sample:
Validation -> Quality -> Preprocessing -> OCR -> NLP Extraction -> Evidence Fusion -> Compliance Evaluation -> SQLite DB.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.service import process_inspection


def main():
    sample_rel = Path("data/samples/food/food_001.jpg")
    if not sample_rel.exists():
        # Fallback to any discovered sample
        samples = list(Path("data/samples").rglob("*.jpg")) + list(Path("data/samples").rglob("*.webp"))
        if not samples:
            print("ERROR: No packaging samples found in data/samples.")
            sys.exit(1)
        sample_rel = samples[0]

    print("=" * 75)
    print("LabelIntel — Packaged Commodity Automated Inspection Demo")
    print(f"Target Packaging Photograph: {sample_rel}")
    print("=" * 75)

    file_bytes = sample_rel.read_bytes()
    filename = sample_rel.name
    category = sample_rel.parent.name

    print("\n[Stage 1-7] Executing End-to-End Pipeline...")
    res = process_inspection(file_bytes, filename=filename, category_hint=category)

    if res.get("status") == "FAILED":
        print(f"\nInspection Failed: {res.get('validation_errors')}")
        sys.exit(1)

    print("\n=== 1. IMAGE VALIDATION & QUALITY METRICS ===")
    print(f"  Inspection ID:    {res['id']}")
    print(f"  Image Format:     {res['metadata']['image_format']} ({res['metadata']['width']}x{res['metadata']['height']} px)")
    print(f"  Laplacian Blur:   {res['quality']['blur_laplacian_variance']:.1f} (Blurry: {res['quality']['is_blurry']})")
    print(f"  Mean Brightness:  {res['quality']['brightness_mean']:.1f} / 255")
    print(f"  Contrast Std Dev: {res['quality']['contrast_std']:.1f}")
    if res['quality']['quality_warnings']:
        print(f"  Quality Warnings: {res['quality']['quality_warnings']}")

    print("\n=== 2. TEXT RECOGNITION & FUSED DECLARATIONS ===")
    print(f"  Total OCR Blocks: {res['ocr_summary']['total_blocks']} (Avg Confidence: {res['ocr_summary']['average_confidence']:.3f})")
    print(f"  Fused Declarations: {len(res['fused_declarations'])}")
    for d in res['fused_declarations']:
        bbox = d['bounding_box']
        norm_val = d.get('normalized_data') or "N/A"
        print(f"\n  [{d['declaration_type'].upper()}] {d['display_title']}")
        print(f"    Raw Text:    \"{d['raw_text']}\"")
        print(f"    Confidence:  {d['combined_confidence']:.2f}")
        print(f"    Coordinates: [x: {bbox['x_min']}..{bbox['x_max']}, y: {bbox['y_min']}..{bbox['y_max']}]")
        print(f"    Normalized:  {norm_val}")

    print("\n=== 3. STATUTORY COMPLIANCE REPORT ===")
    comp = res['compliance_report']
    print(f"  Overall Status:    {comp['overall_status'].upper()}")
    print(f"  Rules Evaluated:   {comp['total_rules_evaluated']} (Compliant: {comp['compliant_count']}, Non-Compliant: {comp['non_compliant_count']}, Review Flagged: {comp['flagged_count']})")
    for a in comp['assessments']:
        status_icon = "✓" if a['status'] == "compliant" else ("✗" if a['status'] == "non_compliant" else "!")
        print(f"\n  [{status_icon}] {a['rule']['title']} ({a['rule']['rule_reference']})")
        print(f"      Status:   {a['status'].upper()}")
        print(f"      Statute:  {a['rule']['statute_name']}")
        print(f"      Findings: {'; '.join(a['findings'])}")
        if a['cautions_and_recommendations']:
            print(f"      Actions:  {'; '.join(a['cautions_and_recommendations'])}")

    print("\n=== 4. ARTIFACTS & PERSISTENCE ===")
    print(f"  Raw Image URL:       {res['image_url']}")
    print(f"  Annotated Image URL: {res['annotated_url']}")
    print(f"  Database:            data/labelintel.db")
    print(f"  Execution Time:      {res['timing_ms']['total_pipeline_ms']:.1f} ms")
    print("\n[DEMO COMPLETE] Pipeline succeeded end-to-end.")


if __name__ == "__main__":
    main()
