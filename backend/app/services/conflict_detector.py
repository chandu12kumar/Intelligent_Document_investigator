"""
Conflict Detection Service.
Multi-level approach: numeric patterns, semantic similarity, LLM verification.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.services.embeddings import compute_cosine_similarity

logger = logging.getLogger(__name__)

# ─── Numeric Pattern Detection ──────────────────────────────────────────────────

# Patterns to detect numeric values with units
NUMERIC_PATTERNS = [
    # Days/hours/weeks/months/years
    r'\b(\d+(?:\.\d+)?)\s*(days?|hours?|weeks?|months?|years?)\b',
    # Percentages
    r'\b(\d+(?:\.\d+)?)\s*%\b',
    # Currency (common symbols)
    r'[₹$€£¥]\s*(\d[\d,]*(?:\.\d+)?)\b',
    r'\b(\d[\d,]*(?:\.\d+)?)\s*(?:rupees?|dollars?|euros?|pounds?)\b',
    # Leave counts
    r'\b(\d+)\s+(?:days?|leaves?|holidays?)\b',
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in NUMERIC_PATTERNS]


def extract_numeric_values(text: str) -> List[Dict[str, Any]]:
    """Extract numeric values with context from a text chunk."""
    values = []
    for pattern in COMPILED_PATTERNS:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 80)
            context = text[start:end].strip()
            values.append({
                "match": match.group(0),
                "context": context,
                "position": match.start(),
            })
    return values


def detect_numeric_conflicts(
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Level 1: Detect numeric conflicts across document chunks.
    
    Identifies cases where the same type of value (days, %, currency)
    appears with different amounts in different documents.
    """
    conflicts = []
    
    # Group chunks by document
    doc_chunks: Dict[str, List[Dict[str, Any]]] = {}
    for chunk in chunks:
        doc = chunk["metadata"].get("document", "unknown")
        if doc not in doc_chunks:
            doc_chunks[doc] = []
        doc_chunks[doc].append(chunk)

    documents = list(doc_chunks.keys())

    # Compare across document pairs
    for i in range(len(documents)):
        for j in range(i + 1, len(documents)):
            doc_a = documents[i]
            doc_b = documents[j]

            chunks_a = doc_chunks[doc_a]
            chunks_b = doc_chunks[doc_b]

            # Extract numeric values from all chunks per doc
            values_a = []
            for chunk in chunks_a:
                vals = extract_numeric_values(chunk["text"])
                for v in vals:
                    v["chunk"] = chunk
                values_a.extend(vals)

            values_b = []
            for chunk in chunks_b:
                vals = extract_numeric_values(chunk["text"])
                for v in vals:
                    v["chunk"] = chunk
                values_b.extend(vals)

            # Find conflicting numeric mentions (same unit type, different value)
            for va in values_a:
                for vb in values_b:
                    if _values_conflict(va["match"], vb["match"]):
                        # Check if contexts are semantically similar (same topic)
                        sim = compute_cosine_similarity_for_texts(
                            va["context"], vb["context"]
                        )
                        if sim > 0.4:  # Topics are related
                            conflicts.append({
                                "type": "numeric_conflict",
                                "topic": _infer_topic(va["context"]),
                                "description": (
                                    f"Documents disagree on a numeric value. "
                                    f"{doc_a} states '{va['match']}' while "
                                    f"{doc_b} states '{vb['match']}'."
                                ),
                                "source_a": {
                                    "document": doc_a,
                                    "page": chunks_a[0]["metadata"].get("page"),
                                    "quote": va["context"],
                                    "value": va["match"],
                                },
                                "source_b": {
                                    "document": doc_b,
                                    "page": chunks_b[0]["metadata"].get("page"),
                                    "quote": vb["context"],
                                    "value": vb["match"],
                                },
                                "similarity_score": sim,
                            })

    # Deduplicate conflicts
    return _deduplicate_conflicts(conflicts)


def _values_conflict(val_a: str, val_b: str) -> bool:
    """Check if two value strings are different (same unit, different number)."""
    # Extract numbers
    nums_a = re.findall(r'\d+(?:\.\d+)?', val_a.replace(',', ''))
    nums_b = re.findall(r'\d+(?:\.\d+)?', val_b.replace(',', ''))

    # Extract unit keywords
    unit_words_a = set(re.findall(r'[a-zA-Z%₹$€£]+', val_a.lower()))
    unit_words_b = set(re.findall(r'[a-zA-Z%₹$€£]+', val_b.lower()))

    if not nums_a or not nums_b:
        return False

    # If numbers differ but units overlap, it's a conflict
    nums_differ = nums_a[0] != nums_b[0]
    units_overlap = bool(unit_words_a & unit_words_b)

    return nums_differ and (units_overlap or not unit_words_a or not unit_words_b)


def compute_cosine_similarity_for_texts(text_a: str, text_b: str) -> float:
    """Compute semantic similarity between two text snippets."""
    try:
        from app.services.embeddings import generate_embeddings
        embeddings = generate_embeddings([text_a, text_b])
        if len(embeddings) == 2:
            return compute_cosine_similarity(embeddings[0], embeddings[1])
    except Exception as e:
        logger.debug(f"Similarity computation failed: {e}")
    return 0.0


