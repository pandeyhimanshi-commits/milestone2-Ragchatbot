FROM python:3.12-slim

WORKDIR /app

# Build context must be repo root. Keep Dockerfile path:
# ingestion/phase-9-security-ui/Dockerfile
COPY ingestion/phase-9-security-ui/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the backend runtime plus dependent RAG phases expected by runtime_api.
COPY ingestion /app/ingestion

ENV PYTHONUNBUFFERED=1
ENV SKIP_MODEL_WARMUP=1

WORKDIR /app/ingestion/phase-9-security-ui
CMD ["sh", "-c", "python -m uvicorn runtime_api.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
