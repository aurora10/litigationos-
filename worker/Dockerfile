FROM python:3.12-slim

# Tesseract OCR with Dutch/French/Russian + Poppler for PDF page rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr tesseract-ocr-nld tesseract-ocr-fra tesseract-ocr-rus \
      poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker.py .
CMD ["python", "worker.py"]
