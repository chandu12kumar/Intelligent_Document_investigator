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

---

## Folder Structure

```
intelligent-document-investigator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + CORS + routing
│   │   ├── config.py            # Environment-based settings + FRONTEND_URL CORS
│   │   ├── api/
│   │   │   ├── documents.py     # Upload/list/delete endpoints
│   │   │   └── questions.py     # Investigation + history endpoints
│   │   ├── services/
│   │   │   ├── document_processor.py  # PDF/DOCX/TXT/image processing
│   │   │   ├── ocr_service.py         # Tesseract OCR (env-aware path)
│   │   │   ├── chunker.py             # Intelligent text chunking
│   │   │   ├── embeddings.py          # SentenceTransformer embeddings (singleton)
│   │   │   ├── vector_store.py        # ChromaDB operations (lazy init)
│   │   │   ├── rag.py                 # Full RAG pipeline + LLM
│   │   │   ├── conflict_detector.py   # Multi-level conflict detection
│   │   │   ├── confidence.py          # Confidence scoring
│   │   │   └── citation.py            # Source citations
│   │   └── models/
│   │       └── schemas.py       # Pydantic models
│   ├── data/
│   │   ├── uploads/             # Uploaded documents (ephemeral on Render free)
│   │   └── chroma/              # ChromaDB persistent storage (ephemeral on Render free)
│   ├── Dockerfile               # Docker build with Tesseract OCR (for Render Docker deploys)
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── .env                     # Secrets (NOT committed)
│   ├── .env.example             # Template
│   └── run.py                   # Uvicorn runner (local dev)
│
├── frontend/
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Page components
│   │   ├── services/api.js      # Axios API client (uses VITE_API_URL)
│   │   └── index.css            # Global styles
│   ├── .env                     # VITE_API_URL (NOT committed)
│   ├── .env.example             # Template
│   └── vite.config.js
│
├── render.yaml                  # Render Blueprint (optional)
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

# 5. Copy and configure environment
cp .env.example .env
# Edit .env with your actual LLM_API_KEY
```

---

## Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Copy environment file
cp .env.example .env
# Edit if you need a different backend URL

# 4. Start development server
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

> The application auto-detects the Tesseract binary on Windows, Linux, and Render (via PATH). You can also override with the `TESSERACT_CMD` environment variable.

### macOS
```bash
brew install tesseract
```

### Ubuntu/Debian (or Render via Dockerfile)
```bash
sudo apt install tesseract-ocr tesseract-ocr-eng
```

---

## Environment Variables

### Backend (`backend/.env`)

```env
# Required: Your OpenAI API key
LLM_API_KEY=YOUR_API_KEY_HERE

# Model to use for answer generation
LLM_MODEL=gpt-4o-mini

# Storage paths (relative to backend directory)
CHROMA_PATH=./data/chroma
UPLOAD_PATH=./data/uploads

# Embedding model (downloads automatically on first run)
EMBEDDING_MODEL=all-MiniLM-L6-v2

# CORS: The frontend URL that is allowed to access the backend
FRONTEND_URL=http://localhost:5173
```

> ⚠️ NEVER commit `backend/.env`. It's in `.gitignore`. Copy `backend/.env.example` and fill in your values.

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
| GET | `/health` | Health + status check (used by Render) |
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

## 🚀 Render Deployment

### Architecture

```
Render Static Site (Frontend)           Render Web Service (Backend)
  https://FRONTEND.onrender.com    →      https://BACKEND.onrender.com
        React + Vite                          FastAPI + Docker
                                             Tesseract OCR
                                             ChromaDB (local)
                                             SentenceTransformers
```

> ⚠️ **Storage Note (IMPORTANT for Hackathon):** Render's free tier uses an ephemeral local filesystem. Uploaded documents and ChromaDB data will be **lost on every redeploy or instance restart**. This is acceptable for a hackathon demo. For production, add persistent storage (AWS S3 / Render Disk / Supabase).

---

### Deployment Order

Follow this exact order to avoid CORS and URL configuration errors:

#### STEP 1 — Push to GitHub
```bash
git add -A
git commit -m "feat: render deployment configuration"
git push origin main
```
> Verify `.env` and `backend/.env` are NOT in the commit (check git status).

---

#### STEP 2 — Deploy Backend First

**Render → New → Web Service**

| Setting | Value |
|---------|-------|
| Repository | Your GitHub repo |
| Branch | `main` |
| Root Directory | `backend` |
| Runtime | `Docker` (recommended, for Tesseract OCR) |
| Build Command | *(auto from Dockerfile)* |
| Start Command | *(auto from Dockerfile CMD)* |
| Health Check Path | `/health` |

> **If not using Docker** (Python runtime instead):
> - Runtime: `Python 3`
> - Build Command: `pip install -r requirements.txt`
> - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
> - ⚠️ Tesseract OCR will NOT be available without Docker.