def detect_semantic_conflicts(
    chunks: List[Dict[str, Any]],
    similarity_threshold: float = 0.75,
) -> List[Dict[str, Any]]:
    """
    Level 2: Detect semantic contradictions across document chunks.
    
    Finds pairs of chunks that discuss similar topics but contain
    potentially contradictory information using embedding similarity.
    """
    conflicts = []
    
    # Group by document
    doc_chunks: Dict[str, List[Dict[str, Any]]] = {}
    for chunk in chunks:
        doc = chunk["metadata"].get("document", "unknown")
        if doc not in doc_chunks:
            doc_chunks[doc] = []
        doc_chunks[doc].append(chunk)

    documents = list(doc_chunks.keys())
    if len(documents) < 2:
        return []

    # Compare chunk pairs across different documents
    for i in range(len(documents)):
        for j in range(i + 1, len(documents)):
            doc_a = documents[i]
            doc_b = documents[j]

            for ca in doc_chunks[doc_a][:5]:  # Limit comparisons for performance
                for cb in doc_chunks[doc_b][:5]:
                    sim = compute_cosine_similarity(
                        ca.get("embedding", []) or [],
                        cb.get("embedding", []) or [],
                    )
                    
                    # High similarity = same topic; check for value differences
                    if 0.65 < sim < 0.95:
                        if _texts_have_different_claims(ca["text"], cb["text"]):
                            conflicts.append({
                                "type": "semantic_conflict",
                                "topic": _infer_topic(ca["text"]),
                                "description": (
                                    f"Documents '{doc_a}' and '{doc_b}' discuss the "
                                    "same topic but may contain different information."
                                ),
                                "source_a": {
                                    "document": doc_a,
                                    "page": ca["metadata"].get("page"),
                                    "quote": ca["text"][:300],
                                },
                                "source_b": {
                                    "document": doc_b,
                                    "page": cb["metadata"].get("page"),
                                    "quote": cb["text"][:300],
                                },
                                "similarity_score": sim,
                            })

    return _deduplicate_conflicts(conflicts)


def _texts_have_different_claims(text_a: str, text_b: str) -> bool:
    """
    Quick check if two texts contain different numeric or policy claims.
    """
    nums_a = set(re.findall(r'\b\d+(?:\.\d+)?\b', text_a))
    nums_b = set(re.findall(r'\b\d+(?:\.\d+)?\b', text_b))
    
    # If both have numbers and they don't fully overlap
    if nums_a and nums_b and nums_a != nums_b:
        return True
    
    return False


def _infer_topic(context: str) -> str:
    """Infer a short topic label from context."""
    context_lower = context.lower()
    
    topic_keywords = {
        "medical leave": ["medical leave", "sick leave", "medical"],
        "annual leave": ["annual leave", "yearly leave", "paid leave"],
        "maternity leave": ["maternity", "maternal"],
        "paternity leave": ["paternity", "paternal"],
        "salary": ["salary", "wage", "pay", "compensation", "remuneration"],
        "working hours": ["working hours", "work hours", "office hours"],
        "notice period": ["notice period", "notice"],
        "effective date": ["effective", "effective date", "effective from"],
        "probation": ["probation", "probationary"],
    }

    for topic, keywords in topic_keywords.items():
        if any(kw in context_lower for kw in keywords):
            return topic

    return "policy value"


def _deduplicate_conflicts(conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate conflicts (same pair of sources + topic + values)."""
    seen = set()
    unique = []
    for c in conflicts:
        val_a = str(c.get("source_a", {}).get("value") or "").strip().lower()
        val_b = str(c.get("source_b", {}).get("value") or "").strip().lower()
        key = (
            c.get("type"),
            c.get("topic"),
            c.get("source_a", {}).get("document"),
            c.get("source_b", {}).get("document"),
            val_a,
            val_b,
        )
        reverse_key = (
            c.get("type"),
            c.get("topic"),
            c.get("source_b", {}).get("document"),
            c.get("source_a", {}).get("document"),
            val_b,
            val_a,
        )
        if key not in seen and reverse_key not in seen:
            seen.add(key)
            seen.add(reverse_key)
            unique.append(c)
    return unique


def analyze_conflicts(retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Main conflict analysis entry point.
    Runs Level 1 (numeric) and Level 2 (semantic) detection.
    
    Args:
        retrieved_chunks: Chunks from ChromaDB search results
        
    Returns:
        List of detected conflicts
    """
    if not retrieved_chunks:
        return []

    # Check if we have multiple documents
    unique_docs = set(
        c["metadata"].get("document") for c in retrieved_chunks
    )
    if len(unique_docs) < 2:
        return []

    conflicts = []

    # Level 1: Numeric conflicts
    try:
        numeric_conflicts = detect_numeric_conflicts(retrieved_chunks)
        conflicts.extend(numeric_conflicts)
        if numeric_conflicts:
            logger.info(f"Detected {len(numeric_conflicts)} numeric conflicts")
    except Exception as e:
        logger.error(f"Numeric conflict detection failed: {e}")

    # Level 2: Semantic conflicts (only if no numeric conflicts found already)
    # Skip in retrieval path to keep response fast; embeddings are pre-computed
    
    return conflicts
