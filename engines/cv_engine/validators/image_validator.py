"""
LabelIntel — Computer Vision Image Validation Module
Validates file existence, format headers, dimensional bounds, aspect ratio,
and image decodability.
"""

import io
from pathlib import Path
from typing import Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image

from engines.cv_engine.config import CVValidationConfig
from engines.cv_engine.schemas import ImageMetadata, ValidationResult

# Canonical Magic Bytes for Supported Formats
MAGIC_BYTES_JPEG = b"\xff\xd8\xff"
MAGIC_BYTES_PNG = b"\x89PNG\r\n\x1a\n"
MAGIC_BYTES_RIFF = b"RIFF"
MAGIC_BYTES_WEBP = b"WEBP"


def detect_format_from_bytes(data: bytes) -> Optional[str]:
    """
    Inspect raw binary header magic bytes to verify actual image container format.
    Does not rely on superficial file extensions.
    """
    if len(data) < 8:
        return None
    if data.startswith(MAGIC_BYTES_JPEG):
        return "JPEG"
    if data.startswith(MAGIC_BYTES_PNG):
        return "PNG"
    if data.startswith(MAGIC_BYTES_RIFF) and len(data) >= 12 and data[8:12] == MAGIC_BYTES_WEBP:
        return "WEBP"
    if b"ftypavif" in data[:32] or b"ftypavis" in data[:32]:
        return "AVIF"
    return None


