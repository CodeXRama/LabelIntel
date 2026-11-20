# OCR region sample data

`ocr_region_samples.csv` contains 35 rows selected deterministically from the repository's recorded OCR evaluation output: five text regions from each of seven genuine package photographs. Run `python scripts/export_submission_dataset.py` from the project root to rebuild it.

Each row is an OCR observation, not a human-corrected transcription or a legal-compliance label. The confidence value is the OCR engine's own score and is not an accuracy percentage. Coordinates are pixel positions in the source image's coordinate system.

| Field | Meaning |
| --- | --- |
| `record_id` | Source image name and OCR block identifier. |
| `source_image` | Relative path of the image used for the recorded evaluation. |
| `category` | Commodity category recorded by the evaluation pipeline. |
| `ocr_text` | Text returned by OCR for this region; errors may be present. |
| `ocr_confidence` | OCR engine confidence score from 0 to 1, not verified correctness. |
| `x_min`, `y_min`, `x_max`, `y_max` | Axis-aligned envelope around the detected text polygon, in source-image pixels. |
| `line_index` | OCR block order/index recorded for the source image. |
| `recorded_ocr_ms` | OCR time recorded in the evaluation JSON for that image. |

The sample is intended to demonstrate the application's input and evidence format. It is too small and lacks ground-truth transcriptions, so it cannot support a word-error rate, accuracy claim, or general performance claim.
