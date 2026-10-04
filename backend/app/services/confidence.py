"""
Confidence Scoring Service.
Transparent, signal-based confidence scoring.
Categorizes confidence into HIGH, MEDIUM, and LOW based on evidence quality.
"""

import logging
from typing import List, Dict, Any, Tuple

from app.models.schemas import ConfidenceLevel

logger = logging.getLogger(__name__)


def compute_confidence(
    retrieved_chunks: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    top_k: int = 5,
) -> Tuple[float, ConfidenceLevel, str]:
    """
    Compute confidence score and confidence level (HIGH / MEDIUM / LOW).
    
    Rules (from system spec):
    - HIGH: Strong relevant evidence + multiple agreeing sources or authoritative direct match + no conflict.
    - MEDIUM: Relevant evidence exists but is limited or only one source supports it.
    - LOW: Weak evidence, conflicting evidence, or incomplete information.
    """
    if not retrieved_chunks:
        return 0.0, ConfidenceLevel.LOW, "No relevant evidence found in the documents."

    relevances = [float(c.get("relevance", c.get("similarity", 0.0))) for c in retrieved_chunks]
    top_relevance = max(relevances) if relevances else 0.0
    avg_relevance = sum(relevances) / len(relevances) if relevances else 0.0

    unique_docs = set(c.get("metadata", {}).get("document") for c in retrieved_chunks)
    num_unique_docs = len(unique_docs)

    # If conflicts exist, confidence is automatically reduced
    if conflicts:
        score = min(0.55, max(0.20, top_relevance * 0.6))
        level = ConfidenceLevel.MEDIUM if score >= 0.45 else ConfidenceLevel.LOW
        explanation = f"Conflicting information detected across documents ({len(conflicts)} discrepancy found)."
        return round(score, 3), level, explanation

    # If strong relevance
    if top_relevance >= 0.70:
        if num_unique_docs > 1 or len(retrieved_chunks) >= 2 or top_relevance >= 0.85:
            score = min(0.98, max(0.85, top_relevance))
            level = ConfidenceLevel.HIGH
            explanation = "Strong direct evidence with consistent document support."
        else:
            score = round(top_relevance, 3)
            level = ConfidenceLevel.HIGH if score >= 0.80 else ConfidenceLevel.MEDIUM
            explanation = "Direct evidence found in indexed document."
    elif top_relevance >= 0.45:
        score = round(top_relevance, 3)
        level = ConfidenceLevel.MEDIUM
        explanation = "Relevant evidence exists but is limited or supported by a single source."
    else:
        score = round(top_relevance, 3)
        level = ConfidenceLevel.LOW
        explanation = "Limited or weak evidence found in the available documents."

    return score, level, explanation
