"""
FastAPI main application entry point.
Intelligent Document Investigator Backend.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.documents import router as documents_router
from app.api.questions import router as questions_router
from app.services.vector_store import get_collection_stats

# ─── Logging Configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Intelligent Document Investigator",
    description=(
        "AI-powered evidence-based document investigation system. "
        "Upload documents and ask natural-language questions to retrieve "
        "evidence-grounded answers with conflict detection and source citations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ───────────────────────────────────────────────────────────────────
app.include_router(documents_router)
app.include_router(questions_router)

# ─── Root Endpoints ────────────────────────────────────────────────────────────

@app.get("/", tags=["root"])
async def root():
    """API root endpoint."""
    return {
        "name": "Intelligent Document Investigator",
        "version": "1.0.0",
        "description": "AI-powered evidence-based document investigation",
        "problem_statement": "ALG-AI-02",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health", tags=["root"])
async def health_check():
    """Health check endpoint."""
    try:
        stats = get_collection_stats()
        chroma_status = "connected"
        documents_indexed = stats.get("total_chunks", 0)
    except Exception as e:
        chroma_status = f"error: {e}"
        documents_indexed = 0

    api_key_configured = bool(settings.LLM_API_KEY and not settings.LLM_API_KEY.startswith("YOUR_"))

    return {
        "status": "healthy",
        "version": "1.0.0",
        "chroma_status": chroma_status,
        "embedding_model": settings.EMBEDDING_MODEL,
        "llm_model": settings.LLM_MODEL if api_key_configured else "NOT CONFIGURED",
        "llm_api_key_set": api_key_configured,
        "documents_indexed": documents_indexed,
        "upload_path": settings.UPLOAD_PATH,
        "chroma_path": settings.CHROMA_PATH,
    }


# ─── Exception Handlers ────────────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": getattr(exc, "detail", str(exc))},
    )


@app.exception_handler(500)
async def server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again.",
        },
    )


# ─── Startup Event ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("=" * 60)
    logger.info("Intelligent Document Investigator - Starting")
    logger.info(f"Embedding model: {settings.EMBEDDING_MODEL}")
    logger.info(f"LLM model: {settings.LLM_MODEL}")
    logger.info(f"ChromaDB path: {settings.CHROMA_PATH}")
    logger.info(f"Upload path: {settings.UPLOAD_PATH}")
    logger.info(f"LLM API key configured: {bool(settings.LLM_API_KEY)}")
    logger.info("=" * 60)
