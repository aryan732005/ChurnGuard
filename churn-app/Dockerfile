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
ENV WEB_CONCURRENCY=1
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health')"

CMD ["sh", "-c", "exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:${PORT:-8000} --timeout 120 --graceful-timeout 30 --keep-alive 5 --access-logfile - --error-logfile -"]
