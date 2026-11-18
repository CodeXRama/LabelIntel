"""
LabelIntel — Computer Vision Preprocessing Pipeline Module
Coordinates sequential preprocessing stages (deskew, resize, denoising, CLAHE)
and maintains mathematically verified forward and inverse coordinate transformation matrices.
"""

from typing import List, Optional, Tuple
import numpy as np

from engines.cv_engine.config import CVPreprocessingConfig
from engines.cv_engine.preprocessors.denoising import apply_denoising
from engines.cv_engine.preprocessors.deskew import apply_deskew
from engines.cv_engine.preprocessors.enhancement import apply_clahe
from engines.cv_engine.preprocessors.resize import aspect_preserving_resize
from engines.cv_engine.schemas import PreprocessingInfo


def preprocess_image(
    image: np.ndarray,
    config: Optional[CVPreprocessingConfig] = None,
    force_deskew_angle: Optional[float] = None,
) -> Tuple[np.ndarray, PreprocessingInfo, List[str], List[str]]:
    """
    Executes the complete Stage 3 preprocessing pipeline.

    Stages executed in sequence:
        1. Conservative Deskew (rotation + bounding expansion)
        2. Aspect-Preserving Resize (scale down or up preserving aspect ratio)
        3. Denoising (optional bilateral or fast-nl-means filtering)
        4. CLAHE (luminance channel contrast enhancement)

    Coordinate Mapping Guarantee:
        Maintains forward (original -> processed) and inverse (processed -> original)
        3x3 homogeneous transformation matrices:
            p_proc = M_forward * p_orig
            p_orig = M_inverse * p_proc

    Args:
        image: Validated source image numpy array (H, W, C) or (H, W).
        config: Preprocessing configuration parameters.
        force_deskew_angle: Optional pre-calculated rotation angle in degrees.

    Returns:
        Tuple of:
            - processed_image: Final transformed uint8 numpy array.
            - preprocessing_info: PreprocessingInfo Pydantic model with matrices.
            - warnings: List of non-fatal operational warnings.
            - errors: List of operational errors if processing encountered failures.
    """
    if image is None or image.size == 0 or image.ndim < 2:
        raise ValueError("Invalid image provided to preprocess_image pipeline.")

    cfg = config or CVPreprocessingConfig()
    warnings: List[str] = []
    errors: List[str] = []
    applied_ops: List[str] = []
    skipped_ops: List[str] = []

    orig_h, orig_w = image.shape[:2]
    original_size = (orig_w, orig_h)

    # Composite 3x3 transformation matrix initialized to identity
    M_forward = np.eye(3, dtype=np.float64)

    current_img = image.copy()
    applied_angle = 0.0

    # -------------------------------------------------------------
    # 1. Conservative Deskewing
    # -------------------------------------------------------------
    if cfg.deskew_enabled or (force_deskew_angle is not None):
        try:
            deskewed_img, rot_angle, M_rot, status_msg, was_rotated = apply_deskew(
                current_img,
                max_angle_degrees=cfg.deskew_max_angle,
                min_angle_threshold=cfg.deskew_min_angle,
                min_text_lines=cfg.deskew_min_text_lines,
                force_angle=force_deskew_angle,
            )
            if was_rotated:
                current_img = deskewed_img
                applied_angle = rot_angle
                # Update composite matrix: M_forward = M_rot * M_forward
                M_forward = M_rot @ M_forward
                applied_ops.append(f"deskew_{applied_angle:.2f}deg")
            else:
                skipped_ops.append(f"deskew ({status_msg})")
        except Exception as e:
            warnings.append(f"Deskewing stage failed with exception: {str(e)}. Proceeding without rotation.")
            skipped_ops.append(f"deskew_error: {str(e)}")
    else:
        skipped_ops.append("deskew (disabled_in_config)")

    # -------------------------------------------------------------
    # 2. Aspect-Preserving Resizing
    # -------------------------------------------------------------
    curr_h, curr_w = current_img.shape[:2]
    scale_x, scale_y = 1.0, 1.0

    if cfg.resize_enabled:
        try:
            resized_img, _, proc_size, sx, sy, M_scale, was_resized = aspect_preserving_resize(
                current_img,
                max_width=cfg.max_width,
                max_height=cfg.max_height,
                allow_upscaling=cfg.allow_upscaling,
            )
            if was_resized:
                current_img = resized_img
                scale_x, scale_y = sx, sy
                # Update composite matrix: M_forward = M_scale * M_forward
                M_forward = M_scale @ M_forward
                applied_ops.append(f"aspect_preserving_resize ({proc_size[0]}x{proc_size[1]}, s={sx:.4f})")
            else:
                skipped_ops.append(f"aspect_preserving_resize (image already within {cfg.max_width}x{cfg.max_height})")
        except Exception as e:
            warnings.append(f"Resizing stage failed with exception: {str(e)}. Proceeding with current size.")
            skipped_ops.append(f"resize_error: {str(e)}")
    else:
        skipped_ops.append("resize (disabled_in_config)")

    final_h, final_w = current_img.shape[:2]
    processed_size = (final_w, final_h)

    # -------------------------------------------------------------
    # 3. Denoising
    # -------------------------------------------------------------
    if cfg.denoise_enabled:
        try:
            denoised_img, was_denoised = apply_denoising(
                current_img,
                method=cfg.denoise_method,
                bilateral_d=cfg.bilateral_d,
                bilateral_sigma_color=cfg.bilateral_sigma_color,
                bilateral_sigma_space=cfg.bilateral_sigma_space,
                fast_nl_h=cfg.fast_nl_h,
            )
            if was_denoised:
                current_img = denoised_img
                applied_ops.append(f"denoising_{cfg.denoise_method}")
            else:
                skipped_ops.append("denoising (filter_returned_false)")
        except Exception as e:
            warnings.append(f"Denoising stage failed with exception: {str(e)}. Proceeding without denoising.")
            skipped_ops.append(f"denoising_error: {str(e)}")
    else:
        skipped_ops.append("denoising (disabled_in_config)")

    # -------------------------------------------------------------
    # 4. Contrast Enhancement (CLAHE)
    # -------------------------------------------------------------
    if cfg.clahe_enabled:
        try:
            enhanced_img, was_enhanced = apply_clahe(
                current_img,
                clip_limit=cfg.clahe_clip_limit,
                tile_grid_size=cfg.clahe_tile_grid_size,
            )
            if was_enhanced:
                current_img = enhanced_img
                applied_ops.append(f"clahe (clip={cfg.clahe_clip_limit}, grid={cfg.clahe_tile_grid_size})")
            else:
                skipped_ops.append("clahe (returned_false)")
        except Exception as e:
            warnings.append(f"CLAHE contrast enhancement failed with exception: {str(e)}. Proceeding without CLAHE.")
            skipped_ops.append(f"clahe_error: {str(e)}")
    else:
        skipped_ops.append("clahe (disabled_in_config)")

    # -------------------------------------------------------------
    # 5. Invert Composite Transformation Matrix
    # -------------------------------------------------------------
    try:
        M_inverse = np.linalg.inv(M_forward)
    except np.linalg.LinAlgError:
        errors.append("Transformation matrix is singular; could not compute inverse matrix.")
        M_inverse = np.eye(3, dtype=np.float64)

    # Convert matrices to standard nested float lists for JSON/Pydantic serialization
    forward_list = [[round(float(v), 8) for v in row] for row in M_forward]
    inverse_list = [[round(float(v), 8) for v in row] for row in M_inverse]

    info = PreprocessingInfo(
        original_size=original_size,
        processed_size=processed_size,
        scale_factor_x=round(float(scale_x), 6),
        scale_factor_y=round(float(scale_y), 6),
        deskew_angle_degrees=round(float(applied_angle), 4),
        applied_operations=applied_ops,
        skipped_operations=skipped_ops,
        forward_matrix=forward_list,
        inverse_matrix=inverse_list,
    )

    return current_img, info, warnings, errors
