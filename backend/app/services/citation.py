"""
Citation Builder Service.
Assembles structured source citations and short relevant excerpts from retrieved evidence chunks.
"""

import re
import logging
from typing import List, Dict, Any, Optional

from app.models.schemas import EvidenceItem, SourceCitation

logger = logging.getLogger(__name__)


def extract_relevant_excerpt(text: str, query: str = "", max_sentences: int = 2, max_chars: int = 220) -> str:
    """
    Extract a short (1-3 sentences, max ~220 chars) excerpt from chunk text
    that directly supports the answer to the user's question.
    Avoids showing entire pages or large raw text blocks.
    """
    if not text:
        return ""

    # Clean text
    clean = re.sub(r"[\r\t]+", " ", text)
    clean = re.sub(r"[ \t]+", " ", clean).strip()

    # Split into candidate lines / sentences
    # Handle slides or line-separated text
    raw_lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    # If the text is short structured lines (e.g. slides, metadata)
    if len(raw_lines) > 2 and any(len(l) < 80 for l in raw_lines):
        # Find lines that match query terms
        q_words = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_]+\b", query) if len(w) > 2]
        scored_lines = []
        for line in raw_lines:
            line_lower = line.lower()
            match_count = sum(1 for w in q_words if w in line_lower)
            # Give bonus to lines containing key indicators like dates, numbers, authors, titles
            if re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b|\bphone\b|\boptimization\b|\bthesis\b|\brouting\b", line_lower):
                match_count += 2
            scored_lines.append((match_count, line))

        # Sort by match score
        scored_lines.sort(key=lambda x: x[0], reverse=True)
        top_lines = [line for score, line in scored_lines if score > 0]
        if not top_lines:
            top_lines = raw_lines[:2]
        
        excerpt = " · ".join(top_lines[:max_sentences])
        if len(excerpt) > max_chars:
            excerpt = excerpt[:max_chars].rsplit(" ", 1)[0] + "..."
        return excerpt

    # Otherwise, split into prose sentences
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    if not sentences:
        sentences = [clean]

    q_words = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_]+\b", query) if len(w) > 2]
    
    def score_sentence(s: str) -> int:
        s_lower = s.lower()
        return sum(1 for w in q_words if w in s_lower)

    ranked_sentences = sorted(sentences, key=score_sentence, reverse=True)
    best_sentences = [s for s in ranked_sentences if score_sentence(s) > 0]
    
    if not best_sentences:
        best_sentences = sentences[:max_sentences]
    else:
        # Keep original order among top sentences
        best_set = set(best_sentences[:max_sentences])
        best_sentences = [s for s in sentences if s in best_set][:max_sentences]

    excerpt = " ".join(best_sentences).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars].rsplit(" ", 1)[0] + "..."
    return excerpt


def build_evidence_items(retrieved_chunks: List[Dict[str, Any]], query: str = "") -> List[EvidenceItem]:
    """
    Build structured evidence items from retrieved chunks.
    """
    evidence = []
    seen_texts = set()

    for chunk in retrieved_chunks:
        text = chunk.get("text", "").strip()
        if not text or text in seen_texts:
            continue
        seen_texts.add(text)

        metadata = chunk.get("metadata", {})
        page = metadata.get("page")
        if page == -1:
            page = None

        excerpt = extract_relevant_excerpt(text, query=query, max_sentences=2, max_chars=250)
        relevance = chunk.get("relevance", chunk.get("similarity", 0.0))

        evidence.append(EvidenceItem(
            document=metadata.get("document", "Unknown"),
            page=page,
            quote=excerpt,
            chunk_index=metadata.get("chunk_index", 0),
            section=metadata.get("section") or None,
            source_type=metadata.get("source_type", "unknown"),
            similarity_score=round(relevance, 4),
        ))

    return evidence


def build_source_citations(retrieved_chunks: List[Dict[str, Any]], query: str = "") -> List[SourceCitation]:
    """
    Build structured source citations for display.
    Includes short relevant excerpts (1-3 sentences max) and relevance score.
    Deduplicates by document + page.
    """
    sources = []
    seen_sources = set()

    for chunk in retrieved_chunks:
        metadata = chunk.get("metadata", {})
        doc = metadata.get("document", "Unknown")
        page = metadata.get("page")
        if page == -1:
            page = None

        source_key = (doc, page)
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)

        excerpt = extract_relevant_excerpt(chunk.get("text", ""), query=query, max_sentences=2, max_chars=220)
        relevance = round(float(chunk.get("relevance", chunk.get("similarity", 0.0))), 4)

        sources.append(SourceCitation(
            document=doc,
            page=page,
            excerpt=excerpt,
            relevance=relevance,
            relevant_text=excerpt,
            similarity_score=relevance,
            chunk_index=metadata.get("chunk_index", 0),
        ))

    return sources


def format_evidence_for_prompt(retrieved_chunks: List[Dict[str, Any]], query: str = "") -> str:
    """
    Format retrieved evidence for the LLM prompt context cleanly and concisely.
    """
    if not retrieved_chunks:
        return "No relevant evidence found in the documents."

    parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        metadata = chunk.get("metadata", {})
        doc = metadata.get("document", "Unknown")
        page = metadata.get("page")
        if page == -1:
            page = None

        page_str = f"Page {page}" if page else "Page N/A"
        relevance = chunk.get("relevance", chunk.get("similarity", 0.0))
        
        # Pass chunk text (cleaned of excessive whitespace)
        clean_text = "\n".join(l.strip() for l in chunk.get("text", "").splitlines() if l.strip())

        parts.append(
            f"SOURCE {i}: {doc} ({page_str}) [Relevance: {relevance:.2f}]\n"
            f"{clean_text}\n"
        )

    return "\n---\n".join(parts)
