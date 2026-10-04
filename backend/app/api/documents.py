"""
Documents API router.
Handles file upload, listing, and deletion.
"""

import os
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.schemas import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentInfo,
    DeleteDocumentResponse,
)
from app.services.document_processor import process_document, SUPPORTED_EXTENSIONS
from app.services.chunker import create_chunks_from_pages
from app.services.embeddings import generate_embeddings
from app.services.vector_store import add_chunks, get_all_documents, delete_document

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)

# Metadata store (in-memory; backed by JSON file for persistence)
METADATA_FILE = Path(settings.UPLOAD_PATH) / "document_metadata.json"


def load_metadata() -> dict:
    """Load document metadata from JSON file."""
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_metadata(metadata: dict):
    """Persist document metadata to JSON file."""
    try:
        METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METADATA_FILE, "w") as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save metadata: {e}")


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document.
    
    Supports: PDF, DOCX, TXT, PNG, JPG, JPEG
    """
    # ── Validate file ──────────────────────────────────────────────────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: '{ext}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    # ── Save file ──────────────────────────────────────────────────────────────
    upload_dir = Path(settings.UPLOAD_PATH)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = file.filename.replace(" ", "_")
    filepath = upload_dir / safe_filename

    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        with open(filepath, "wb") as f:
            f.write(content)
        logger.info(f"Saved uploaded file: {filepath}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # ── Process document ───────────────────────────────────────────────────────
    try:
        doc_result = process_document(str(filepath))
    except (ValueError, RuntimeError) as e:
        if filepath.exists():
            try:
                os.remove(filepath)
            except Exception:
                pass
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if filepath.exists():
            try:
                os.remove(filepath)
            except Exception:
                pass
        logger.error(f"Document processing error: {e}")
        raise HTTPException(
            status_code=400,
            detail="The document could not be read. Please upload a text-based document or a clearer scanned document.",
        )

    # ── Create chunks ──────────────────────────────────────────────────────────
    try:
        chunks = create_chunks_from_pages(
            pages_data=doc_result["pages_data"],
            document_id=doc_result["document_id"],
            filename=doc_result["filename"],
            file_type=doc_result["file_type"],
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
    except Exception as e:
        if filepath.exists():
            try:
                os.remove(filepath)
            except Exception:
                pass
        logger.error(f"Chunking error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to chunk document: {e}")

    if not chunks:
        if filepath.exists():
            try:
                os.remove(filepath)
            except Exception:
                pass
        raise HTTPException(
            status_code=400,
            detail="The document could not be read. Please upload a text-based document or a clearer scanned document.",
        )

    # ── Generate embeddings ────────────────────────────────────────────────────
    try:
        texts = [chunk["text"] for chunk in chunks]
        embeddings = generate_embeddings(texts, model_name=settings.EMBEDDING_MODEL)
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {e}")

    # ── Store in ChromaDB ──────────────────────────────────────────────────────
    try:
        stored_count = add_chunks(chunks, embeddings)
    except Exception as e:
        logger.error(f"ChromaDB storage error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store in vector database: {e}")

    # ── Save metadata ──────────────────────────────────────────────────────────
    metadata = load_metadata()
    metadata[doc_result["document_id"]] = {
        "document_id": doc_result["document_id"],
        "filename": doc_result["filename"],
        "file_type": doc_result["file_type"],
        "total_pages": doc_result["total_pages"],
        "chunks": stored_count,
        "ocr_used": doc_result["ocr_used"],
        "upload_time": doc_result["upload_time"],
        "filepath": str(filepath),
    }
    save_metadata(metadata)

    logger.info(
        f"Document processed: {doc_result['filename']} | "
        f"Pages: {doc_result['total_pages']} | "
        f"Chunks: {stored_count} | "
        f"OCR: {doc_result['ocr_used']}"
    )

    return DocumentUploadResponse(
        success=True,
        filename=doc_result["filename"],
        document_id=doc_result["document_id"],
        pages=doc_result["total_pages"],
        chunks=stored_count,
        ocr_used=doc_result["ocr_used"],
        message=f"Document processed successfully. {stored_count} chunks indexed.",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents():
    """List all indexed documents."""
    try:
        metadata = load_metadata()
        documents = []

        for doc_id, info in metadata.items():
            documents.append(DocumentInfo(
                document_id=info.get("document_id", doc_id),
                filename=info.get("filename", "Unknown"),
                upload_time=info.get("upload_time", ""),
                pages=info.get("total_pages", 0),
                chunks=info.get("chunks", 0),
                file_type=info.get("file_type", ""),
                ocr_used=info.get("ocr_used", False),
            ))

        return DocumentListResponse(documents=documents, total=len(documents))

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {e}")


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
async def delete_document_endpoint(document_id: str):
    """Delete a document and all its chunks from the vector store."""
    try:
        success = delete_document(document_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{document_id}' not found in vector store.",
            )

        # Remove from metadata
        metadata = load_metadata()
        if document_id in metadata:
            # Optionally delete the file
            filepath = metadata[document_id].get("filepath")
            if filepath and Path(filepath).exists():
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            del metadata[document_id]
            save_metadata(metadata)

        return DeleteDocumentResponse(
            success=True,
            message="Document deleted successfully.",
            document_id=document_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")
