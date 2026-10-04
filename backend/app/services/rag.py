"""
RAG Pipeline Service.
Orchestrates:
1. QUESTION UNDERSTANDING & INTENT CLASSIFICATION (query expansion, pronoun/context handling)
2. MULTI-QUERY SEMANTIC RETRIEVAL (vector search across expanded candidates)
3. DOCUMENT OVERVIEW FALLBACK (representative chunks for broad queries)
4. RELEVANCE FILTERING & RERANKING (intent extraction, keyword matching, thresholding)
5. CONFLICT ANALYSIS (discrepancy detection on relevant evidence only)
6. NATURAL ANSWER GENERATION (LLM JSON output or smart natural language synthesizer)
7. SOURCE FORMATTING (short excerpts, relevance scores, and citations)
8. FRONTEND PRESENTATION ASSEMBLE
"""

import logging
import time
import uuid
import json
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from openai import OpenAI
from pydantic import ValidationError

from app.config import settings
from app.models.schemas import (
    InvestigationResult,
    InvestigationStatus,
    ConfidenceLevel,
    EvidenceItem,
    SourceCitation,
    ConflictDetail,
    LLMAnswerOutput,
)
from app.services.embeddings import generate_query_embedding
from app.services.vector_store import (
    search_documents,
    search_documents_multi,
    get_document_overview,
    get_collection_stats,
    get_all_documents,
)
from app.services.query_understanding import (
    understand_question,
    QuestionIntent,
    is_document_overview_question,
)
from app.services.relevance import filter_and_rerank_chunks, detect_question_intent
from app.services.conflict_detector import analyze_conflicts
from app.services.confidence import compute_confidence
from app.services.citation import (
    build_evidence_items,
    build_source_citations,
    format_evidence_for_prompt,
    extract_relevant_excerpt,
)

logger = logging.getLogger(__name__)

# ─── System Prompt for LLM ───────────────────────────────────────────────────

INVESTIGATOR_SYSTEM_PROMPT = """You are an evidence-grounded document investigator.

Understand the user's natural-language question before answering.
The user may use synonyms, informal language, pronouns, or broad questions.
Use the supplied document evidence to answer naturally.
Never require exact keyword matches.
For broad document questions, summarize the relevant document content.
Use only information supported by the uploaded documents.
Never use outside knowledge.
If evidence is insufficient, clearly say so.
If multiple documents disagree, explain the disagreement instead of choosing one silently.
Do not expose retrieval mechanics, embeddings, vector databases, chunks, or internal evidence IDs.
Write concise, natural, human-readable answers.
Cite relevant documents and page numbers separately.

Return valid JSON only matching the schema:
{
  "answer": "Natural language answer directly addressing the question.",
  "status": "SUPPORTED | PARTIALLY_SUPPORTED | CONFLICTING | INSUFFICIENT_EVIDENCE",
  "confidence": "HIGH | MEDIUM | LOW",
  "uncertainty": "Only if meaningful uncertainty or conflict exists, otherwise null",
  "evidence_points": [
    "Short supporting point 1",
    "Short supporting point 2"
  ],
  "source_ids": [1, 2]
}"""

USER_PROMPT_TEMPLATE = """USER QUESTION:
{question}

RELEVANT DOCUMENT EVIDENCE:
{evidence_context}

{conflict_context}

Return valid structured JSON matching the required schema."""


def build_openai_client() -> Optional[OpenAI]:
    """Create OpenAI client with API key and optional base URL from settings."""
    key = settings.LLM_API_KEY.strip() if settings.LLM_API_KEY else ""
    if not key or key.startswith("YOUR_") or key == "none":
        return None
    base_url = settings.LLM_BASE_URL.strip() if getattr(settings, "LLM_BASE_URL", None) else None
    if base_url:
        return OpenAI(api_key=key, base_url=base_url, timeout=10.0)
    return OpenAI(api_key=key, timeout=10.0)


# ─── Dynamic Document Structure & Sentence Extraction Engine ─────────────────

