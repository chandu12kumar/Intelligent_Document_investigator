"""
Intelligent text chunker with overlap and sentence-boundary awareness.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using simple regex."""
    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[str]:
    """
    Split text into chunks with overlap.
    Tries to avoid splitting mid-sentence when possible.
    
    Args:
        text: Input text
        chunk_size: Target characters per chunk
        chunk_overlap: Characters of overlap between consecutive chunks
        
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    # If text is short enough, return as-is
    if len(text) <= chunk_size:
        return [text]

    sentences = split_into_sentences(text)
    chunks: List[str] = []
    current_chunk = ""

    for sentence in sentences:
        # If adding this sentence exceeds chunk_size, flush current chunk
        if current_chunk and len(current_chunk) + len(sentence) + 1 > chunk_size:
            chunks.append(current_chunk.strip())

            # Create overlap: take last `chunk_overlap` chars from current chunk
            if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                overlap_text = current_chunk[-chunk_overlap:]
                # Find a clean sentence boundary in the overlap
                overlap_sentences = split_into_sentences(overlap_text)
                current_chunk = " ".join(overlap_sentences) + " " + sentence
            else:
                current_chunk = sentence
        else:
            current_chunk = (current_chunk + " " + sentence).strip() if current_chunk else sentence

    # Flush last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def create_chunks_from_pages(
    pages_data: List[Dict[str, Any]],
    document_id: str,
    filename: str,
    file_type: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Dict[str, Any]]:
    """
    Create chunks from processed page data.
    Each chunk retains full metadata.
    
    Args:
        pages_data: List of {page, text, ocr, section (optional)}
        document_id: Unique document identifier
        filename: Original filename
        file_type: pdf/docx/txt/png/etc.
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunk dictionaries with metadata
    """
    all_chunks: List[Dict[str, Any]] = []
    global_chunk_index = 0

    for page_data in pages_data:
        page_text = page_data.get("text", "").strip()
        page_num = page_data.get("page")
        section = page_data.get("section")
        ocr_used = page_data.get("ocr", False)

        if not page_text:
            continue

        page_chunks = chunk_text(page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        for chunk_idx, chunk_text_content in enumerate(page_chunks):
            if not chunk_text_content.strip():
                continue

            chunk_record = {
                "chunk_id": f"{document_id}_p{page_num}_c{chunk_idx}",
                "document_id": document_id,
                "document": filename,
                "page": page_num,
                "chunk_index": global_chunk_index,
                "local_chunk_index": chunk_idx,
                "section": section,
                "source_type": file_type,
                "ocr_used": ocr_used,
                "text": chunk_text_content,
                "char_count": len(chunk_text_content),
            }
            all_chunks.append(chunk_record)
            global_chunk_index += 1

    logger.info(
        f"Created {len(all_chunks)} chunks from {len(pages_data)} pages "
        f"for document: {filename}"
    )
    return all_chunks
