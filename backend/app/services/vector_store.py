"""
ChromaDB vector store service.
Persistent storage of document chunks and their embeddings.
"""

import os
import logging
import uuid
import json
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

logger = logging.getLogger(__name__)

# ─── ChromaDB Client (singleton) ───────────────────────────────────────────────

_chroma_client: Optional[chromadb.PersistentClient] = None
_collection = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Get or create persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(settings.CHROMA_PATH, exist_ok=True)
        logger.info(f"Initializing ChromaDB at: {settings.CHROMA_PATH}")
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
        )
        logger.info("ChromaDB initialized successfully.")
    return _chroma_client


def get_collection():
    """Get or create the document collection."""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"Collection '{settings.CHROMA_COLLECTION}' ready. "
            f"Documents: {_collection.count()}"
        )
    return _collection


# ─── Document Management ────────────────────────────────────────────────────────

def add_chunks(chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
    """
    Add document chunks with embeddings to ChromaDB.
    Uses content-based IDs to prevent duplicates.
    
    Args:
        chunks: List of chunk metadata dicts
        embeddings: Corresponding embedding vectors
        
    Returns:
        Number of chunks successfully added
    """
    if not chunks or not embeddings:
        return 0

    if len(chunks) != len(embeddings):
        raise ValueError(f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) count mismatch.")

    collection = get_collection()

    ids = []
    documents = []
    metadatas = []
    embedding_list = []

    for chunk, embedding in zip(chunks, embeddings):
        chunk_id = chunk.get("chunk_id") or str(uuid.uuid4())

        # Build metadata (ChromaDB only supports str/int/float/bool values)
        metadata = {
            "document_id": str(chunk.get("document_id", "")),
            "document": str(chunk.get("document", "")),
            "page": chunk.get("page") if chunk.get("page") is not None else -1,
            "chunk_index": int(chunk.get("chunk_index", 0)),
            "local_chunk_index": int(chunk.get("local_chunk_index", 0)),
            "section": str(chunk.get("section") or ""),
            "source_type": str(chunk.get("source_type", "unknown")),
            "ocr_used": bool(chunk.get("ocr_used", False)),
            "char_count": int(chunk.get("char_count", 0)),
        }

        ids.append(chunk_id)
        documents.append(chunk["text"])
        metadatas.append(metadata)
        embedding_list.append(embedding)

    try:
        # Upsert prevents duplicates (same ID = overwrite)
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embedding_list,
        )
        logger.info(f"Upserted {len(ids)} chunks into ChromaDB.")
        return len(ids)
    except Exception as e:
        logger.error(f"ChromaDB upsert failed: {e}")
        raise RuntimeError(f"Failed to store chunks in ChromaDB: {e}")


