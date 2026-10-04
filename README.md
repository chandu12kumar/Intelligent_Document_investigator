# 🔎 Intelligent Document Investigator
### Problem Statement: **ALG-AI-02**

> **AI-powered evidence-based document investigation system**  
> Upload documents → Ask questions → Get evidence-grounded answers with conflict detection and source citations.

---

## 📋 Table of Contents

1. [Project Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Features](#features)
4. [Architecture](#architecture)
5. [Tech Stack](#tech-stack)
6. [Folder Structure](#folder-structure)
7. [Installation](#installation)
8. [Backend Setup](#backend-setup)
9. [Frontend Setup](#frontend-setup)
10. [Tesseract Installation](#tesseract-installation)
11. [Environment Variables](#environment-variables)
12. [How to Run](#how-to-run)
13. [API Endpoints](#api-endpoints)
14. [Sample Documents](#sample-documents)
15. [Demo Questions](#demo-questions)
16. [RAG Explanation](#rag-explanation)
17. [Conflict Detection](#conflict-detection)
18. [Uncertainty Handling](#uncertainty-handling)
19. [Future Improvements](#future-improvements)
20. [Hackathon Pitch](#hackathon-pitch)

---

## Overview

**Intelligent Document Investigator** is NOT a simple "Chat with PDF" application. It is a full-stack AI investigation system that:

- Accepts multiple document formats (PDF, DOCX, TXT, PNG, JPG)
- Extracts text using native parsers and OCR
- Creates semantic embeddings using `all-MiniLM-L6-v2`
- Stores vectors in **ChromaDB** persistent vector store
- Retrieves evidence using **RAG** (Retrieval-Augmented Generation)
- Detects **contradictory information** across documents
- Generates evidence-grounded answers via **OpenAI API**
- Explicitly communicates **uncertainty** and **insufficient evidence**
- Shows exact source documents, page numbers, and similarity scores

---

## Problem Statement

**ALG-AI-02** — Build an AI-powered document investigation system that allows users to upload multiple documents and ask natural-language questions about them.

---

## Features

| Feature | Description |
|---------|-------------|
| 📄 Multi-format upload | PDF, DOCX, TXT, PNG, JPG, JPEG |
| 🔍 OCR support | Tesseract for scanned PDFs and images |
| 🧩 Smart chunking | Sentence-boundary-aware overlapping chunks |
| 🧠 Semantic embeddings | `all-MiniLM-L6-v2` via SentenceTransformers |
| 💾 Vector store | ChromaDB persistent storage |
| 🔎 RAG pipeline | Retrieval-Augmented Generation |
| ⚠️ Conflict detection | 3-level: numeric, semantic, LLM-verified |
| 📊 Confidence scoring | Transparent signal-based scoring |
| 📎 Source citations | Document, page, similarity score |
| 🚫 Uncertainty handling | Refuses to fabricate evidence |
| 🎨 Professional UI | Dark theme, investigation-style dashboard |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                       │
│  Upload → Question → Answer + Evidence + Conflicts + Sources     │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP (Axios)
┌─────────────────────────▼───────────────────────────────────────┐
│                    BACKEND (FastAPI)                              │
│                                                                   │
│  POST /documents/upload                                           │
│    → Document Processor (PDF/DOCX/TXT/OCR)                       │
│    → Chunker (sentence-boundary chunks)                          │
│    → Embeddings (all-MiniLM-L6-v2)                               │
│    → ChromaDB (persistent vector store)                          │
│                                                                   │
│  POST /questions/ask                                              │
│    → Query Embedding                                              │
│    → ChromaDB Semantic Search (top-k=10)                         │
│    → Conflict Detector (numeric + semantic)                       │
│    → Confidence Scorer                                            │
│    → LLM (OpenAI) with strict evidence grounding                 │
│    → Structured InvestigationResult                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Frontend
| Package | Version | Purpose |
|---------|---------|---------|
| React | 18.x | UI framework |
| Vite | 5.x | Build tool |
| Axios | latest | HTTP client |
| Lucide React | latest | Icons |
| Tailwind CSS | 3.x | Utility CSS |

### Backend
| Package | Version | Purpose |
|---------|---------|---------|
| FastAPI | ≥0.111 | Web framework |
| Uvicorn | latest | ASGI server |
| PyMuPDF | ≥1.24 | PDF processing |
| python-docx | ≥1.1 | DOCX processing |
| Pillow | ≥10.3 | Image processing |
| pytesseract | ≥0.3.10 | OCR |
| sentence-transformers | ≥3.0 | Embeddings |
| ChromaDB | ≥0.5 | Vector store |
| OpenAI | ≥1.30 | LLM API |
| Pydantic | ≥2.7 | Data validation |

---

## Folder Structure

```
intelligent-document-investigator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS + routing
│   │   ├── config.py            # Environment-based settings
│   │   ├── api/
│   │   │   ├── documents.py     # Upload/list/delete endpoints
│   │   │   └── questions.py     # Investigation + history endpoints
│   │   ├── services/
│   │   │   ├── document_processor.py  # PDF/DOCX/TXT/image processing
│   │   │   ├── ocr_service.py         # Tesseract OCR wrapper
│   │   │   ├── chunker.py             # Intelligent text chunking
│   │   │   ├── embeddings.py          # SentenceTransformer embeddings
│   │   │   ├── vector_store.py        # ChromaDB operations
│   │   │   ├── rag.py                 # Full RAG pipeline + LLM
│   │   │   ├── conflict_detector.py   # Multi-level conflict detection
│   │   │   ├── confidence.py          # Confidence scoring
│   │   │   └── citation.py            # Source citations
│   │   └── models/
│   │       └── schemas.py       # Pydantic models
│   ├── data/
│   │   ├── uploads/             # Uploaded documents
│   │   └── chroma/              # ChromaDB persistent storage
│   ├── requirements.txt
│   ├── .env                     # Secrets (NOT committed)
│   ├── .env.example             # Template
│   └── run.py                   # Uvicorn runner
│
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Page components
│   │   ├── services/api.js      # API client
│   │   └── index.css            # Global styles
│   ├── .env                     # VITE_API_URL
│   └── vite.config.js
│
├── sample_documents/            # Demo documents with intentional conflict
│   ├── policy_a.txt             # 15 days medical leave
│   ├── policy_b.txt             # 12 days medical leave (CONFLICT!)
│   └── company_policy.txt       # General HR procedures
│
├── README.md
└── .gitignore
```

---

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- Tesseract OCR (optional, for scanned documents)

---

## Backend Setup

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv venv

# 3. Activate (Windows)
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

---

## Tesseract Installation

Tesseract is required for OCR (scanned PDFs and image files). Without it, only native text PDFs and DOCX/TXT are supported.

### Windows
1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to: `C:\Program Files\Tesseract-OCR\`
3. Add to PATH: `C:\Program Files\Tesseract-OCR\`
4. Verify: `tesseract --version`

### macOS
```bash
brew install tesseract
```

### Ubuntu/Debian
```bash
sudo apt install tesseract-ocr
```

---

## Environment Variables

### Backend (`backend/.env`)

```env
# Required: Your OpenAI API key
LLM_API_KEY=sk-proj-your-actual-key-here

# Model to use for answer generation
LLM_MODEL=gpt-4o-mini

# Storage paths (relative to backend directory)
CHROMA_PATH=./data/chroma
UPLOAD_PATH=./data/uploads

# Embedding model (downloads automatically)
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

> ⚠️ NEVER commit `backend/.env`. It's in `.gitignore`.

### Frontend (`frontend/.env`)

```env
VITE_API_URL=http://localhost:8000
```

---

## How to Run

### 1. Start Backend

```bash
cd backend
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

uvicorn app.main:app --reload --port 8000
```

### 2. Start Frontend (separate terminal)

```bash
cd frontend
npm run dev
```

### 3. Open browser

Navigate to: **http://localhost:5173**

### 4. Upload sample documents

Upload all 3 files from `sample_documents/`

### 5. Ask demo questions

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API root info |
| GET | `/health` | Health + status |
| POST | `/documents/upload` | Upload & process document |
| GET | `/documents` | List all indexed documents |
| DELETE | `/documents/{id}` | Delete document |
| POST | `/questions/ask` | Submit investigation question |
| GET | `/questions/history` | Get investigation history |
| GET | `/questions/history/{id}` | Get specific investigation |

### Upload Response
```json
{
  "success": true,
  "filename": "policy_a.txt",
  "document_id": "policy_a_abc12345",
  "pages": 1,
  "chunks": 5,
  "ocr_used": false,
  "message": "Document processed successfully. 5 chunks indexed."
}
```

### Investigation Response
```json
{
  "investigation_id": "uuid",
  "question": "How many medical leave days?",
  "answer": "CONFLICTING evidence found...",
  "status": "CONFLICTING",
  "confidence": 0.72,
  "confidence_level": "MEDIUM",
  "confidence_explanation": "Confidence reduced: 1 conflicting claim(s) detected",
  "uncertainty": "Conflicting information found across documents...",
  "evidence": [...],
  "conflicts": [...],
  "sources": [...],
  "timestamp": "2026-10-04T..."
}
```

---

## Sample Documents

Three documents with intentional conflicts for demo:

### `policy_a.txt`
> **15 days** medical leave per year  
> Effective: **January 1, 2026**

### `policy_b.txt`
> **12 days** medical leave per year  
> Effective: **March 1, 2026**  
> *(Supersedes previous policy)*

### `company_policy.txt`
> How to submit leave requests through HR portal  
> Employee benefits (health insurance, PF, bonuses)

---

## Demo Questions

| # | Question | Expected Status | Expected Result |
|---|----------|----------------|-----------------|
| 1 | *How many medical leave days does an employee receive per year?* | **CONFLICTING** | Shows Policy A (15 days) vs Policy B (12 days) conflict |
| 2 | *When is the medical leave policy effective?* | **CONFLICTING** | Jan 1, 2026 vs March 1, 2026 |
| 3 | *How should employees submit medical leave requests?* | **SUPPORTED** | HR portal procedure from company_policy.txt |
| 4 | *What is the maternity leave policy?* | **INSUFFICIENT_EVIDENCE** | No evidence found, refuses to fabricate |

---

## RAG Explanation

**Retrieval-Augmented Generation (RAG)** is the core AI architecture:

```
1. USER QUESTION
      ↓
2. QUERY EMBEDDING (all-MiniLM-L6-v2)
      ↓
3. CHROMADB SEMANTIC SEARCH (cosine similarity, top-k=10)
      ↓
4. RETRIEVED EVIDENCE CHUNKS
      ↓
5. CONFLICT ANALYSIS (numeric + semantic detection)
      ↓
6. EVIDENCE ASSEMBLY (formatted with source labels)
      ↓
7. LLM PROMPT (strict grounding instructions + evidence)
      ↓
8. STRUCTURED ANSWER (status, confidence, evidence, conflicts, sources)
```

The LLM is **only allowed** to use the supplied evidence. It cannot use general knowledge.

---

## Conflict Detection

### Level 1: Numeric Conflict Detection
Regex patterns detect numeric values with units:
- `15 days` vs `12 days`
- `80%` vs `90%`
- `₹50,000` vs `₹60,000`

Compares values across documents and flags differences on the same topic.

### Level 2: Semantic Conflict Detection
Uses embedding cosine similarity to find chunks discussing the same topic but with different claims (similarity 0.65–0.95 range).

### Level 3: LLM Verification
The LLM is shown detected conflicts in the prompt and asked to verify and explain them in the answer.

---

## Uncertainty Handling

The system has four investigation statuses:

| Status | Meaning |
|--------|---------|
| `SUPPORTED` | Evidence directly supports the answer (confidence ≥ 0.55) |
| `PARTIALLY_SUPPORTED` | Limited evidence found |
| `CONFLICTING` | Documents contradict each other |
| `INSUFFICIENT_EVIDENCE` | No relevant evidence found |

When evidence is insufficient, the LLM is instructed to say so explicitly rather than guessing.

---

## Future Improvements

1. **Multi-language OCR** — Tesseract supports 100+ languages
2. **Re-ranking** — Cross-encoder re-ranking for better retrieval precision
3. **Graph-based relationships** — Document relationship mapping
4. **Timeline extraction** — Automatic detection of date-based conflicts
5. **Export reports** — PDF investigation reports
6. **Authentication** — Multi-user support with document namespaces
7. **Streaming responses** — Real-time LLM streaming via SSE
8. **Table extraction** — Structured data from PDF tables
9. **Self-hosted LLM** — Ollama + Llama 3 for fully local operation
10. **Citation highlighting** — Highlight exact quotes in original documents

---

## Hackathon Pitch

### Problem
Organizations have dozens of policy documents, circulars, and handbooks — often contradictory. Employees and auditors waste hours cross-referencing them manually.

### Solution
**Intelligent Document Investigator** provides instant, evidence-grounded answers with:
- ⚠️ Automatic contradiction detection
- 📊 Transparent confidence scoring
- 📎 Exact source citations with page numbers
- 🚫 Honest "I don't know" when evidence is absent

### Impact
- **HR teams**: Instantly identify conflicting policies
- **Legal teams**: Cross-reference contracts and regulations
- **Auditors**: Trace policy changes across versions
- **Compliance**: Flag regulatory inconsistencies

### Demo Highlights
1. Upload 3 sample documents (30 seconds)
2. Ask: *"How many medical leave days?"* → **CONFLICTING** detected
3. Ask: *"What is maternity leave policy?"* → **INSUFFICIENT EVIDENCE** (refuses to guess)
4. Ask: *"How to submit leave requests?"* → **SUPPORTED** with exact source

---

*Built for Hackathon — Problem Statement ALG-AI-02*  
*Stack: React + FastAPI + ChromaDB + SentenceTransformers + OpenAI*
