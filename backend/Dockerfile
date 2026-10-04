# Production Dockerfile for Intelligent Document Investigator Backend
# Designed for Render Web Service deployment with Tesseract OCR support.

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies: Tesseract OCR, English data, OpenCV/PyMuPDF GL dependencies, and curl
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY . .

# Ensure storage directories exist inside the container
RUN mkdir -p data/uploads data/chroma

# Expose default port
EXPOSE 8000

# Start FastAPI application using dynamic $PORT provided by Render
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
