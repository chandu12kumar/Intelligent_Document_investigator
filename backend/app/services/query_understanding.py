"""
Natural Language Query Understanding, Intent Classification, and Query Expansion Service.

Interprets natural language questions without requiring exact keyword matching.
Supports query rewriting, expansion, intent classification, pronoun/context handling,
and broad document overview detection.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class QuestionIntent(str, Enum):
    DOCUMENT_SUMMARY = "DOCUMENT_SUMMARY"
    DOCUMENT_OVERVIEW = "DOCUMENT_OVERVIEW"
    KEY_POINTS = "KEY_POINTS"
    FACT_LOOKUP = "FACT_LOOKUP"
    PERSON_LOOKUP = "PERSON_LOOKUP"
    DATE_LOOKUP = "DATE_LOOKUP"
    LOCATION_LOOKUP = "LOCATION_LOOKUP"
    SKILLS_LOOKUP = "SKILLS_LOOKUP"
    EXPERIENCE_LOOKUP = "EXPERIENCE_LOOKUP"
    PROJECT_LOOKUP = "PROJECT_LOOKUP"
    EDUCATION_LOOKUP = "EDUCATION_LOOKUP"
    RULE_LOOKUP = "RULE_LOOKUP"
    COMPARISON = "COMPARISON"
    CONFLICT_DETECTION = "CONFLICT_DETECTION"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    GENERAL_QUESTION = "GENERAL_QUESTION"


OVERVIEW_INTENTS: Set[QuestionIntent] = {
    QuestionIntent.DOCUMENT_SUMMARY,
    QuestionIntent.DOCUMENT_OVERVIEW,
    QuestionIntent.KEY_POINTS,
}

# Questions that are completely unrelated to document investigation
OUT_OF_SCOPE_PATTERNS = [
    r"^(?:tell\s+me\s+a\s+joke|make\s+me\s+laugh|say\s+something\s+funny)\b",
    r"^(?:what\s+is\s+the\s+weather|how\s+is\s+the\s+weather|weather\s+today|forecast)\b",
    r"^(?:hi|hello|hey|good\s+morning|good\s+afternoon|good\s+evening)\b[\s!.,?]*$",
    r"^(?:who\s+won\s+the\s+(?:super\s*bowl|world\s*cup|match|game))\b",
    r"^(?:write\s+a\s+(?:poem|song|story|essay))\b",
]

# Words that indicate broad document overview questions
OVERVIEW_PATTERNS = [
    r"\bwhat\s+is\s+this\s+document\s+(?:mainly\s+)?about\b",
    r"\bwhat\s+(?:is|are)\s+(?:this|the)\s+(?:document|file|paper|pdf)\b",
    r"\b(?:can\s+you\s+)?summarize\s+(?:this|the)\s+(?:document|file|paper|pdf|it)\b",
    r"\b(?:give\s+me\s+an?|what\s+is\s+the)\s+overview\s+of\s+(?:this|the)\b",
    r"\bwhat\s+does\s+this\s+document\s+(?:contain|say|talk\s+about)\b",
    r"\btell\s+me\s+what\s+this\s+document\s+contains\b",
    r"\bwhat\s+information\s+does\s+this\s+document\s+contain\b",
    r"\bwhat\s+should\s+i\s+know\s+from\s+this\s+document\b",
    r"\bexplain\s+this\s+document(?:\s+in\s+simple\s+words)?\b",
    r"\bwhat\s+is\s+the\s+main\s+purpose\s+of\s+this\s+document\b",
    r"\bwhat\s+is\s+this\s+(?:file|resume|paper|policy)\s+(?:mainly\s+)?about\b",
]

KEY_POINTS_PATTERNS = [
    r"\b(?:main|key|important)\s+(?:points|takeaways|highlights|aspects|things)\b",
    r"\bwhat\s+are\s+the\s+(?:important\s+things|key\s+points)\b",
    r"\bcan\s+you\s+(?:explain|give\s+me)\s+the\s+main\s+points\b",
]


def is_document_overview_question(question: str) -> bool:
    """Check if the user is asking a broad document overview or summary question."""
    q_lower = question.lower().strip()
    for pat in OVERVIEW_PATTERNS:
        if re.search(pat, q_lower):
            return True
    for pat in KEY_POINTS_PATTERNS:
        if re.search(pat, q_lower) and any(w in q_lower for w in ["document", "file", "it", "paper", "here", "this"]):
            return True
    return False


def is_out_of_scope_question(question: str) -> bool:
    """Check if the question is an unrelated request (joke, weather, chit-chat)."""
    q_lower = question.lower().strip()
    for pat in OUT_OF_SCOPE_PATTERNS:
        if re.search(pat, q_lower):
            return True
    return False


def classify_intent(question: str) -> QuestionIntent:
    """
    Classify user question into a semantic intent category.
    Does not require exact keywords; uses semantic indicators and patterns.
    """
    q_lower = question.lower().strip()

    # 1. Out of scope
    if is_out_of_scope_question(q_lower):
        return QuestionIntent.OUT_OF_SCOPE

    # 2. Conflict & Comparison
    if re.search(r"\b(?:disagree|conflict|conflicts|conflicting|contradict|discrepan(?:cy|cies)|differ|difference\s+between)\b", q_lower):
        return QuestionIntent.CONFLICT_DETECTION

    if re.search(r"\b(?:compare|comparison|versus|vs\.?)\b", q_lower):
        return QuestionIntent.COMPARISON

    # 3. Document Overview / Summary / Key Points
    if is_document_overview_question(q_lower):
        if any(w in q_lower for w in ["summarize", "summary", "brief"]):
            return QuestionIntent.DOCUMENT_SUMMARY
        if any(w in q_lower for w in ["key point", "key points", "main point", "main points", "important things"]):
            return QuestionIntent.KEY_POINTS
        return QuestionIntent.DOCUMENT_OVERVIEW

    # 4. Skills & Technologies
    if re.search(
        r"\b(?:skills?|technolog(?:y|ies)|programming\s+languages?|frameworks?|tools?|"
        r"languages?|tech\s+stack|proficient|competenc(?:y|ies)|expertise|"
        r"what\s+does\s+(?:this\s+person|the\s+candidate|he|she)\s+know|"
        r"what\s+can\s+(?:this\s+person|the\s+candidate)\s+do)\b",
        q_lower
    ):
        return QuestionIntent.SKILLS_LOOKUP

    # 5. Projects & Systems built
    if re.search(
        r"\b(?:projects?|what\s+has\s+(?:this\s+person|the\s+candidate|he|she)\s+(?:worked\s+on|built|developed|made)|"
        r"portfolio|applications?\s+built|systems?\s+developed)\b",
        q_lower
    ):
        return QuestionIntent.PROJECT_LOOKUP

    # 6. Work Experience & Career
    if re.search(
        r"\b(?:experience|work\s+experience|intern(?:ship)?|job|career|employment|"
        r"where\s+did\s+(?:he|she|they|the\s+person|the\s+candidate)\s+work|"
        r"companies\s+worked|responsibilit(?:y|ies))\b",
        q_lower
    ):
        return QuestionIntent.EXPERIENCE_LOOKUP

    # 7. Education & Academic Background
    if re.search(
        r"\b(?:education(?:al)?|degree|university|college|school|cgpa|gpa|percentage|"
        r"bachelor|master|phd|diploma|studied|graduate|graduated|academic|coursework)\b",
        q_lower
    ):
        return QuestionIntent.EDUCATION_LOOKUP

    # 8. Rules & Policies
    if re.search(
        r"\b(?:rules?|polic(?:y|ies)|regulations?|guidelines?|entitled|entitlement|"
        r"benefits?|leaves?|medical\s+leave|maternity|penalty|consequences?|"
        r"what\s+happens\s+if)\b",
        q_lower
    ):
        return QuestionIntent.RULE_LOOKUP

    # 9. Dates & Timeline
    if re.search(
        r"\b(?:when|date|dates|year|years|timeline|what\s+time|schedule|duration)\b",
        q_lower
    ):
        return QuestionIntent.DATE_LOOKUP

    # 10. Location
    if re.search(
        r"\b(?:where|location|address|city|country|state|office|placed)\b",
        q_lower
    ):
        return QuestionIntent.LOCATION_LOOKUP

    # 11. Person Lookup
    if re.search(
        r"\b(?:who\s+is|who\s+wrote|author|candidate|lecturer|professor|who\s+developed|who\s+created)\b",
        q_lower
    ):
        return QuestionIntent.PERSON_LOOKUP

    # 12. General definition or fact
    if re.search(r"\b(?:what\s+is|what\s+are|define|definition|explain|how\s+does)\b", q_lower):
        return QuestionIntent.FACT_LOOKUP

    return QuestionIntent.GENERAL_QUESTION


def expand_query(question: str, intent: QuestionIntent, person_names: Optional[List[str]] = None) -> List[str]:
    """
    Generate expanded internal semantic search queries based on the question and intent.
    These queries maximize embedding recall across candidate chunks without exposing
    them to the user.
    """
    expanded: List[str] = [question]
    q_lower = question.lower().strip()

    if intent in (QuestionIntent.DOCUMENT_OVERVIEW, QuestionIntent.DOCUMENT_SUMMARY):
        expanded.extend([
            "document title summary overview introduction",
            "profile summary main topic key background",
            "purpose subject main content",
            "abstract introduction key findings overview",
        ])

    elif intent == QuestionIntent.KEY_POINTS:
        expanded.extend([
            "key points main highlights summary",
            "core findings achievements responsibilities",
            "important information overview takeaways",
        ])

    elif intent == QuestionIntent.SKILLS_LOOKUP:
        expanded.extend([
            "technical skills programming languages frameworks tools",
            "technologies proficiencies libraries databases",
            "skills qualifications competencies expertise",
        ])

    elif intent == QuestionIntent.PROJECT_LOOKUP:
        expanded.extend([
            "projects developed applications systems built",
            "project title description technologies used",
            "practical applications case studies implementations",
        ])

    elif intent == QuestionIntent.EXPERIENCE_LOOKUP:
        expanded.extend([
            "work experience employment job responsibilities",
            "professional experience roles responsibilities duties",
            "practical background career history",
        ])

    elif intent == QuestionIntent.EDUCATION_LOOKUP:
        expanded.extend([
            "education qualifications degree university college",
            "academic background school coursework degrees",
            "certifications educational history",
        ])

    elif intent == QuestionIntent.RULE_LOOKUP:
        expanded.extend([
            "rules regulations policy guidelines requirements",
            "policy entitlement terms conditions compliance",
            "guidelines procedures standards",
        ])

    elif intent == QuestionIntent.DATE_LOOKUP:
        expanded.extend([
            "date given held timeline year month",
            "effective date schedule timeline duration",
        ])

    elif intent == QuestionIntent.PERSON_LOOKUP:
        if person_names:
            for name in person_names:
                expanded.append(f"{name} author background profile contact")
        expanded.append("author lecturer creator presenter candidate name")

    elif intent == QuestionIntent.CONFLICT_DETECTION:
        expanded.extend([
            "policy difference disagreement conflicting terms",
            "entitlement difference discrepancy mismatch",
        ])

    # Deduplicate while preserving order
    seen: Set[str] = set()
    unique_expanded: List[str] = []
    for q in expanded:
        normalized = q.strip().lower()
        if normalized not in seen and len(normalized) > 0:
            seen.add(normalized)
            unique_expanded.append(q.strip())

    return unique_expanded[:5]


def extract_person_names(question: str) -> List[str]:
    """Extract candidate person names from capitalized tokens or known name phrases."""
    words = question.split()
    names = []
    stop = {"What", "Who", "Where", "When", "Why", "How", "Can", "Could", "Which", "Is", "Are", "The", "This"}
    for w in words:
        cleaned = re.sub(r"[^a-zA-Z]", "", w)
        if cleaned and cleaned[0].isupper() and len(cleaned) >= 3 and cleaned not in stop:
            names.append(cleaned)
    return names


def detect_document_reference(question: str, available_documents: List[Dict[str, Any]]) -> Optional[str]:
    """
    Detect if the user explicitly or implicitly references a specific document in their question.
    Completely dynamic based on uploaded filenames and document categories.
    """
    if not available_documents:
        return None

    # If only one document is indexed, any reference to "this document" is that document
    if len(available_documents) == 1:
        return available_documents[0].get("filename")

    q_lower = question.lower()
    
    # 1. Direct filename or token matches
    for doc in available_documents:
        fname = doc.get("filename", "").lower()
        base_name = fname.split(".")[0].lower()
        if fname in q_lower or (len(base_name) > 3 and base_name in q_lower):
            return doc.get("filename")
        # Check significant tokens in filename
        tokens = [t for t in re.split(r"[_\-\s\(\)\.]+", base_name) if len(t) > 3]
        if any(t in q_lower for t in tokens):
            return doc.get("filename")

    # 2. Category matching
    if any(w in q_lower for w in ["resume", "cv", "candidate"]):
        for doc in available_documents:
            fname = doc.get("filename", "").lower()
            if "resume" in fname or "cv" in fname:
                return doc.get("filename")

    if any(w in q_lower for w in ["policy", "leave", "guideline"]):
        for doc in available_documents:
            fname = doc.get("filename", "").lower()
            if "policy" in fname:
                return doc.get("filename")

    if any(w in q_lower for w in ["paper", "article", "study", "research"]):
        for doc in available_documents:
            fname = doc.get("filename", "").lower()
            if any(term in fname for term in ["paper", "article", "study", "soft", "hard", "research"]):
                return doc.get("filename")

    return None


def is_followup_question(question: str, history: Optional[List[Dict[str, Any]]] = None) -> bool:
    """Check if the question is a follow-up depending on conversation context."""
    if not history:
        return False
    q_lower = question.lower().strip()
    pronouns = [r"\bit\b", r"\bthis\b", r"\bthat\b", r"\bhe\b", r"\bshe\b", r"\bthey\b", r"\bthe\s+previous\b", r"\bwhich\s+one\b"]
    return any(re.search(p, q_lower) for p in pronouns)


def understand_question(
    question: str,
    available_documents: Optional[List[Dict[str, Any]]] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Main entry point for natural language query understanding.
    
    Returns structured analysis:
    - intent: QuestionIntent
    - is_overview: bool
    - is_out_of_scope: bool
    - is_followup: bool
    - expanded_queries: List[str]
    - target_document: Optional[str]
    - person_names: List[str]
    """
    docs = available_documents or []
    intent = classify_intent(question)
    is_overview = intent in OVERVIEW_INTENTS
    is_out_of_scope = intent == QuestionIntent.OUT_OF_SCOPE
    is_followup = is_followup_question(question, conversation_history)
    person_names = extract_person_names(question)
    target_document = detect_document_reference(question, docs)

    # If only one document exists, any reference to "this document" is that document
    if not target_document and len(docs) == 1:
        target_document = docs[0].get("filename")

    expanded_queries = expand_query(question, intent, person_names)

    result = {
        "original_question": question,
        "intent": intent,
        "is_overview": is_overview,
        "is_out_of_scope": is_out_of_scope,
        "is_followup": is_followup,
        "expanded_queries": expanded_queries,
        "target_document": target_document,
        "person_names": person_names,
    }

    logger.info(
        f"Query Understanding: intent={intent.value}, is_overview={is_overview}, "
        f"target_doc={target_document}, expanded_queries={len(expanded_queries)}"
    )
    return result