def extract_document_structure(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Dynamically analyze retrieved document chunks to extract:
    - title: Stated document title (from first chunk/page 1)
    - author_info: Stated author(s), affiliations, or presenter
    - doc_type: 'research article', 'policy document', 'technical resume', 'lecture presentation', or 'document'
    - abstract_or_summary: Stated abstract, profile summary, executive summary, or lead sentences
    - key_topics: Extracted keywords, index terms, or section headings
    """
    if not chunks:
        return {
            "title": "Document",
            "author_info": "",
            "doc_type": "document",
            "abstract_or_summary": "",
            "key_topics": [],
        }

    first_chunk = chunks[0]
    first_text = first_chunk.get("text", "")
    lines = [line.strip() for line in first_text.splitlines() if line.strip()]

    # Extract title from the top lines of chunk 0
    title_lines = []
    for line in lines[:4]:
        line_l = line.lower()
        if any(marker in line_l for marker in [
            "email", "abstract", "keywords:", "index terms:", "author",
            "department", "university", "faculty", "phone:", "tel:",
            "curriculum vitae", "table of contents", "confidential"
        ]) or "@" in line or re.match(r"^[0-9\+\(\)]", line):
            break
        title_lines.append(line)
        if len(" ".join(title_lines)) > 140:
            break

    if title_lines:
        title = " ".join(title_lines)
        title = re.sub(r"^[●\-\*\d\.\s#]+", "", title).strip()
    else:
        doc_filename = first_chunk.get("metadata", {}).get("document", "Document")
        title = doc_filename.rsplit(".", 1)[0].replace("_", " ").title()

    all_first_text = " ".join([c.get("text", "") for c in chunks[:4]])
    all_first_lower = all_first_text.lower()

    # Detect document type dynamically based on content signatures
    if any(k in all_first_lower for k in ["abstract", "index terms:", "keywords:", "ieee", "doi:", "case studies", "references\n", "methodology"]):
        doc_type = "research article"
    elif any(k in all_first_lower for k in ["policy", "effective date", "entitlement", "regulations", "employee handbook", "leave policy"]):
        doc_type = "policy document"
    elif any(k in all_first_lower for k in ["profile summary", "curriculum vitae", "relevant coursework"]) or (
        "education" in all_first_lower and "technical skills" in all_first_lower and "projects" in all_first_lower
    ):
        doc_type = "technical resume"
    elif any(k in all_first_lower for k in ["lecture", "module", "slides", "syllabus", "natural computing"]):
        doc_type = "lecture presentation"
    elif any(k in all_first_lower for k in ["report", "executive summary", "financial overview"]):
        doc_type = "technical report"
    else:
        doc_type = "document"

    # Extract author or organization
    author_info = ""
    for line in lines[len(title_lines):min(len(lines), len(title_lines) + 8)]:
        line_l = line.lower()
        if "@" in line or any(k in line_l for k in ["university", "institute", "college", "school", "corporation", "inc.", "dept", "department", "author", "lecturer"]):
            clean_l = re.sub(r"^[●\-\*\s]+", "", line).strip()
            if len(clean_l) > 3 and not any(k in clean_l.lower() for k in ["keywords", "abstract"]):
                author_info = clean_l
                break
        elif re.search(r"^[A-Z][a-zA-Z\s\.\(\)\d\-]{3,50}$", line) and not any(k in line_l for k in ["keywords", "abstract", "index terms", "title", "content"]):
            author_info = line.strip()
            break

    # Extract abstract / summary
    abstract_text = ""
    abs_match = re.search(
        r"(?:abstract|profile\s+summary|executive\s+summary|overview)[\s\-\–:]+(.*?)(?=\n\s*(?:[I|1]\.\s+[A-Z]|keywords|index\s+terms|relevant\s+coursework|projects|skills|\n\n)|\Z)",
        all_first_text,
        re.DOTALL | re.IGNORECASE,
    )
    if abs_match:
        raw_abs = " ".join(abs_match.group(1).split())
        sentences = re.split(r"(?<=[.!?])\s+", raw_abs)
        trimmed = ""
        for s in sentences:
            if len(trimmed) + len(s) < 450:
                trimmed += (" " if trimmed else "") + s
            else:
                break
        abstract_text = trimmed if trimmed else raw_abs[:350]

    # Extract index terms / keywords
    key_topics = []
    kw_match = re.search(r"(?:index\s+terms|keywords|topics)[:\-\s]+(.*?)(?=\n|\Z)", all_first_text, re.IGNORECASE)
    if kw_match:
        key_topics = [t.strip() for t in re.split(r"[,;•]+", kw_match.group(1)) if len(t.strip()) > 2]

    return {
        "title": title,
        "author_info": author_info,
        "doc_type": doc_type,
        "abstract_or_summary": abstract_text,
        "key_topics": key_topics[:6],
    }


def compute_token_overlap(text_a: str, text_b: str) -> float:
    """Compute token Jaccard similarity to prevent duplicate sentences in answers."""
    tokens_a = set(re.findall(r"\b[a-zA-Z]{3,}\b", text_a.lower()))
    tokens_b = set(re.findall(r"\b[a-zA-Z]{3,}\b", text_b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def extract_relevant_sentences(
    query: str,
    chunks: List[Dict[str, Any]],
    max_sentences: int = 3,
    min_score: float = 0.15,
) -> List[str]:
    """
    Dynamically extract the most relevant, non-redundant sentences from retrieved chunks
    based on query keyword overlap, intent indicators, and semantic informativeness.
    """
    from app.services.relevance import extract_query_keywords, STOP_WORDS

    q_tokens = extract_query_keywords(query)
    q_lower = query.lower()

    all_sentences = []
    seen_texts = set()

    for chunk in chunks:
        text = chunk.get("text", "")
        raw_sents = re.split(r"(?<=[.!?])\s+|\n+", text)
        for s in raw_sents:
            cleaned = re.sub(r"^[●\-\*\d\.\s#]+", "", s).strip()
            if len(cleaned) < 20 or cleaned.startswith("http") or cleaned in seen_texts:
                continue
            seen_texts.add(cleaned)

            s_lower = cleaned.lower()
            score = 0.0

            # 1. Keyword coverage
            if q_tokens:
                kw_matches = sum(1 for kw in q_tokens if re.search(r"\b" + re.escape(kw) + r"\b", s_lower))
                score += (kw_matches / len(q_tokens)) * 0.60

            # 2. Phrase matching
            words = q_lower.split()
            if len(words) >= 2:
                for i in range(len(words) - 1):
                    pair = f"{words[i]} {words[i+1]}"
                    if pair not in STOP_WORDS and pair in s_lower:
                        score += 0.25
                        break

            # 3. Intent-specific bonuses
            if any(k in q_lower for k in ["when", "date", "year", "time"]):
                if re.search(r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}|january|february|march|april|may|june|july|august|september|october|november|december)\b", s_lower):
                    score += 0.35

            if any(k in q_lower for k in ["who", "author", "lecturer", "founder", "created", "developed"]):
                if re.search(r"\b(?:dr\.?|prof\.?|mr\.?|ms\.?|ph\.?d|thesis|by|lecturer|author|intern)\b", s_lower) or any(w[0].isupper() for w in cleaned.split() if len(w) > 2):
                    score += 0.30

            if any(k in q_lower for k in ["phone", "contact", "email", "number"]):
                if re.search(r"\b(?:\d{3,5}[\s\-]?\d{3,6}|phone|tel|email|@)\b", s_lower):
                    score += 0.45

            if any(k in q_lower for k in ["skill", "skills", "technolog", "language", "framework", "tool"]):
                if any(w in s_lower for w in ["languages:", "skills:", "frameworks:", "tools:", "proficient", "programming"]):
                    score += 0.40

            if any(k in q_lower for k in ["project", "projects", "application", "applications", "built"]):
                if any(w in s_lower for w in ["project", "developed", "built", "application", "system", "case study", "routing"]):
                    score += 0.35

            if any(k in q_lower for k in ["rule", "rules", "policy", "regulations", "leave", "entitled"]):
                if any(w in s_lower for w in ["policy", "leave", "entitled", "days", "rules", "must", "shall", "required"]):
                    score += 0.35

            if score >= min_score:
                all_sentences.append((cleaned, score))

    all_sentences.sort(key=lambda x: x[1], reverse=True)

    selected: List[str] = []
    for sent, score in all_sentences:
        if not any(compute_token_overlap(sent, sel) > 0.65 for sel in selected):
            selected.append(sent)
            if len(selected) >= max_sentences:
                break

    return selected


# ─── Natural Fallback Synthesizer ─────────────────────────────────────────────

def synthesize_natural_answer(
    question: str,
    chunks: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    confidence_level: ConfidenceLevel,
    all_chunks: Optional[List[Dict[str, Any]]] = None,
    intent: Optional[QuestionIntent] = None,
    is_overview: bool = False,
) -> Tuple[str, InvestigationStatus, List[str], Optional[str]]:
    """
    Dynamically synthesize a natural, question-specific answer from document evidence.
    Completely general and extractively grounded in the retrieved chunks.
    """
    q_lower = question.lower()

    # 1. Handle conflicts only when relevant to the user query
    conflict_relevant = False
    if conflicts:
        if intent in (QuestionIntent.CONFLICT_DETECTION, QuestionIntent.COMPARISON):
            conflict_relevant = True
        else:
            keywords_to_check = ["leave", "medical", "days", "policy", "disagree", "conflict", "contradict", "difference", "differ", "discrepancy"]
            if any(k in q_lower for k in keywords_to_check):
                conflict_relevant = True

    if conflict_relevant and conflicts:
        c = conflicts[0]
        src_a = c.get("source_a", {})
        src_b = c.get("source_b", {})
        doc_a = src_a.get("document", "Document A")
        doc_b = src_b.get("document", "Document B")
        val_a = src_a.get("value") or src_a.get("quote", "")[:100].strip()
        val_b = src_b.get("value") or src_b.get("quote", "")[:100].strip()

        answer = (
            f"The documents contain conflicting information. {doc_a} states that {val_a}, "
            f"while {doc_b} states {val_b}. The available documents therefore do not "
            f"establish one definitive value."
        )
        points = [
            f"{doc_a} indicates {val_a}",
            f"{doc_b} indicates {val_b}",
        ]
        uncertainty = "Discrepancy detected across indexed documents on this topic."
        return answer, InvestigationStatus.CONFLICTING, points, uncertainty

    # 2. Out of scope
    if intent == QuestionIntent.OUT_OF_SCOPE:
        return (
            "This investigator answers questions using the uploaded documents. I couldn't find evidence relevant to that request.",
            InvestigationStatus.INSUFFICIENT_EVIDENCE,
            [],
            "The query does not pertain to the content of the indexed documents."
        )

    if not chunks and not all_chunks:
        return (
            "I couldn't find sufficient information in the provided documents to answer this question.",
            InvestigationStatus.INSUFFICIENT_EVIDENCE,
            [],
            "The available documents do not contain relevant information to answer this question."
        )

    search_chunks = all_chunks if all_chunks else chunks
    meta = extract_document_structure(search_chunks)

    # ── 3. BROAD OVERVIEW / DOCUMENT SUMMARY ──────────────────────────────────
    if is_overview or intent in (QuestionIntent.DOCUMENT_OVERVIEW, QuestionIntent.DOCUMENT_SUMMARY):
        title = meta["title"]
        doc_type = meta["doc_type"]
        author = meta["author_info"]
        author_clause = f" by {author}" if author else ""
        abstract = meta["abstract_or_summary"]

        if abstract:
            clean_abs = abstract.strip()
            if not clean_abs.endswith("."):
                clean_abs += "."
            # Seamless natural lead-in
            if clean_abs.lower().startswith("this "):
                answer = f"This {doc_type} titled '{title}'{author_clause} presents the following:\n\n{clean_abs}"
            else:
                answer = f"This {doc_type} titled '{title}'{author_clause} covers:\n\n{clean_abs}"
        else:
            top_sents = extract_relevant_sentences("summary overview main topic content", search_chunks[:3], max_sentences=2)
            if top_sents:
                answer = f"This {doc_type} titled '{title}'{author_clause} discusses: {' '.join(top_sents)}"
            else:
                answer = f"This {doc_type} is titled '{title}'{author_clause}."

        # Dynamic evidence points
        points = [f"Title: {title} ({doc_type.title()})"]
        if author:
            points.append(f"Author / Institution: {author}")
        if meta["key_topics"]:
            points.append(f"Core Topics: {', '.join(meta['key_topics'])}")
        elif abstract:
            points.append(f"Summary: {abstract[:130]}...")

        return answer, InvestigationStatus.SUPPORTED, points, None

    # ── 4. KEY POINTS ─────────────────────────────────────────────────────────
    if intent == QuestionIntent.KEY_POINTS or any(w in q_lower for w in ["key point", "main point", "important thing"]):
        top_sents = extract_relevant_sentences("main key important findings overview conclusion", search_chunks, max_sentences=4)
        if not top_sents:
            top_sents = [c.get("text", "")[:120].strip() for c in search_chunks[:3]]

        numbered_points = "\n".join([f"{i+1}. {s}" for i, s in enumerate(top_sents)])
        answer = f"The main points of the document include:\n{numbered_points}"
        return answer, InvestigationStatus.SUPPORTED, top_sents, None

    # ── 5. SPECIFIC INTENT: RULES & POLICIES ──────────────────────────────────
    if intent == QuestionIntent.RULE_LOOKUP or any(w in q_lower for w in ["rule", "rules", "policy", "regulations", "guideline"]):
        rule_sents = extract_relevant_sentences("policy rules regulations leave entitled must shall required", search_chunks, max_sentences=3)
        if not rule_sents:
            return (
                "I couldn't find any rules, regulations, or policies mentioned in the provided document.",
                InvestigationStatus.INSUFFICIENT_EVIDENCE,
                [],
                "The available documents do not contain rules or policy guidelines relevant to this query."
            )
        answer = " ".join(rule_sents)
        if not answer.endswith("."):
            answer += "."
        return answer, InvestigationStatus.SUPPORTED, rule_sents, None

    # ── 6. SPECIFIC INTENT: SKILLS / TECHNOLOGIES ─────────────────────────────
    if intent == QuestionIntent.SKILLS_LOOKUP or any(w in q_lower for w in ["skill", "skills", "technolog", "programming language", "tools", "framework"]):
        skill_sents = extract_relevant_sentences("technical skills programming languages frameworks tools technologies competencies", search_chunks, max_sentences=3)
        if not skill_sents:
            return (
                "I couldn't find information about technical skills or qualifications in the provided document.",
                InvestigationStatus.INSUFFICIENT_EVIDENCE,
                [],
                "The available documents do not specify technical skills."
            )
        answer = " ".join(skill_sents)
        if not answer.endswith("."):
            answer += "."
        return answer, InvestigationStatus.SUPPORTED, skill_sents, None

    # ── 7. SPECIFIC INTENT: PROJECTS / CASE STUDIES ───────────────────────────
    if intent == QuestionIntent.PROJECT_LOOKUP or any(w in q_lower for w in ["project", "projects", "case study", "case studies", "applications"]):
        proj_sents = extract_relevant_sentences("projects developed applications systems case studies implementations", search_chunks, max_sentences=3)
        if not proj_sents:
            return (
                "I couldn't find project or application information in the provided document.",
                InvestigationStatus.INSUFFICIENT_EVIDENCE,
                [],
                "The available documents do not describe specific projects or case studies."
            )
        answer = " ".join(proj_sents)
        if not answer.endswith("."):
            answer += "."
        return answer, InvestigationStatus.SUPPORTED, proj_sents, None

    # ── 8. SPECIFIC INTENT: EDUCATION ─────────────────────────────────────────
    if intent == QuestionIntent.EDUCATION_LOOKUP or any(w in q_lower for w in ["education", "degree", "university", "college", "school", "cgpa", "study"]):
        edu_sents = extract_relevant_sentences("education degree university college school bachelor master cgpa percentage", search_chunks, max_sentences=3)
        if not edu_sents:
            return (
                "I couldn't find educational background information in the provided document.",
                InvestigationStatus.INSUFFICIENT_EVIDENCE,
                [],
                "The available documents do not contain educational qualifications."
            )
        answer = " ".join(edu_sents)
        if not answer.endswith("."):
            answer += "."
        return answer, InvestigationStatus.SUPPORTED, edu_sents, None

    # ── 9. GENERAL DYNAMIC FACT EXTRACTION ────────────────────────────────────
    matched_sents = extract_relevant_sentences(question, search_chunks, max_sentences=3)

    if matched_sents:
        answer = " ".join(matched_sents)
        if not answer.endswith("."):
            answer += "."
        status = InvestigationStatus.SUPPORTED if confidence_level == ConfidenceLevel.HIGH else InvestigationStatus.PARTIALLY_SUPPORTED
        uncertainty = None if status == InvestigationStatus.SUPPORTED else "Answer is synthesized from the most relevant retrieved passages."
        return answer, status, matched_sents, uncertainty

    return (
        "I couldn't find sufficient information in the provided documents to answer this question.",
        InvestigationStatus.INSUFFICIENT_EVIDENCE,
        [],
        "The available documents do not contain relevant information to answer this question."
    )


# ─── Main Investigation Workflow ──────────────────────────────────────────────

async def run_investigation(question: str) -> InvestigationResult:
    """
    Execute the complete natural-language RAG investigation pipeline:
    1. Question Understanding & Intent Classification
    2. Multi-Query Semantic Retrieval
    3. Document Overview Fallback (if broad question)
    4. Relevance Filtering & Reranking
    5. Conflict Analysis
    6. Answer Generation (LLM / intelligent synthesizer)
    7. Source Formatting & Presentation
    """
    start_time = time.time()
    investigation_id = str(uuid.uuid4())

    logger.info(f"[{investigation_id}] Starting investigation: '{question[:80]}'")

    # ── Check collection stats ────────────────────────────────────────────────
    stats = get_collection_stats()
    if stats.get("total_chunks", 0) == 0:
        return InvestigationResult(
            investigation_id=investigation_id,
            question=question,
            answer="No documents have been uploaded yet. Please upload documents first.",
            status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
            confidence=0.0,
            confidence_level=ConfidenceLevel.LOW,
            confidence_explanation="No documents indexed in the system.",
            uncertainty="No documents available. Upload PDF, DOCX, TXT, or image files to begin.",
            evidence_points=[],
            evidence=[],
            conflicts=[],
            sources=[],
            timestamp=datetime.utcnow().isoformat(),
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # ── Stage 1: QUESTION UNDERSTANDING & INTENT CLASSIFICATION ───────────────
    available_docs = get_all_documents()
    analysis = understand_question(question, available_documents=available_docs)
    intent = analysis["intent"]
    is_overview = analysis["is_overview"]
    is_out_of_scope = analysis["is_out_of_scope"]
    expanded_queries = analysis["expanded_queries"]
    target_document = analysis["target_document"]

    # Handle out-of-scope queries (jokes, weather, chit-chat)
    if is_out_of_scope:
        processing_time_ms = int((time.time() - start_time) * 1000)
        return InvestigationResult(
            investigation_id=investigation_id,
            question=question,
            answer="This investigator answers questions using the uploaded documents. I couldn't find evidence relevant to that request.",
            status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
            confidence=0.0,
            confidence_level=ConfidenceLevel.LOW,
            confidence_explanation="The query is outside the scope of the uploaded documents.",
            uncertainty="The query does not pertain to the content of the indexed documents.",
            evidence_points=[],
            evidence=[],
            conflicts=[],
            sources=[],
            timestamp=datetime.utcnow().isoformat(),
            processing_time_ms=processing_time_ms,
        )

    # ── Stage 2: MULTI-QUERY SEMANTIC RETRIEVAL ───────────────────────────────
    try:
        query_embeddings = [
            generate_query_embedding(q, model_name=settings.EMBEDDING_MODEL)
            for q in expanded_queries
        ]
    except Exception as e:
        logger.error(f"Query embedding generation failed: {e}")
        raise RuntimeError(f"Failed to process your question: {e}")

    try:
        collection_size = stats.get("total_chunks", 50)
        raw_chunks = search_documents_multi(
            query_embeddings=query_embeddings,
            top_k=max(collection_size, 30),
            document_filter=target_document,
        )
        logger.info(f"[{investigation_id}] Multi-query retrieval fetched {len(raw_chunks)} chunks")
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise RuntimeError(f"Document search failed: {e}")

    # ── Stage 3: DOCUMENT OVERVIEW FALLBACK ────────────────────────────────────
    # For broad document questions, fetch representative chunks and combine them
    if is_overview:
        overview_chunks = get_document_overview(filename=target_document, top_k=6)
        existing_ids = {c["id"] for c in raw_chunks}
        for oc in overview_chunks:
            if oc["id"] not in existing_ids:
                raw_chunks.append(oc)
                existing_ids.add(oc["id"])
        logger.info(f"[{investigation_id}] Added {len(overview_chunks)} document overview chunks")

    # ── Stage 4: RELEVANCE FILTERING & RERANKING ──────────────────────────────
    relevant_chunks, is_insufficient = filter_and_rerank_chunks(
        query=question,
        chunks=raw_chunks,
        top_k=5 if is_overview else 4,
        min_relevance_threshold=0.15,
        is_overview=is_overview,
        intent_override=detect_question_intent(question),
    )
    logger.info(
        f"[{investigation_id}] Relevance filter kept {len(relevant_chunks)} chunks "
        f"(is_insufficient={is_insufficient})"
    )

    # If relevance filtering identified no relevant chunks
    if is_insufficient or not relevant_chunks:
        if intent == QuestionIntent.RULE_LOOKUP:
            doc_struct = extract_document_structure(raw_chunks)
            doc_type = doc_struct.get("doc_type", "document")
            answer_text = f"I couldn't find any rules, regulations, or policies mentioned in the provided {doc_type}."
        else:
            answer_text = "I couldn't find sufficient information in the provided documents to answer this question."

        processing_time_ms = int((time.time() - start_time) * 1000)
        return InvestigationResult(
            investigation_id=investigation_id,
            question=question,
            answer=answer_text,
            status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
            confidence=0.0,
            confidence_level=ConfidenceLevel.LOW,
            confidence_explanation="No relevant evidence was found in the uploaded documents.",
            uncertainty="The available documents do not contain relevant information to answer this question.",
            evidence_points=[],
            evidence=[],
            conflicts=[],
            sources=[],
            timestamp=datetime.utcnow().isoformat(),
            processing_time_ms=processing_time_ms,
        )

    # ── Stage 5: CONFLICT ANALYSIS ────────────────────────────────────────────
    conflicts_raw = []
    try:
        conflicts_raw = analyze_conflicts(relevant_chunks)
        logger.info(f"[{investigation_id}] Detected {len(conflicts_raw)} conflicts in relevant evidence")
    except Exception as e:
        logger.warning(f"Conflict detection failed (non-fatal): {e}")

    conflicts: List[ConflictDetail] = []
    for c in conflicts_raw:
        try:
            conflicts.append(ConflictDetail(
                type=c.get("type", "unknown"),
                topic=c.get("topic", "discrepancy"),
                description=c.get("description", ""),
                source_a=c.get("source_a", {}),
                source_b=c.get("source_b", {}),
                why_it_matters=(
                    "The available documents disagree, so the system cannot establish a single definitive answer."
                ),
            ))
        except Exception:
            pass

    # ── Stage 6: CONFIDENCE SCORING ───────────────────────────────────────────
    confidence, confidence_level, confidence_explanation = compute_confidence(
        retrieved_chunks=relevant_chunks,
        conflicts=conflicts_raw,
        top_k=len(relevant_chunks),
    )

    # For overview questions where representative chunks exist, ensure high confidence
    if is_overview and relevant_chunks and confidence < 0.85:
        confidence = 0.90
        confidence_level = ConfidenceLevel.HIGH
        confidence_explanation = "Document overview synthesized directly from representative document content."

    # ── Stage 7: SOURCE FORMATTING ────────────────────────────────────────────
    # Post-filter: Remove off-topic sources from other documents when one document dominates
    primary_docs = {c.get("metadata", {}).get("document") for c in relevant_chunks[:2]}
    filtered_chunks_for_sources = relevant_chunks
    if len(primary_docs) >= 1:
        top_doc = relevant_chunks[0].get("metadata", {}).get("document")
        top_relevance = relevant_chunks[0].get("relevance", 0.0)
        if top_relevance >= 0.50:
            filtered_chunks_for_sources = [
                c for c in relevant_chunks
                if (
                    c.get("metadata", {}).get("document") == top_doc
                    or c.get("relevance", 0.0) >= 0.65
                )
            ]
            if not filtered_chunks_for_sources:
                filtered_chunks_for_sources = relevant_chunks

    source_citations = build_source_citations(filtered_chunks_for_sources, query=question)
    evidence_items = build_evidence_items(filtered_chunks_for_sources, query=question)
    evidence_context = format_evidence_for_prompt(relevant_chunks, query=question)

    conflict_context = ""
    if conflicts:
        conflict_context = "CONFLICTING EVIDENCE FOUND ACROSS DOCUMENTS:\n"
        for idx, conf in enumerate(conflicts, 1):
            conflict_context += (
                f"- Conflict {idx} ({conf.topic}): "
                f"Source A ({conf.source_a.get('document')}) says '{conf.source_a.get('value', '')}' "
                f"vs Source B ({conf.source_b.get('document')}) says '{conf.source_b.get('value', '')}'\n"
            )

    # ── Stage 8: ANSWER GENERATION ────────────────────────────────────────────
    final_answer: str = ""
    final_status: InvestigationStatus = InvestigationStatus.SUPPORTED
    final_points: List[str] = []
    final_uncertainty: Optional[str] = None

    client = build_openai_client()
    llm_succeeded = False

    if client is not None:
        try:
            user_prompt = USER_PROMPT_TEMPLATE.format(
                question=question,
                evidence_context=evidence_context,
                conflict_context=conflict_context,
            )

            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": INVESTIGATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=800,
            )
            raw_json = response.choices[0].message.content.strip()

            try:
                parsed_data = json.loads(raw_json)
                parsed_llm = LLMAnswerOutput(**parsed_data)
                final_answer = parsed_llm.answer.strip()
                final_status = parsed_llm.status
                final_points = parsed_llm.evidence_points
                final_uncertainty = parsed_llm.uncertainty
                llm_succeeded = True
                logger.info(f"[{investigation_id}] LLM structured response generated successfully")
            except (json.JSONDecodeError, ValidationError) as parse_err:
                logger.warning(f"[{investigation_id}] JSON parse failed ({parse_err}), using synthesizer")
        except Exception as e:
            logger.warning(f"[{investigation_id}] LLM call error: {e}. Using natural synthesizer.")

    if not llm_succeeded:
        (
            final_answer,
            final_status,
            final_points,
            final_uncertainty,
        ) = synthesize_natural_answer(
            question=question,
            chunks=relevant_chunks,
            conflicts=conflicts_raw,
            confidence_level=confidence_level,
            all_chunks=raw_chunks,
            intent=intent,
            is_overview=is_overview,
        )

    # Clean up uncertainty
    if final_uncertainty and (
        "strictly from indexed document" in final_uncertainty.lower()
        or final_uncertainty.strip() == ""
    ):
        final_uncertainty = None

    if conflicts and not final_uncertainty:
        final_uncertainty = "Two or more sources provide conflicting values on this topic."

    processing_time_ms = int((time.time() - start_time) * 1000)

    result = InvestigationResult(
        investigation_id=investigation_id,
        question=question,
        answer=final_answer,
        status=final_status,
        confidence=confidence,
        confidence_level=confidence_level,
        confidence_explanation=confidence_explanation,
        uncertainty=final_uncertainty,
        evidence_points=final_points,
        evidence=evidence_items,
        conflicts=conflicts,
        sources=source_citations,
        timestamp=datetime.utcnow().isoformat(),
        processing_time_ms=processing_time_ms,
    )

    logger.info(
        f"[{investigation_id}] Complete in {processing_time_ms}ms. "
        f"Status: {final_status} | Confidence: {confidence_level} ({confidence:.2f})"
    )
    return result
