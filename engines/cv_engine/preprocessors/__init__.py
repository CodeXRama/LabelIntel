"""
LabelIntel Computer Vision Preprocessing Subpackage.
Provides aspect-preserving resizing, CLAHE contrast enhancement,
edge-preserving denoising, conservative deskewing, and coordinate mapping contracts.
"""

from engines.cv_engine.preprocessors.denoising import apply_denoising
from engines.cv_engine.preprocessors.deskew import (
    apply_deskew,
    estimate_dominant_skew_angle,
    rotate_image_with_matrix,
)
from engines.cv_engine.preprocessors.enhancement import apply_clahe
from engines.cv_engine.preprocessors.pipeline import preprocess_image
from engines.cv_engine.preprocessors.resize import aspect_preserving_resize

__all__ = [
    "aspect_preserving_resize",
    "apply_clahe",
    "apply_denoising",
    "estimate_dominant_skew_angle",
    "rotate_image_with_matrix",
    "apply_deskew",
    "preprocess_image",
]
