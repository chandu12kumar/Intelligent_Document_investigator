"""
Run script for the backend server.
Usage: python run.py
"""

import uvicorn
import os
from pathlib import Path

if __name__ == "__main__":
    # Ensure data directories exist
    base = Path(__file__).parent
    os.makedirs(base / "data" / "uploads", exist_ok=True)
    os.makedirs(base / "data" / "chroma", exist_ok=True)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
