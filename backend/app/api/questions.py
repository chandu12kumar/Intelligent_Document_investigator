"""
Questions API router.
Handles investigation queries and history retrieval.
"""

import logging
import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import (
    QuestionRequest,
    InvestigationResult,
    InvestigationHistoryResponse,
    InvestigationSummary,
)
from app.services.rag import run_investigation

router = APIRouter(prefix="/questions", tags=["questions"])
logger = logging.getLogger(__name__)

# ── In-memory + persistent investigation history ───────────────────────────────
HISTORY_FILE = Path(settings.UPLOAD_PATH) / "investigation_history.json"
_investigation_cache: dict = {}  # id -> InvestigationResult


def load_history() -> dict:
    """Load investigation history from JSON."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_history(history: dict):
    """Persist investigation history to JSON."""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Keep only last 50 investigations on disk
        if len(history) > 50:
            keys = sorted(history.keys())
            for old_key in keys[:-50]:
                del history[old_key]
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save history: {e}")


@router.post("/ask", response_model=InvestigationResult)
async def ask_question(request: QuestionRequest):
    """
    Submit a question for AI investigation.
    
    The system will:
    1. Retrieve relevant evidence from indexed documents
    2. Detect conflicts across sources
    3. Generate an evidence-grounded answer
    4. Return structured investigation result
    """
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Validate that LLM_API_KEY is configured
    api_key = (settings.LLM_API_KEY or "").strip()
    if not api_key or api_key.startswith("YOUR_") or api_key == "none":
        raise HTTPException(status_code=400, detail="LLM_API_KEY is not configured.")

    logger.info(f"Investigation request: {question[:80]}")

    try:
        result = await run_investigation(question)
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Investigation validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Investigation failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during investigation: {e}", exc_info=True)
        err_msg = str(e)
        if "model" in err_msg.lower() and ("not found" in err_msg.lower() or "does not exist" in err_msg.lower()):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid LLM_MODEL '{settings.LLM_MODEL}': {err_msg}",
            )
        raise HTTPException(
            status_code=500,
            detail="Investigation failed due to an internal error. Please try again.",
        )

    # Persist to history
    try:
        history = load_history()
        history[result.investigation_id] = result.model_dump(mode="json")
        save_history(history)
        _investigation_cache[result.investigation_id] = result
    except Exception as e:
        logger.warning(f"Failed to save investigation history: {e}")

    return result


@router.get("/history", response_model=InvestigationHistoryResponse)
async def get_investigation_history():
    """Get recent investigation history."""
    try:
        history = load_history()
        summaries = []

        for inv_id, inv_data in reversed(list(history.items())):
            summaries.append(InvestigationSummary(
                investigation_id=inv_id,
                question=inv_data.get("question", ""),
                status=inv_data.get("status", "INSUFFICIENT_EVIDENCE"),
                confidence=inv_data.get("confidence", 0.0),
                timestamp=inv_data.get("timestamp", ""),
            ))

        return InvestigationHistoryResponse(
            investigations=summaries[:20],  # Return last 20
            total=len(summaries),
        )
    except Exception as e:
        logger.error(f"Failed to load history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve investigation history.")


@router.get("/history/{investigation_id}", response_model=InvestigationResult)
async def get_investigation(investigation_id: str):
    """Retrieve a specific investigation by ID."""
    # Check in-memory cache first
    if investigation_id in _investigation_cache:
        return _investigation_cache[investigation_id]

    # Try loading from disk
    history = load_history()
    if investigation_id not in history:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation '{investigation_id}' not found.",
        )

    try:
        inv_data = history[investigation_id]
        return InvestigationResult(**inv_data)
    except Exception as e:
        logger.error(f"Failed to deserialize investigation {investigation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve investigation.")
