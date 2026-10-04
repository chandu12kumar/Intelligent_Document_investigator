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
    _raw_chroma = os.getenv("CHROMA_PATH", "./data/chroma")
    CHROMA_PATH: str = str((BASE_DIR / _raw_chroma).resolve()) if not Path(_raw_chroma).is_absolute() else _raw_chroma

    _raw_upload = os.getenv("UPLOAD_PATH", "./data/uploads")
    UPLOAD_PATH: str = str((BASE_DIR / _raw_upload).resolve()) if not Path(_raw_upload).is_absolute() else _raw_upload

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

    # Frontend URL & CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    @property
    def ALLOWED_ORIGINS(self) -> list:
        origins = {
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        }
        if self.FRONTEND_URL:
            for url in self.FRONTEND_URL.split(","):
                clean = url.strip().rstrip("/")
                if clean:
                    origins.add(clean)
        return sorted(list(origins))

    def __init__(self):
        # Ensure storage directories exist safely
        os.makedirs(self.CHROMA_PATH, exist_ok=True)
        os.makedirs(self.UPLOAD_PATH, exist_ok=True)

    def validate(self):
        """Validate required settings without raising fatal errors at startup."""
        if not self.LLM_API_KEY or self.LLM_API_KEY.startswith("YOUR_"):
            return False
        return True


settings = Settings()
