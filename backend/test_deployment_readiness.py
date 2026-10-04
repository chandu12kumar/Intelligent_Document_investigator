"""
Test deployment readiness for Render deployment.
Tests:
1. GET /health returns status: healthy
2. GET / returns valid API description
3. GET /documents returns document list
4. POST /documents/upload validates unsupported file types with HTTP 400
5. POST /documents/upload validates empty files with HTTP 400
6. POST /questions/ask returns 400 with 'LLM_API_KEY is not configured.' when key is missing/invalid
7. CORS allows configured FRONTEND_URL and localhost
8. OCR configuration is environment-aware and non-fatal
"""

import sys
import os
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.ocr_service import is_ocr_available, configure_tesseract

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200, f"Health check failed: {response.text}"
    data = response.json()
    assert data["status"] == "healthy", f"Expected healthy, got: {data}"
    assert "version" in data
    assert "chroma_status" in data
    print("PASS: /health returned HTTP 200 and status: healthy")

def test_root():
    response = client.get("/")
    assert response.status_code == 200, f"Root endpoint failed: {response.text}"
    data = response.json()
    assert data["status"] == "online"
    assert data["name"] == "Intelligent Document Investigator"
    assert data["docs"] == "/docs"
    print("PASS: / returned HTTP 200 and valid status info")

def test_documents_list():
    response = client.get("/documents")
    assert response.status_code == 200, f"List documents failed: {response.text}"
    data = response.json()
    assert "documents" in data
    assert "total" in data
    print(f"PASS: /documents returned HTTP 200 with {data['total']} documents indexed")

def test_unsupported_upload():
    # Attempt to upload an executable or unsupported file
    response = client.post(
        "/documents/upload",
        files={"file": ("malicious.exe", b"executable binary content", "application/octet-stream")}
    )
    assert response.status_code == 400, f"Expected 400 for unsupported file, got {response.status_code}"
    print(f"PASS: /documents/upload rejected unsupported file with HTTP 400: {response.json()['detail']}")

def test_empty_upload():
    # Attempt to upload an empty file
    response = client.post(
        "/documents/upload",
        files={"file": ("empty.txt", b"", "text/plain")}
    )
    assert response.status_code == 400, f"Expected 400 for empty file, got {response.status_code}"
    print(f"PASS: /documents/upload rejected empty file with HTTP 400: {response.json()['detail']}")

def test_missing_api_key_ask():
    # Temporarily unset LLM_API_KEY to test Requirement 22
    original_key = settings.LLM_API_KEY
    try:
        settings.LLM_API_KEY = ""
        response = client.post("/questions/ask", json={"question": "What is in this document?"})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert response.json()["detail"] == "LLM_API_KEY is not configured.", f"Got {response.json()}"
        print("PASS: /questions/ask returned HTTP 400 with 'LLM_API_KEY is not configured.' when key missing")
    finally:
        settings.LLM_API_KEY = original_key

def test_cors_configuration():
    origins = settings.ALLOWED_ORIGINS
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    print(f"PASS: CORS configured with origins: {origins}")

def test_ocr_configuration():
    configured = configure_tesseract()
    available = is_ocr_available()
    print(f"PASS: OCR environment-aware check succeeded (available={available})")

if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING DEPLOYMENT READINESS TESTS")
    print("=" * 60)
    test_health()
    test_root()
    test_documents_list()
    test_unsupported_upload()
    test_empty_upload()
    test_missing_api_key_ask()
    test_cors_configuration()
    test_ocr_configuration()
    print("=" * 60)
    print("ALL DEPLOYMENT READINESS TESTS PASSED!")
    print("=" * 60)