def validate_image_input(
    source: Union[str, Path, bytes, np.ndarray],
    filename: Optional[str] = None,
    config: Optional[CVValidationConfig] = None,
) -> Tuple[ValidationResult, Optional[np.ndarray]]:
    """
    Validate input image for format compliance, structural decodability,
    and dimensional integrity.

    Args:
        source: File path (str or Path), raw bytes, or an already-loaded numpy ndarray.
        filename: Optional filename label used in metadata when source is bytes/array.
        config: Optional validation configuration thresholds.

    Returns:
        Tuple of (ValidationResult, Optional[np.ndarray]):
            - ValidationResult: Pydantic model with validation status, metadata, errors, warnings.
            - Optional[np.ndarray]: Successfully decoded BGR image array (None if invalid).
    """
    cfg = config or CVValidationConfig()
    errors = []
    warnings = []
    raw_bytes: Optional[bytes] = None
    resolved_path: Optional[str] = None
    resolved_filename = filename or "in_memory_image"
    file_size_bytes = 0

    # 1. Source Resolution & Reading
    if isinstance(source, (str, Path)):
        path_obj = Path(source)
        resolved_filename = filename or path_obj.name
        resolved_path = str(path_obj.resolve())

        if not path_obj.exists():
            errors.append(f"Image file not found at path: '{resolved_path}'")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

        if not path_obj.is_file():
            errors.append(f"Specified path is not a regular file: '{resolved_path}'")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

        try:
            file_size_bytes = path_obj.stat().st_size
            if file_size_bytes == 0:
                errors.append(f"Image file is empty (0 bytes): '{resolved_path}'")
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

            if file_size_bytes > cfg.max_file_size_bytes:
                errors.append(
                    f"File size ({file_size_bytes / (1024*1024):.2f} MB) exceeds maximum "
                    f"allowed limit ({cfg.max_file_size_bytes / (1024*1024):.2f} MB)"
                )
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

            with open(path_obj, "rb") as f:
                raw_bytes = f.read()

        except Exception as e:
            errors.append(f"Failed to read image file from disk: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

    elif isinstance(source, bytes):
        raw_bytes = source
        file_size_bytes = len(raw_bytes)
        if file_size_bytes == 0:
            errors.append("Provided image byte buffer is empty (0 bytes)")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

        if file_size_bytes > cfg.max_file_size_bytes:
            errors.append(
                f"Byte buffer size ({file_size_bytes / (1024*1024):.2f} MB) exceeds limit "
                f"({cfg.max_file_size_bytes / (1024*1024):.2f} MB)"
            )
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

    elif isinstance(source, np.ndarray):
        # Directly supplied numpy array
        if source.size == 0:
            errors.append("Provided numpy image array is empty (0 elements)")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

        img = source
        file_size_bytes = source.nbytes
        image_format = "NUMPY_ARRAY"
        return _validate_array_dimensions(img, resolved_filename, resolved_path, file_size_bytes, image_format, cfg)

    else:
        errors.append(f"Unsupported source type: '{type(source).__name__}'. Expected str, Path, bytes, or ndarray.")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

    # 2. Container Format Validation (Magic Bytes)
    detected_format = detect_format_from_bytes(raw_bytes)
    if detected_format is None:
        errors.append(
            "Unsupported or unrecognized image container format. "
            f"File does not match magic signatures for {', '.join(cfg.allowed_formats)}."
        )
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

    if detected_format not in cfg.allowed_formats:
        errors.append(
            f"Detected format '{detected_format}' is not in allowed formats: {cfg.allowed_formats}"
        )
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

    # 3. Structural Image Decoding
    try:
        nparr = np.frombuffer(raw_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if img is None:
            # Fallback to Pillow for formats not natively compiled into OpenCV Windows (e.g. AVIF)
            pil_img = Image.open(io.BytesIO(raw_bytes))
            if pil_img.mode == "RGBA":
                bgra = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2BGRA)
                img = bgra
            else:
                rgb = np.array(pil_img.convert("RGB"))
                img = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception as e:
        errors.append(f"Corrupted image data or decoding exception: {str(e)}")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

    if img is None:
        errors.append("Corrupted image data: Failed to decode the byte stream into an image matrix.")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

    # 4. Dimensional and Aspect Ratio Validation
    return _validate_array_dimensions(img, resolved_filename, resolved_path, file_size_bytes, detected_format, cfg)


def _validate_array_dimensions(
    img: np.ndarray,
    filename: str,
    source_path: Optional[str],
    file_size_bytes: int,
    image_format: str,
    cfg: CVValidationConfig,
) -> Tuple[ValidationResult, Optional[np.ndarray]]:
    """Internal helper to validate geometry and extract ImageMetadata."""
    errors = []
    warnings = []

    if img.ndim < 2:
        errors.append(f"Invalid image array dimension: ndim={img.ndim}. Expected 2D or 3D matrix.")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

    height, width = img.shape[:2]
    channels = 1 if img.ndim == 2 else img.shape[2]

    # Dimension guards
    if width <= 0 or height <= 0:
        errors.append(f"Invalid image dimensions: width={width}, height={height}. Both must be > 0.")
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

    if width < cfg.min_dimension or height < cfg.min_dimension:
        errors.append(
            f"Image dimensions ({width}x{height}) below minimum threshold "
            f"({cfg.min_dimension}x{cfg.min_dimension} pixels). "
            "Packaged statutory declarations cannot be reliably resolved at this resolution."
        )
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

    if width > cfg.max_dimension or height > cfg.max_dimension:
        warnings.append(
            f"Image dimensions ({width}x{height}) exceed standard limit "
            f"({cfg.max_dimension}x{cfg.max_dimension}). "
            "Aspect-preserving downscaling will be required prior to inference."
        )

    # Aspect ratio check
    aspect_ratio = round(width / float(height), 4)
    if aspect_ratio < cfg.min_aspect_ratio or aspect_ratio > cfg.max_aspect_ratio:
        errors.append(
            f"Extreme aspect ratio ({aspect_ratio:.4f}) outside acceptable range "
            f"[{cfg.min_aspect_ratio}, {cfg.max_aspect_ratio}]. "
            "Image appears to be an unreadable packaging strip or abnormal crop."
        )
        return ValidationResult(is_valid=False, errors=errors, warnings=warnings), None

    # If image has 4 channels (BGRA with alpha), normalize to 3 channels (BGR)
    # while preserving original rgb content on a neutral white background
    processed_img = img
    if channels == 4:
        warnings.append("Image contains an alpha channel (4-channel BGRA). Converted to 3-channel BGR.")
        b, g, r, a = cv2.split(img)
        alpha_factor = a.astype(float) / 255.0
        white_bg = np.ones_like(b, dtype=float) * 255.0
        b = (b.astype(float) * alpha_factor + white_bg * (1.0 - alpha_factor)).astype(np.uint8)
        g = (g.astype(float) * alpha_factor + white_bg * (1.0 - alpha_factor)).astype(np.uint8)
        r = (r.astype(float) * alpha_factor + white_bg * (1.0 - alpha_factor)).astype(np.uint8)
        processed_img = cv2.merge([b, g, r])
        channels = 3

    metadata = ImageMetadata(
        filename=filename,
        source_path=source_path,
        file_size_bytes=file_size_bytes,
        image_format=image_format,
        width=width,
        height=height,
        channels=channels,
        aspect_ratio=aspect_ratio,
    )

    return ValidationResult(is_valid=True, metadata=metadata, errors=[], warnings=warnings), processed_img
