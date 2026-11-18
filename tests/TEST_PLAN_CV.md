# LabelIntel — Computer Vision Test Suite & Verification Strategy

## 1. Objectives & Scope
This test strategy provides deterministic verification for the Computer Vision pipeline stages:
1. Input format & dimension validation.
2. Degradation & image quality scoring.
3. Preprocessing transformations (aspect preservation, CLAHE, deskew).
4. Full-image and ROI OCR text extraction & confidence scoring.
5. Coordinate preservation & mapping invariants.
6. ArUco optical marker detection, calibration, and character height estimation.

---

## 2. Test Matrix: 10 Canonical Image Test Cases

| Case # | Scenario | Test Input Characteristics | Expected Pipeline Behavior | Acceptance Invariants |
| :--- | :--- | :--- | :--- | :--- |
| **01** | Valid JPEG | Standard JPEG packaging photograph (e.g. 1920x1080, RGB, standard lighting) | Successfully decoded; quality pass; OCR blocks extracted. | `success == True`, `metadata.image_format == "JPEG"`, `quality.quality_warnings == []`. |
| **02** | Valid PNG | Lossless PNG package label flat art | Decoded; transparency alpha channels properly handled if RGBA. | `success == True`, `metadata.image_format == "PNG"`, channels converted to BGR/RGB. |
| **03** | Corrupted Image | Truncated binary header or invalid byte sequence | Caught at Stage 1 validation without unhandled crash. | `success == False`, `"Corrupted image data or unrecognized format"` in `errors`. |
| **04** | Extremely Small Image | Low-resolution crop (< 100x100 pixels, e.g. 64x64) | Rejected by dimension guard to prevent hallucinated OCR. | `success == False`, `"Image dimensions below minimum 100x100 threshold"` in `errors`. |
| **05** | Blurry Image | Defocused or motion-blurred photo ($\sigma^2_{\nabla^2} < 100.0$) | Processed, but flagged with blur warning. | `quality.is_blurry == True`, `"Low Laplacian variance: possible motion blur"` in `quality_warnings`. |
| **06** | Low-Light Image | Underexposed label photograph ($\mu < 40.0$) | Flagged for illumination; CLAHE preprocessing improves OCR contrast. | `quality.is_under_exposed == True`, `"clahe"` in `preprocessing.applied_operations`. |
| **07** | High-Resolution Image | Large camera capture (> 3000x3000px, e.g. 4032x3024) | Downscaled preserving aspect ratio; OCR coordinates accurately remapped to raw size. | `preprocessing.scale_factor_x < 1.0`, all `ocr_blocks.bounding_box` match raw pixel scale. |
| **08** | Packaged Declarations | Clear retail package displaying MRP, Net Qty, Dates, and Packer | All text lines localized and extracted with high confidence ($> 0.85$). | `len(ocr_blocks) > 0`, key tokens (`MRP`, `Net`, `g/ml`, `202...`) present in raw text. |
| **09** | Image Without Text | Blank solid texture, unprinted packaging foil, or background | Graceful execution; returns empty text block list without error. | `success == True`, `ocr_blocks == []`, `errors == []`. |
| **10** | ArUco Calibrated Image | Packaging with ArUco marker (e.g. `DICT_4X4_50`, 20mm reference) | ArUco corners detected; optical scale $\text{px/mm}$ computed; glyph heights in mm. | `physical_measurements.calibration_status == "calibrated"`, `pixels_per_mm > 0.0`, glyph mm populated. |

---

## 3. Execution & Regression Policy
- **Synthetic/Unit Tests:** Run via `pytest tests/test_cv_schemas.py` on every git commit.
- **Pipeline Integration Tests:** Image fixtures stored in `data/samples/` once canonical packaging samples are curated.
- **Integrity Rule:** Do not generate synthetic mock metrics or fake detection accuracies; metrics must be computed strictly on actual inference runs.
