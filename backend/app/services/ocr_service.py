"""
OCR Service using Pillow and pytesseract.
Provides image-to-text extraction with graceful error handling.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Try importing OCR dependencies gracefully
try:
    import pytesseract
    from PIL import Image
    import io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract or Pillow not installed. OCR will be unavailable.")


def is_ocr_available() -> bool:
    """Check if OCR dependencies are available."""
    if not OCR_AVAILABLE:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        logger.warning("Tesseract not found. OCR disabled.")
        return False


def extract_text_from_image(image_data: bytes, page_num: int = 1) -> Tuple[str, bool]:
    """
    Extract text from image bytes using Tesseract OCR.
    
    Args:
        image_data: Raw image bytes (PNG, JPEG, etc.)
        page_num: Page number for logging context
        
    Returns:
        Tuple of (extracted_text, ocr_used)
    """
    if not is_ocr_available():
        return "", False

    try:
        image = Image.open(io.BytesIO(image_data))

        # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # Run OCR with English language and layout preservation
        text = pytesseract.image_to_string(
            image,
            lang="eng",
            config="--psm 1 --oem 3"
        )
        text = text.strip()

        if not text:
            logger.debug(f"OCR returned empty text for page {page_num}")
            return "", True

        logger.info(f"OCR extracted {len(text)} chars from page {page_num}")
        return text, True

    except Exception as e:
        logger.error(f"OCR failed for page {page_num}: {e}")
        return "", False


def extract_text_from_image_file(image_path: str) -> Tuple[str, bool]:
    """
    Extract text from an image file path.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Tuple of (extracted_text, ocr_used)
    """
    if not is_ocr_available():
        return "", False

    try:
        path = Path(image_path)
        if not path.exists():
            logger.error(f"Image file not found: {image_path}")
            return "", False

        image = Image.open(image_path)

        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        text = pytesseract.image_to_string(
            image,
            lang="eng",
            config="--psm 1 --oem 3"
        )
        text = text.strip()

        logger.info(f"OCR extracted {len(text)} chars from {path.name}")
        return text, True

    except Exception as e:
        logger.error(f"OCR failed for file {image_path}: {e}")
        return "", False


def pdf_page_to_image_bytes(page) -> Optional[bytes]:
    """
    Convert a PyMuPDF page to PNG image bytes for OCR.
    
    Args:
        page: PyMuPDF page object
        
    Returns:
        PNG bytes or None on failure
    """
    try:
        # Render at 2x resolution for better OCR accuracy
        mat = page.get_matrix(2, 2) if hasattr(page, 'get_matrix') else None
        if mat:
            pix = page.get_pixmap(matrix=mat)
        else:
            pix = page.get_pixmap(dpi=200)
        return pix.tobytes("png")
    except Exception as e:
        logger.error(f"Failed to render PDF page to image: {e}")
        return None
