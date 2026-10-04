"""
Configuration management for the Intelligent Document Investigator backend.
All secrets and configurable values are loaded from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Application settings loaded from environment variables."""

    # LLM Configuration
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")

    # Storage Paths
    CHROMA_PATH: str = os.getenv("CHROMA_PATH", str(BASE_DIR / "data" / "chroma"))
    UPLOAD_PATH: str = os.getenv("UPLOAD_PATH", str(BASE_DIR / "data" / "uploads"))

    # Embedding Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # ChromaDB Collection
    CHROMA_COLLECTION: str = "document_investigator"

    # RAG Configuration
    TOP_K_RETRIEVAL: int = 10
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Confidence Thresholds
    HIGH_CONFIDENCE_THRESHOLD: float = 0.85
    MEDIUM_CONFIDENCE_THRESHOLD: float = 0.60

    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ]

    def __init__(self):
        # Ensure storage directories exist
        os.makedirs(self.CHROMA_PATH, exist_ok=True)
        os.makedirs(self.UPLOAD_PATH, exist_ok=True)

    def validate(self):
        """Validate required settings."""
        if not self.LLM_API_KEY:
            raise ValueError(
                "LLM_API_KEY is not set. Please add it to backend/.env"
            )
        return True


settings = Settings()
