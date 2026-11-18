"""
LabelIntel — PaddleOCR Result Parser Module
Transforms heterogeneous raw output formats (PaddleOCR 3.x / PaddleX dictionaries
and PaddleOCR 2.x legacy lists) into strongly typed, coordinate-restored OCRTextBlock
models conforming to the LabelIntel CV output contract.
"""

from typing import Any, List, Optional, Tuple
import numpy as np

from engines.cv_engine.schemas import BoundingBox, OCRTextBlock, Point2D, PreprocessingInfo


def parse_ocr_results(
    raw_results: Any,
    source_image_ref: str = "input_image",
    preprocessing_info: Optional[PreprocessingInfo] = None,
    min_confidence: float = 0.0,
    original_dimensions: Optional[Tuple[int, int]] = None,
) -> Tuple[List[OCRTextBlock], List[str]]:
    """
    Parses raw PaddleOCR output and restores text coordinates to original image space.

    Args:
        raw_results: Output from PaddleOCR (list of dicts, single dict, or legacy list).
        source_image_ref: Identifier or filename of the source image.
        preprocessing_info: Preprocessing metadata used to invert affine transformations.
        min_confidence: Confidence filter threshold (default: 0.0).
        original_dimensions: Optional (width, height) used for boundary clamping.

    Returns:
        Tuple of (List[OCRTextBlock], List[str] warnings).
    """
    blocks: List[OCRTextBlock] = []
    warnings: List[str] = []

    if raw_results is None:
        return blocks, warnings

    # Normalize input: PaddleOCR returns a list of results (one per image/page)
    result_items: List[Any] = []
    if isinstance(raw_results, list):
        result_items = raw_results
    elif isinstance(raw_results, dict):
        result_items = [raw_results]
    else:
        warnings.append(f"Unrecognized raw OCR output type: {type(raw_results).__name__}")
        return blocks, warnings

    if not result_items:
        return blocks, warnings

    # Boundary dimensions for clamping
    max_w = float(original_dimensions[0]) if original_dimensions else None
    max_h = float(original_dimensions[1]) if original_dimensions else None
    if preprocessing_info and (max_w is None or max_h is None):
        max_w = float(preprocessing_info.original_size[0])
        max_h = float(preprocessing_info.original_size[1])

    block_counter = 0

    for item in result_items:
        if item is None:
            continue

        # -------------------------------------------------------------
        # Format A: PaddleOCR 3.x / PaddleX Dictionary Structure
        # Keys: 'rec_texts', 'rec_scores', 'rec_polys', 'rec_boxes'
        # -------------------------------------------------------------
        if isinstance(item, dict) and "rec_texts" in item:
            texts = item.get("rec_texts", [])
            scores = item.get("rec_scores", [])
            polys = item.get("rec_polys", [])

            if not (len(texts) == len(scores) == len(polys)):
                warnings.append(
                    f"Mismatched array lengths in PaddleX output: texts={len(texts)}, "
                    f"scores={len(scores)}, polys={len(polys)}"
                )

            count = min(len(texts), len(scores), len(polys))
            for i in range(count):
                raw_text = str(texts[i]).strip()
                score = float(scores[i])
                raw_poly = polys[i]

                if not raw_text or score < min_confidence:
                    continue

                poly_points = _extract_polygon_points(raw_poly)
                if len(poly_points) < 3:
                    warnings.append(f"Skipping degenerate polygon with {len(poly_points)} vertices")
                    continue

                # Restore coordinates to original raw image space
                restored_poly = _restore_polygon(poly_points, preprocessing_info, max_w, max_h)
                bbox = _compute_enclosing_bbox(restored_poly, max_w, max_h)

                block_counter += 1
                block = OCRTextBlock(
                    block_id=f"ocr_block_{block_counter:04d}",
                    text=raw_text,
                    confidence=round(score, 4),
                    polygon=restored_poly,
                    bounding_box=bbox,
                    source_image_ref=source_image_ref,
                    associated_region_id=None,
                    line_index=block_counter - 1,
                )
                blocks.append(block)

        # -------------------------------------------------------------
        # Format B: PaddleOCR 2.x Legacy Nested List Structure
        # [ [ [ [x1, y1], [x2, y2], [x3, y3], [x4, y4] ], (text, score) ], ... ]
        # -------------------------------------------------------------
        elif isinstance(item, list):
            for entry in item:
                if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                    continue

                raw_poly, text_score_pair = entry[0], entry[1]
                if not isinstance(text_score_pair, (list, tuple)) or len(text_score_pair) < 2:
                    continue

                raw_text = str(text_score_pair[0]).strip()
                try:
                    score = float(text_score_pair[1])
                except (ValueError, TypeError):
                    score = 0.0

                if not raw_text or score < min_confidence:
                    continue

                poly_points = _extract_polygon_points(raw_poly)
                if len(poly_points) < 3:
                    warnings.append(f"Skipping degenerate legacy polygon with {len(poly_points)} vertices")
                    continue

                restored_poly = _restore_polygon(poly_points, preprocessing_info, max_w, max_h)
                bbox = _compute_enclosing_bbox(restored_poly, max_w, max_h)

                block_counter += 1
                block = OCRTextBlock(
                    block_id=f"ocr_block_{block_counter:04d}",
                    text=raw_text,
                    confidence=round(score, 4),
                    polygon=restored_poly,
                    bounding_box=bbox,
                    source_image_ref=source_image_ref,
                    associated_region_id=None,
                    line_index=block_counter - 1,
                )
                blocks.append(block)

    return blocks, warnings


