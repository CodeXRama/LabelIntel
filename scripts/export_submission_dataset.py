"""Export a small, reproducible sample of recorded OCR regions for submission."""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "data" / "processed" / "ocr_evaluation"
OUTPUT = ROOT / "data" / "submission" / "ocr_region_samples.csv"
ROWS_PER_IMAGE = 5


def main() -> None:
    rows = []
    for path in sorted(EVAL_DIR.glob("*_eval.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        blocks = payload.get("ocr_blocks") or []
        if not blocks:
            continue
        count = min(ROWS_PER_IMAGE, len(blocks))
        indexes = sorted({round(i * (len(blocks) - 1) / max(1, count - 1)) for i in range(count)})
        timing = payload.get("timings_ms") or {}
        for index in indexes:
            block = blocks[index]
            box = block.get("bounding_box") or {}
            rows.append({
                "record_id": f"{payload.get('file_name', path.stem)}:{block.get('block_id', index)}",
                "source_image": payload.get("relative_path", payload.get("file_name", "")),
                "category": payload.get("category", "unknown"),
                "ocr_text": block.get("text", ""),
                "ocr_confidence": block.get("confidence", ""),
                "x_min": box.get("x_min", ""),
                "y_min": box.get("y_min", ""),
                "x_max": box.get("x_max", ""),
                "y_max": box.get("y_max", ""),
                "line_index": block.get("line_index", index),
                "recorded_ocr_ms": timing.get("ocr_ms", ""),
            })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["record_id", "source_image", "category", "ocr_text", "ocr_confidence",
              "x_min", "y_min", "x_max", "y_max", "line_index", "recorded_ocr_ms"]
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {len(rows)} genuine OCR-region rows to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
