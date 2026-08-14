FROM python:3.11-slim

WORKDIR /app/churn-app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY churn-app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY churn-app/app ./app
COPY ml /app/ml
COPY data /app/data
COPY models /app/models
COPY docs /app/docs

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health')"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