def _extract_polygon_points(raw_poly: Any) -> List[Point2D]:
    """Converts numpy array, nested list, or coordinates into List[Point2D]."""
    points: List[Point2D] = []
    if isinstance(raw_poly, np.ndarray):
        arr = raw_poly.reshape(-1, 2)
        for pt in arr:
            points.append(Point2D(x=float(pt[0]), y=float(pt[1])))
    elif isinstance(raw_poly, (list, tuple)):
        for pt in raw_poly:
            if isinstance(pt, (list, tuple, np.ndarray)) and len(pt) >= 2:
                points.append(Point2D(x=float(pt[0]), y=float(pt[1])))
    return points


def _restore_polygon(
    poly: List[Point2D],
    preprocessing_info: Optional[PreprocessingInfo],
    max_w: Optional[float] = None,
    max_h: Optional[float] = None,
) -> List[Point2D]:
    """Applies inverse coordinate transformation and clamps within original bounds."""
    if preprocessing_info:
        restored = preprocessing_info.transform_polygon_to_original(poly)
    else:
        restored = poly

    # Boundary clamping
    clamped: List[Point2D] = []
    for pt in restored:
        cx = max(0.0, pt.x)
        cy = max(0.0, pt.y)
        if max_w is not None:
            cx = min(cx, max_w)
        if max_h is not None:
            cy = min(cy, max_h)
        clamped.append(Point2D(x=round(cx, 2), y=round(cy, 2)))

    return clamped


def _compute_enclosing_bbox(
    polygon: List[Point2D],
    max_w: Optional[float] = None,
    max_h: Optional[float] = None,
) -> BoundingBox:
    """Computes axis-aligned bounding box covering all polygon vertices."""
    xs = [pt.x for pt in polygon]
    ys = [pt.y for pt in polygon]

    x_min = min(xs)
    y_min = min(ys)
    x_max = max(xs)
    y_max = max(ys)

    if max_w is not None:
        x_min = max(0.0, min(x_min, max_w))
        x_max = max(0.0, min(x_max, max_w))
    if max_h is not None:
        y_min = max(0.0, min(y_min, max_h))
        y_max = max(0.0, min(y_max, max_h))

    return BoundingBox(
        x_min=round(x_min, 2),
        y_min=round(y_min, 2),
        x_max=round(x_max, 2),
        y_max=round(y_max, 2),
    )