**Environment Variables (set in Render Dashboard):**

| Variable | Value |
|----------|-------|
| `LLM_API_KEY` | Your actual OpenAI API key |
| `LLM_MODEL` | `gpt-4o-mini` |
| `CHROMA_PATH` | `./data/chroma` |
| `UPLOAD_PATH` | `./data/uploads` |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` |
| `FRONTEND_URL` | *(leave empty for now, fill after frontend deploy)* |

Click **Deploy**.

---

#### STEP 3 — Test Backend

Once deployed, test these URLs:

```
https://YOUR-BACKEND.onrender.com/
https://YOUR-BACKEND.onrender.com/health       ← must return {"status": "healthy"}
https://YOUR-BACKEND.onrender.com/docs         ← Swagger UI
```

> If `/health` returns `{"status": "healthy"}` you are good to proceed.

---

#### STEP 4 — Deploy Frontend

**Render → New → Static Site**

| Setting | Value |
|---------|-------|
| Repository | Your GitHub repo |
| Branch | `main` |
| Root Directory | `frontend` |
| Build Command | `npm install && npm run build` |
| Publish Directory | `dist` |

**Environment Variables:**

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://YOUR-BACKEND.onrender.com` |

> Replace `YOUR-BACKEND` with your actual Render backend service name.

Click **Deploy**.

---

#### STEP 5 — Connect Frontend URL to Backend CORS

1. Copy the deployed frontend URL: `https://YOUR-FRONTEND.onrender.com`
2. Go to **Backend service → Environment** in Render Dashboard
3. Set `FRONTEND_URL` = `https://YOUR-FRONTEND.onrender.com`
4. Click **Save** → Render will automatically redeploy the backend

---

#### STEP 6 — Final Tests

Test the complete flow:

```
✅ https://YOUR-BACKEND.onrender.com/health
✅ https://YOUR-BACKEND.onrender.com/docs
✅ https://YOUR-FRONTEND.onrender.com           (React app loads)
✅ Upload a document                             (no CORS errors)
✅ Ask a natural-language question               (LLM answer returned)
✅ Check source citations                        (document + page shown)
✅ Upload conflicting documents + ask question   (CONFLICTING detected)
```

---

### Full Environment Variables Reference

#### Backend (Render Web Service)

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | ✅ Yes | Your OpenAI API key |
| `LLM_MODEL` | ✅ Yes | e.g. `gpt-4o-mini` |
| `CHROMA_PATH` | Optional | Default: `./data/chroma` |
| `UPLOAD_PATH` | Optional | Default: `./data/uploads` |
| `EMBEDDING_MODEL` | Optional | Default: `all-MiniLM-L6-v2` |
| `FRONTEND_URL` | ✅ Yes | Your deployed frontend URL (for CORS) |
| `TESSERACT_CMD` | Optional | Override Tesseract binary path |

#### Frontend (Render Static Site)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | ✅ Yes | Your deployed backend URL |

---

### render.yaml (Optional Blueprint)

A `render.yaml` file is included at the root of this project. It describes both services for Render's Infrastructure as Code (Blueprint) feature. However, **secrets like `LLM_API_KEY` and `VITE_API_URL` must still be set manually in the Render Dashboard** — they are marked `sync: false` in the YAML to prevent accidental exposure.

---

### Tesseract OCR on Render

The backend includes a `Dockerfile` at `backend/Dockerfile` that:
1. Uses `python:3.11-slim` as the base
2. Installs `tesseract-ocr` and `tesseract-ocr-eng` via `apt-get`
3. Installs all Python requirements
4. Starts the app with dynamic `$PORT`

**Use Docker runtime on Render** to enable full OCR support for scanned PDFs and image uploads.

The OCR service auto-detects Tesseract in this order:
1. `TESSERACT_CMD` environment variable (if set)
2. System PATH (`which tesseract`)
3. Windows standard installation paths (for local dev)
4. Graceful degradation — OCR disabled if not found (non-fatal)

---

## Future Improvements

1. **Persistent storage** — Replace local ChromaDB + uploads with Render Disk, AWS S3, or Supabase
2. **Multi-language OCR** — Tesseract supports 100+ languages
3. **Re-ranking** — Cross-encoder re-ranking for better retrieval precision
4. **Graph-based relationships** — Document relationship mapping
5. **Timeline extraction** — Automatic detection of date-based conflicts
6. **Export reports** — PDF investigation reports
7. **Authentication** — Multi-user support with document namespaces
8. **Streaming responses** — Real-time LLM streaming via SSE
9. **Table extraction** — Structured data from PDF tables
10. **Self-hosted LLM** — Ollama + Llama 3 for fully local operation

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
*Deployment: Render (Web Service + Static Site)*
