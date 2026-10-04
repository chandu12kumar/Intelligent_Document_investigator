"""
Document Processor Service.
Handles PDF, DOCX, TXT, and image files with OCR fallback.
"""

import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── PDF via PyMuPDF ───────────────────────────────────────────────────────────
try:
    import pymupdf as fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False
        logger.warning("PyMuPDF not installed. PDF processing limited.")

# ─── DOCX ─────────────────────────────────────────────────────────────────────
try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("python-docx not installed. DOCX processing unavailable.")

from app.services.ocr_service import (
    extract_text_from_image,
    extract_text_from_image_file,
    pdf_page_to_image_bytes,
    is_ocr_available,
)

# Minimum character count to consider native text extraction successful
MIN_TEXT_THRESHOLD = 50


def compute_document_id(filepath: str) -> str:
    """Generate a stable document ID from the file path + content hash."""
    with open(filepath, "rb") as f:
        content = f.read()
    hash_val = hashlib.sha256(content).hexdigest()[:16]
    stem = Path(filepath).stem[:20].replace(" ", "_")
    return f"{stem}_{hash_val}"


# ─── PDF Processing ────────────────────────────────────────────────────────────

def process_pdf(filepath: str) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Process a PDF file, extracting text per page.
    Falls back to OCR for scanned/image pages.
    
    Returns:
        (pages_data, ocr_used)
        pages_data: list of {"page": int, "text": str, "ocr": bool}
    """
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF is not installed. Cannot process PDF.")

    pages_data: List[Dict[str, Any]] = []
    ocr_used = False

    try:
        doc = fitz.open(filepath)
        logger.info(f"Processing PDF: {filepath} ({doc.page_count} pages)")

        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text("text").strip()

            if len(text) < MIN_TEXT_THRESHOLD and is_ocr_available():
                # Native extraction insufficient → try OCR
                logger.info(f"Page {page_num + 1}: sparse text, attempting OCR")
                image_bytes = pdf_page_to_image_bytes(page)
                if image_bytes:
                    ocr_text, ocr_success = extract_text_from_image(
                        image_bytes, page_num=page_num + 1
                    )
                    if ocr_success and ocr_text:
                        pages_data.append({
                            "page": page_num + 1,
                            "text": ocr_text,
                            "ocr": True,
                        })
                        ocr_used = True
                        continue

            if text:
                pages_data.append({
                    "page": page_num + 1,
                    "text": text,
                    "ocr": False,
                })

        doc.close()
        return pages_data, ocr_used

    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        raise RuntimeError(f"Failed to process PDF: {e}")


# ─── DOCX Processing ───────────────────────────────────────────────────────────

def process_docx(filepath: str) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Process a DOCX file, extracting paragraphs with section context.
    
    Returns:
        (pages_data, ocr_used)
    """
    if not DOCX_AVAILABLE:
        raise RuntimeError("python-docx is not installed. Cannot process DOCX.")

    try:
        doc = DocxDocument(filepath)
        logger.info(f"Processing DOCX: {filepath}")

        pages_data: List[Dict[str, Any]] = []
        current_section = None
        current_text_parts: List[str] = []
        chunk_page = 1  # DOCX has no real page numbers

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            # Detect section headings
            if para.style.name.startswith("Heading"):
                # Save accumulated text as a "page"
                if current_text_parts:
                    pages_data.append({
                        "page": chunk_page,
                        "text": "\n".join(current_text_parts),
                        "section": current_section,
                        "ocr": False,
                    })
                    chunk_page += 1
                    current_text_parts = []
                current_section = text
            else:
                current_text_parts.append(text)

        # Flush remaining text
        if current_text_parts:
            pages_data.append({
                "page": chunk_page,
                "text": "\n".join(current_text_parts),
                "section": current_section,
                "ocr": False,
            })

        # If nothing was segmented, treat as single block
        if not pages_data:
            all_text = "\n".join(
                p.text.strip() for p in doc.paragraphs if p.text.strip()
            )
            if all_text:
                pages_data.append({"page": 1, "text": all_text, "ocr": False})

        return pages_data, False

    except Exception as e:
        logger.error(f"DOCX processing failed: {e}")
        raise RuntimeError(f"Failed to process DOCX: {e}")


# ─── TXT Processing ────────────────────────────────────────────────────────────

def process_txt(filepath: str) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Process a plain text file.
    
    Returns:
        (pages_data, ocr_used)
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if not content.strip():
            raise RuntimeError("TXT file is empty.")

        # Split into logical pages by double newlines or ~2000 chars
        pages_data = [{"page": 1, "text": content, "ocr": False}]
        logger.info(f"Processing TXT: {filepath} ({len(content)} chars)")
        return pages_data, False

    except Exception as e:
        logger.error(f"TXT processing failed: {e}")
        raise RuntimeError(f"Failed to process TXT: {e}")


# ─── Image Processing (PNG/JPG) ────────────────────────────────────────────────

def process_image(filepath: str) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Process an image file via OCR.
    
    Returns:
        (pages_data, ocr_used)
    """
    if not is_ocr_available():
        raise ValueError(
            "OCR is not available on this server. Install Tesseract OCR to process scanned images."
        )

    text, ocr_success = extract_text_from_image_file(filepath)
    if not ocr_success or not text or not text.strip():
        raise ValueError(
            "The document could not be read. Please upload a text-based document or a clearer scanned document."
        )

    return [{"page": 1, "text": text.strip(), "ocr": True}], True


# ─── Main Dispatcher ───────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"}


def process_document(filepath: str) -> Dict[str, Any]:
    """
    Main document processing entry point.
    
    Args:
        filepath: Absolute path to the uploaded file
        
    Returns:
        {
            "document_id": str,
            "filename": str,
            "file_type": str,
            "pages_data": [...],
            "total_pages": int,
            "ocr_used": bool,
        }
    """
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    logger.info(f"Processing document: {path.name} (type: {ext})")

    if ext == ".pdf":
        pages_data, ocr_used = process_pdf(filepath)
    elif ext == ".docx":
        pages_data, ocr_used = process_docx(filepath)
    elif ext == ".txt":
        pages_data, ocr_used = process_txt(filepath)
    elif ext in (".png", ".jpg", ".jpeg"):
        pages_data, ocr_used = process_image(filepath)
    else:
        raise ValueError(f"Unsupported extension: {ext}")

    if not pages_data or not any(p.get("text", "").strip() for p in pages_data):
        raise ValueError(
            "The document could not be read. Please upload a text-based document or a clearer scanned document."
        )

    document_id = compute_document_id(filepath)

    return {
        "document_id": document_id,
        "filename": path.name,
        "file_type": ext.lstrip("."),
        "pages_data": pages_data,
        "total_pages": len(pages_data),
        "ocr_used": ocr_used,
        "upload_time": datetime.utcnow().isoformat(),
    }
