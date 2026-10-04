"""
Embedding service using SentenceTransformers.
Uses all-MiniLM-L6-v2 for semantic embeddings.
Model downloads automatically on first use.
"""

import logging
import numpy as np
from typing import List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# Global model instance (lazy-loaded)
_model = None


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """
    Lazy-load the embedding model (singleton).
    Downloads model automatically on first call.
    """
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {model_name}")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_name)
        logger.info("Embedding model loaded successfully.")
    return _model


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """L2-normalize an embedding vector."""
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm


def generate_embeddings(
    texts: List[str],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32,
) -> List[List[float]]:
    """
    Generate normalized embeddings for a list of texts.
    
    Args:
        texts: List of text strings to embed
        model_name: SentenceTransformer model name
        batch_size: Processing batch size
        
    Returns:
        List of normalized embedding vectors (as Python lists)
    """
    if not texts:
        return []

    model = get_embedding_model(model_name)

    try:
        logger.info(f"Generating embeddings for {len(texts)} texts")
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        # Convert numpy arrays to Python lists for JSON serialization
        return [emb.tolist() for emb in embeddings]

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise RuntimeError(f"Failed to generate embeddings: {e}")


def generate_query_embedding(
    question: str,
    model_name: str = "all-MiniLM-L6-v2",
) -> List[float]:
    """
    Generate a normalized embedding for a single query.
    
    Args:
        question: The user's question
        model_name: SentenceTransformer model name
        
    Returns:
        Normalized embedding vector as Python list
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    results = generate_embeddings([question.strip()], model_name=model_name)
    return results[0] if results else []


def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Compute cosine similarity between two normalized vectors.
    Assumes vectors are already L2-normalized.
    
    Returns:
        Similarity score in [-1, 1]
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b))
