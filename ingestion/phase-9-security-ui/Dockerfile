FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV SKIP_MODEL_WARMUP=1

CMD ["sh", "-c", "python -m uvicorn runtime_api.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
