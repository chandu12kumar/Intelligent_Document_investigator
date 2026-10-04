"""
OCR Service using Pillow and pytesseract.
Provides image-to-text extraction with graceful error handling.
"""

import os
import shutil
import platform
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

_tesseract_configured = False


def configure_tesseract() -> bool:
    """
    Configure Tesseract binary path based on operating system and environment.
    Supports Windows, Linux/Render, Docker, and custom TESSERACT_CMD env var.
    """
    global _tesseract_configured
    if not OCR_AVAILABLE:
        return False

    if _tesseract_configured:
        return True

    # 1. Custom environment variable override
    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd and os.path.exists(env_cmd):
        pytesseract.pytesseract.tesseract_cmd = env_cmd
        logger.info(f"Configured Tesseract from TESSERACT_CMD: {env_cmd}")
        _tesseract_configured = True
        return True

    # 2. System PATH (Linux / Render / Docker default)
    system_tesseract = shutil.which("tesseract")
    if system_tesseract:
        pytesseract.pytesseract.tesseract_cmd = system_tesseract
        logger.info(f"Configured system Tesseract from PATH: {system_tesseract}")
        _tesseract_configured = True
        return True

    # 3. Windows standard installation locations
    if platform.system() == "Windows":
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                logger.info(f"Configured Windows Tesseract path: {p}")
                _tesseract_configured = True
                return True

    logger.info("Tesseract binary not found in system PATH or standard locations. OCR disabled.")
    return False


def is_ocr_available() -> bool:
    """Check if OCR dependencies and Tesseract binary are available."""
    if not OCR_AVAILABLE:
        return False
    configure_tesseract()
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
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
