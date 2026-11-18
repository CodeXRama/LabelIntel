"""
LabelIntel — PaddleOCR Text Detection and Recognition Engine
Provides thread-safe initialization, model reuse, full-image inference on CPU,
and original-coordinate restoration for packaged commodity inspections.
"""

from typing import List, Optional, Tuple
import threading
import numpy as np

from engines.cv_engine.ocr.config import CVOCRConfig
from engines.cv_engine.ocr.parser import parse_ocr_results
from engines.cv_engine.schemas import OCRTextBlock, PreprocessingInfo


class PaddleOCREngine:
    """
    Singleton-capable wrapper around PaddleOCR.
    Reuses model instance across inferences to avoid costly re-initialization.
    """

    _instance: Optional["PaddleOCREngine"] = None
    _lock = threading.Lock()

    def __init__(self, config: Optional[CVOCRConfig] = None):
        self.config = config or CVOCRConfig()
        self._ocr = None
        self._is_initialized = False
        self._init_error: Optional[str] = None

    @classmethod
    def get_instance(cls, config: Optional[CVOCRConfig] = None) -> "PaddleOCREngine":
        """Thread-safe retrieval of the shared OCR engine instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
            elif config is not None:
                # Update config if instance exists
                cls._instance.config = config
            return cls._instance

    def initialize(self) -> bool:
        """Initializes the PaddleOCR model pipeline on CPU."""
        if self._is_initialized and self._ocr is not None:
            return True

        try:
            from paddleocr import PaddleOCR

            # Crucial Windows fix: enable_mkldnn=False avoids PIR double-attribute exceptions
            self._ocr = PaddleOCR(
                ocr_version=self.config.ocr_version,
                lang=self.config.lang,
                device=self.config.device,
                enable_mkldnn=self.config.enable_mkldnn,
                use_textline_orientation=self.config.use_textline_orientation,
                use_doc_orientation_classify=self.config.use_doc_orientation_classify,
                use_doc_unwarping=self.config.use_doc_unwarping,
                text_det_limit_side_len=self.config.text_det_limit_side_len,
                text_recognition_batch_size=self.config.text_recognition_batch_size,
                text_det_thresh=self.config.text_det_thresh,
                text_det_box_thresh=self.config.text_det_box_thresh,
                text_rec_score_thresh=self.config.text_rec_score_thresh,
                cpu_threads=self.config.cpu_threads,
            )
            self._is_initialized = True
            self._init_error = None
            return True
        except Exception as e:
            self._init_error = f"PaddleOCR initialization failed: {str(e)}"
            self._is_initialized = False
            self._ocr = None
            return False

    def predict(
        self,
        image: np.ndarray,
        source_image_ref: str = "input_image",
        preprocessing_info: Optional[PreprocessingInfo] = None,
        custom_config: Optional[CVOCRConfig] = None,
    ) -> Tuple[List[OCRTextBlock], List[str], List[str]]:
        """
        Executes OCR inference on an input image matrix and returns original-coordinate blocks.

        Args:
            image: Preprocessed or raw uint8 image numpy array (H, W, 3) or (H, W).
            source_image_ref: Identifier or filename of the source image.
            preprocessing_info: Optional PreprocessingInfo with affine matrices to invert.
            custom_config: Optional configuration override.

        Returns:
            Tuple of:
                - List[OCRTextBlock]: Parsed blocks with coordinates restored to raw image space.
                - List[str]: Operational warnings (e.g. low confidence, empty detection).
                - List[str]: Fatal inference or initialization errors.
        """
        warnings: List[str] = []
        errors: List[str] = []

        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            errors.append("Invalid image provided to OCR engine: image is None or empty array.")
            return [], warnings, errors

        if image.ndim < 2:
            errors.append(f"Invalid image dimensions: ndim={image.ndim}. Expected 2D or 3D array.")
            return [], warnings, errors

        cfg = custom_config or self.config

        # Ensure model is initialized
        if not self._is_initialized or self._ocr is None:
            if not self.initialize():
                errors.append(self._init_error or "PaddleOCR engine could not be initialized.")
                return [], warnings, errors

        # Execute OCR inference
        try:
            # PaddleOCR 3.x uses predict()
            raw_predictions = self._ocr.predict(image)
        except Exception as e:
            errors.append(f"Inference exception during PaddleOCR execution: {str(e)}")
            return [], warnings, errors

        # Check for empty predictions
        if not raw_predictions:
            warnings.append("OCR engine executed successfully but detected zero text regions.")
            return [], warnings, errors

        # Parse results and restore coordinates
        blocks, parse_warnings = parse_ocr_results(
            raw_results=raw_predictions,
            source_image_ref=source_image_ref,
            preprocessing_info=preprocessing_info,
            min_confidence=cfg.min_confidence_filter,
            original_dimensions=preprocessing_info.original_size if preprocessing_info else None,
        )
        warnings.extend(parse_warnings)

        if not blocks:
            warnings.append("OCR detection completed, but no text blocks met the confidence threshold.")

        return blocks, warnings, errors


def get_ocr_engine(config: Optional[CVOCRConfig] = None) -> PaddleOCREngine:
    """Convenience getter for the global PaddleOCREngine instance."""
    return PaddleOCREngine.get_instance(config)