def search_documents(
    query_embedding: List[float],
    top_k: int = 10,
    document_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Semantic search in ChromaDB using a single query embedding.
    """
    return search_documents_multi(
        query_embeddings=[query_embedding],
        top_k=top_k,
        document_filter=document_filter,
    )


def search_documents_multi(
    query_embeddings: List[List[float]],
    top_k: int = 15,
    document_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Semantic search in ChromaDB supporting multiple query embeddings (e.g., expanded queries).
    Retrieves results across all queries, deduplicates chunks by ID, and keeps the highest
    similarity score for each candidate chunk.
    
    Args:
        query_embeddings: List of normalized query vectors
        top_k: Number of results to return
        document_filter: Optional document filename or ID filter
        
    Returns:
        Deduplicated list of chunk dicts ranked by highest similarity
    """
    collection = get_collection()
    count = collection.count()

    if count == 0 or not query_embeddings:
        return []

    actual_k = min(top_k, count)

    where = None
    if document_filter:
        where = {"document": document_filter}

    try:
        results = collection.query(
            query_embeddings=query_embeddings,
            n_results=actual_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # Aggregate across all query runs, keeping max similarity per chunk
        chunk_map: Dict[str, Dict[str, Any]] = {}

        if results and results.get("ids"):
            for q_idx in range(len(results["ids"])):
                q_ids = results["ids"][q_idx]
                q_docs = results["documents"][q_idx]
                q_metas = results["metadatas"][q_idx]
                q_dists = results["distances"][q_idx]

                for i, doc_id in enumerate(q_ids):
                    distance = q_dists[i]
                    # Cosine distance: 0 = identical, 2 = opposite
                    similarity = max(0.0, 1.0 - distance)

                    if doc_id not in chunk_map:
                        chunk_map[doc_id] = {
                            "id": doc_id,
                            "text": q_docs[i],
                            "metadata": q_metas[i],
                            "similarity": round(similarity, 4),
                            "distance": distance,
                        }
                    else:
                        # Keep highest similarity across expanded queries
                        if similarity > chunk_map[doc_id]["similarity"]:
                            chunk_map[doc_id]["similarity"] = round(similarity, 4)
                            chunk_map[doc_id]["distance"] = distance

        # Rank all unique chunks by descending similarity
        ranked_hits = sorted(chunk_map.values(), key=lambda x: x["similarity"], reverse=True)
        return ranked_hits[:actual_k]

    except Exception as e:
        logger.error(f"ChromaDB multi-search failed: {e}")
        raise RuntimeError(f"Search failed: {e}")


def get_document_overview(
    document_id: Optional[str] = None,
    filename: Optional[str] = None,
    top_k: int = 6,
) -> List[Dict[str, Any]]:
    """
    Retrieve representative chunks from a document for broad overview and summarization.
    Selects:
    - Page 1 / chunk 0 & 1 (intro, profile summary, titles)
    - Heading/section chunks
    - High-information content chunks
    - Evenly distributed chunks across document
    
    Args:
        document_id: Optional unique document ID
        filename: Optional document filename
        top_k: Max representative chunks to return
        
    Returns:
        List of representative chunk dicts
    """
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []

    where = None
    if document_id:
        where = {"document_id": document_id}
    elif filename:
        where = {"document": filename}

    try:
        results = collection.get(
            where=where,
            include=["documents", "metadatas"],
        )

        ids = results.get("ids", [])
        docs = results.get("documents", [])
        metas = results.get("metadatas", [])

        if not ids:
            return []

        all_items = []
        for doc_id, text, meta in zip(ids, docs, metas):
            all_items.append({
                "id": doc_id,
                "text": text,
                "metadata": meta,
                "similarity": 0.85,  # High baseline for overview
                "chunk_index": meta.get("chunk_index", 0),
                "char_count": meta.get("char_count", len(text)),
            })

        # Sort by chunk_index to maintain reading order
        all_items.sort(key=lambda x: x["chunk_index"])

        if len(all_items) <= top_k:
            return all_items

        # Pick representative sample:
        # 1. First 2 chunks (header, profile summary, title)
        # 2. Last chunk (conclusion, education, certifications)
        # 3. Chunks with highest character count in the middle
        selected = []
        selected_ids = set()

        # Always include chunk 0 and 1 if available
        for item in all_items[:2]:
            selected.append(item)
            selected_ids.add(item["id"])

        # Include last chunk if not already included
        if all_items[-1]["id"] not in selected_ids:
            selected.append(all_items[-1])
            selected_ids.add(all_items[-1]["id"])

        # Fill remaining slots with largest content chunks from remaining items
        remaining = [it for it in all_items if it["id"] not in selected_ids]
        remaining.sort(key=lambda x: x["char_count"], reverse=True)

        needed = top_k - len(selected)
        for it in remaining[:needed]:
            selected.append(it)

        # Re-sort by chunk_index
        selected.sort(key=lambda x: x["chunk_index"])
        return selected

    except Exception as e:
        logger.error(f"Failed to get document overview chunks: {e}")
        return []


def get_all_documents() -> List[Dict[str, Any]]:
    """
    Retrieve unique documents stored in ChromaDB.
    
    Returns:
        List of document info dicts
    """
    collection = get_collection()
    count = collection.count()

    if count == 0:
        return []

    try:
        # Get all items to extract unique documents
        results = collection.get(include=["metadatas"])
        
        seen_docs: Dict[str, Dict[str, Any]] = {}
        for meta in results["metadatas"]:
            doc_id = meta.get("document_id", "")
            if doc_id not in seen_docs:
                seen_docs[doc_id] = {
                    "document_id": doc_id,
                    "filename": meta.get("document", ""),
                    "file_type": meta.get("source_type", ""),
                    "chunks": 0,
                    "max_page": 0,
                    "ocr_used": meta.get("ocr_used", False),
                }
            seen_docs[doc_id]["chunks"] += 1
            page = meta.get("page", 0) or 0
            if page > seen_docs[doc_id]["max_page"]:
                seen_docs[doc_id]["max_page"] = page

        return list(seen_docs.values())

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        return []


def delete_document(document_id: str) -> bool:
    """
    Delete all chunks for a given document from ChromaDB.
    
    Args:
        document_id: The document's unique ID
        
    Returns:
        True if deletion succeeded
    """
    collection = get_collection()

    try:
        results = collection.get(
            where={"document_id": {"$eq": document_id}},
            include=["metadatas"],
        )
        ids_to_delete = results.get("ids", [])

        if not ids_to_delete:
            logger.warning(f"No chunks found for document_id: {document_id}")
            return False

        collection.delete(ids=ids_to_delete)
        logger.info(f"Deleted {len(ids_to_delete)} chunks for document: {document_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise RuntimeError(f"Delete failed: {e}")


def get_collection_stats() -> Dict[str, Any]:
    """Get collection statistics."""
    try:
        collection = get_collection()
        return {
            "total_chunks": collection.count(),
            "collection_name": settings.CHROMA_COLLECTION,
            "chroma_path": settings.CHROMA_PATH,
        }
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        return {"total_chunks": 0, "error": str(e)}
