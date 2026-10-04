"""
Relevance Filtering and Reranking Service.

Filters retrieved candidate chunks, applies hybrid scoring (dense + lexical + intent),
and identifies when evidence is truly insufficient or irrelevant.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional, Set

logger = logging.getLogger(__name__)

STOP_WORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by",
    "from", "about", "into", "through", "after", "over", "between", "out",
    "against", "during", "without", "before", "under", "around", "among",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "can", "could", "should", "would", "will", "shall",
    "and", "or", "but", "if", "then", "else", "when", "where", "why", "how",
    "what", "who", "whom", "which", "this", "that", "these", "those",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us",
    "them", "my", "your", "his", "its", "our", "their", "mine", "yours",
    "hers", "ours", "theirs", "please", "tell", "give", "show", "find",
    "mentioned", "provided", "documents", "given", "get", "any", "candidate",
}

# Generic words that should NEVER be used as discriminating topic indicators
GENERIC_WORDS: Set[str] = {
    "given", "when", "where", "what", "which", "company", "policy",
    "leave", "please", "type", "kind", "sort", "make", "like",
    "information", "topic", "subject", "related", "document", "documents",
    "file", "files", "mainly", "summary", "summarize", "point", "points",
    "main", "content", "contents", "overview", "important", "contain",
    "contains", "mention", "mentioned", "describe", "described", "detail",
    "details", "explain", "explanation", "understand", "give", "tell",
    "show", "know", "person", "paper", "about", "thing", "things"
}


def extract_query_keywords(query: str) -> List[str]:
    """Extract meaningful search tokens from a question."""
    tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", query.lower())
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


def extract_topic_discriminators(keywords: List[str]) -> List[str]:
    """
    Extract keywords that are true domain-specific discriminators:
    - Length >= 5 characters
    - Not a generic English query/document word
    - Not a stop word or pure digit
    """
    return [
        k for k in keywords
        if len(k) >= 5
        and k not in GENERIC_WORDS
        and k not in STOP_WORDS
        and not k.isdigit()
    ]


def detect_question_intent(query: str) -> Dict[str, Any]:
    """
    Detect semantic intent signals and extract person names/entities.
    """
    q_lower = query.lower()
    words = query.split()
    person_name_candidates = []
    stop_names = {"What", "Who", "Where", "When", "Why", "How", "Can", "Could", "Which", "Is", "Are", "The", "This"}
    for w in words:
        cleaned = re.sub(r"[^a-zA-Z]", "", w)
        if cleaned and cleaned[0].isupper() and len(cleaned) >= 3 and cleaned not in stop_names:
            person_name_candidates.append(cleaned.lower())

    intent = {
        "is_who": bool(re.search(r"\bwho\b", q_lower)),
        "is_when": bool(re.search(r"\bwhen\b|\bdate\b|\bwhat time\b|\byear\b", q_lower)),
        "is_phone": bool(re.search(r"\bphone\b|\btelephone\b|\bnumber\b|\bcontact\b|\bcall\b", q_lower)),
        "is_email": bool(re.search(r"\bemail\b|\be-mail\b|\bmail\b", q_lower)),
        "is_application": bool(re.search(r"\bapplication\b|\bapplications\b|\bapplied\b|\buse\s+case", q_lower)),
        "is_definition": bool(re.search(r"\bwhat is\b|\bwhat are\b|\bdefine\b|\bdefinition\b|\bexplain\b", q_lower)),
        "is_list": bool(re.search(r"\blist\b|\bwhat are\b|\bwhich\b", q_lower)),
        "is_skills": bool(re.search(r"\bskills?\b|\btechnolog(?:y|ies)\b|\blanguages?\b|\btools?\b|\bframeworks?\b|\btech\s+stack\b", q_lower)),
        "is_projects": bool(re.search(r"\bprojects?\b|\bworked\s+on\b|\bbuilt\b|\bportfolio\b", q_lower)),
        "is_experience": bool(re.search(r"\bexperience\b|\bintern(?:ship)?\b|\bjob\b|\bwork\b|\bcareer\b", q_lower)),
        "is_education": bool(re.search(r"\beducation\b|\bdegree\b|\buniversity\b|\bcollege\b|\bschool\b|\bcgpa\b|\bacademic\b", q_lower)),
        "is_rules": bool(re.search(r"\brules?\b|\bpolic(?:y|ies)\b|\bregulations?\b|\bguidelines?\b|\bentitled\b", q_lower)),
        "is_overview": bool(re.search(r"\b(?:mainly\s+about|about|summarize|summary|overview|key\s+points|main\s+points)\b", q_lower)),
        "person_names": person_name_candidates,
    }
    return intent


def compute_chunk_relevance(
    chunk: Dict[str, Any],
    query: str,
    keywords: List[str],
    intent: Dict[str, Any],
) -> float:
    """
    Compute a combined relevance score between 0.0 and 1.0 for a retrieved chunk.
    Balances dense similarity with lexical matching and intent-specific semantic bonuses.
    """
    text = chunk.get("text", "")
    text_lower = text.lower()
    dense_sim = float(chunk.get("similarity", 0.0))

    if not text:
        return 0.0

    # 1. Keyword coverage
    if keywords:
        kw_score = 0.0
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                kw_score += 1.0
            elif kw in text_lower:
                kw_score += 0.5
        kw_score = min(1.0, kw_score / len(keywords))
    else:
        kw_score = 0.5

    # 2. Person name matching bonus
    name_bonus = 0.0
    person_names = intent.get("person_names", [])
    if person_names:
        matched_names = sum(1 for name in person_names if name in text_lower)
        if matched_names:
            name_bonus = min(0.4, matched_names * 0.20)

    # 3. Intent-specific bonuses
    intent_bonus = 0.0

    if intent.get("is_overview"):
        # For overview queries, boost profile summaries, intro sections, and first chunks
        chunk_idx = chunk.get("metadata", {}).get("chunk_index", chunk.get("chunk_index", 99))
        if chunk_idx in (0, 1):
            intent_bonus += 0.35
        if any(h in text_lower for h in ["profile summary", "summary", "overview", "introduction", "about"]):
            intent_bonus += 0.30

    if intent.get("is_skills"):
        if any(w in text_lower for w in ["technical skills", "languages:", "frameworks:", "tools:", "skills", "proficient"]):
            intent_bonus += 0.40

    if intent.get("is_projects"):
        if any(w in text_lower for w in ["projects", "project", "developed a", "built a", "recommendation system", "smart map"]):
            intent_bonus += 0.35

    if intent.get("is_experience"):
        if any(w in text_lower for w in ["experience", "intern", "internship", "developed responsive", "collaborated with"]):
            intent_bonus += 0.35

    if intent.get("is_education"):
        if any(w in text_lower for w in ["education", "bachelor of technology", "university", "school", "cgpa", "intermediate"]):
            intent_bonus += 0.35

    if intent.get("is_rules"):
        if any(w in text_lower for w in ["policy", "rules", "regulations", "medical leave", "entitlement", "guideline"]):
            intent_bonus += 0.35

    if intent.get("is_when"):
        if re.search(
            r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b"
            r"|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2},? \d{4}\b"
            r"|\b\d{4}\b"
            r"|\blecture\b|\bdate\b|\bsession\b",
            text_lower
        ):
            intent_bonus += 0.30

    if intent.get("is_phone"):
        if re.search(r"\bphone\b|\b\d{3,5}[\s\-]?\d{1,3}[\s\-]?\d{3,6}\b|\btel\b", text_lower):
            intent_bonus += 0.45

    if intent.get("is_email"):
        if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text):
            intent_bonus += 0.45

    if intent.get("is_application"):
        if re.search(r"\bapplications?\b|\brouting\b|\bscheduling\b|\broutes?\b|\bproblem\b", text_lower):
            intent_bonus += 0.25

    if intent.get("is_who") and person_names:
        if any(n in text_lower for n in person_names):
            intent_bonus += 0.25

    # 4. Combined score
    score = (
        (0.35 * dense_sim)
        + (0.35 * kw_score)
        + name_bonus
        + min(0.40, intent_bonus)
    )
    return round(min(1.0, max(0.0, score)), 4)


def detect_document_bias(
    query: str,
    chunks: List[Dict[str, Any]],
    intent: Dict[str, Any],
) -> Optional[str]:
    """
    If the query contains a strong person name/org signal that indicates
    results should come from a specific document, return that document name.
    """
    person_names = intent.get("person_names", [])
    if not person_names:
        return None

    doc_name_counts: Dict[str, int] = {}
    for chunk in chunks:
        doc = chunk.get("metadata", {}).get("document", "")
        text_lower = chunk.get("text", "").lower()
        count = sum(1 for name in person_names if name in text_lower)
        if count > 0:
            doc_name_counts[doc] = doc_name_counts.get(doc, 0) + count

    if not doc_name_counts:
        return None

    best_doc = max(doc_name_counts, key=lambda d: doc_name_counts[d])
    if doc_name_counts[best_doc] >= 1:
        return best_doc
    return None


def filter_and_rerank_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 4,
    min_relevance_threshold: float = 0.15,
    is_overview: bool = False,
    intent_override: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Filter retrieved candidate chunks and keep only the most relevant ones.
    
    Returns:
        (relevant_chunks, is_insufficient_evidence)
    """
    if not chunks:
        return [], True

    keywords = extract_query_keywords(query)
    intent = intent_override or detect_question_intent(query)
    if is_overview:
        intent["is_overview"] = True

    preferred_doc = detect_document_bias(query, chunks, intent)

    scored_chunks = []
    for c in chunks:
        rel = compute_chunk_relevance(c, query, keywords, intent)
        chunk_copy = dict(c)
        chunk_copy["relevance"] = rel

        if preferred_doc:
            chunk_doc = c.get("metadata", {}).get("document", "")
            if chunk_doc == preferred_doc:
                chunk_copy["relevance"] = min(1.0, rel * 1.2)
            elif rel < 0.60:
                chunk_copy["relevance"] = rel * 0.5

        scored_chunks.append(chunk_copy)

    scored_chunks.sort(key=lambda x: x["relevance"], reverse=True)

    # If it's an overview query, NEVER reject due to topic discriminators!
    if not is_overview and not intent.get("is_overview"):
        topic_discriminators = extract_topic_discriminators(keywords)
        # Only apply discriminator check if we have distinct domain words
        # and the intent is not a broad functional search (skills, experience, projects)
        is_functional_query = (
            intent.get("is_skills")
            or intent.get("is_projects")
            or intent.get("is_experience")
            or intent.get("is_education")
        )
        if topic_discriminators and not is_functional_query:
            all_text = " ".join(c.get("text", "").lower() for c in chunks)
            matched_discriminators = [k for k in topic_discriminators if k in all_text]

            # If none of the specific domain words appear and top relevance is very low
            if not matched_discriminators and scored_chunks[0]["relevance"] < 0.40:
                logger.info(
                    f"Topic discriminators {topic_discriminators} absent from all evidence "
                    f"and top relevance {scored_chunks[0]['relevance']:.3f} < 0.40 → INSUFFICIENT_EVIDENCE"
                )
                return [], True

    filtered = [c for c in scored_chunks if c["relevance"] >= min_relevance_threshold]
    if not filtered:
        # If overview query, fall back to top scored chunks anyway
        if is_overview or intent.get("is_overview"):
            return scored_chunks[:top_k], False
        return [], True

    return filtered[:top_k], False
