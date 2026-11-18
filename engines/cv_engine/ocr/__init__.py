"""
LabelIntel Computer Vision OCR Subpackage.
Provides PaddleOCR CPU text detection, recognition, and coordinate restoration.
"""

from engines.cv_engine.ocr.config import CVOCRConfig
from engines.cv_engine.ocr.engine import PaddleOCREngine, get_ocr_engine
from engines.cv_engine.ocr.parser import parse_ocr_results

__all__ = [
    "CVOCRConfig",
    "PaddleOCREngine",
    "get_ocr_engine",
    "parse_ocr_results",
]
