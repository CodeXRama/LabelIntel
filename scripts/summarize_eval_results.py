import json
from pathlib import Path

eval_dir = Path("data/processed/ocr_evaluation")
json_files = sorted([p for p in eval_dir.glob("*_eval.json") if not p.name.startswith("evaluation_summary")])

print(f"Found {len(json_files)} evaluation files.")
for p in json_files:
    with open(p, "r", encoding="utf-8") as f:
        d = json.load(f)
    print("=" * 70)
    print(f"File: {d['file_name']} | Category: {d['category']}")
    print(f"Dimensions: {d['metadata']['width']}x{d['metadata']['height']} | File size: {d['metadata']['file_size_bytes']} bytes")
    print(f"Quality: Laplacian Var={d['quality']['blur_laplacian_variance']:.1f}, Mean Brightness={d['quality']['brightness_mean']:.1f}, Contrast Std={d['quality']['contrast_std']:.1f}")
    if d['quality']['quality_warnings']:
        print(f"Quality Warnings: {d['quality']['quality_warnings']}")
    print(f"Timings: OCR={d['timings_ms']['ocr_ms']}ms, Total={d['timings_ms']['total_pipeline_ms']}ms")
    print(f"Detections: Total={d['detection_summary']['total_blocks']}, HighConf(>=0.85)={d['detection_summary']['high_confidence_blocks']}, AvgConf={d['detection_summary']['average_confidence']:.4f}")
    
    # Print sample detected declarations
    print("Sample Detected Texts:")
    for b in d['ocr_blocks'][:10]:
        print(f"  [{b['confidence']:.2f}] {b['text']}")
