FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PAPERS_DIR=/app/data/papers

WORKDIR /app

COPY packages/ingestion ./packages/ingestion
COPY apps/api ./apps/api

RUN python -m pip install --no-cache-dir -U pip \
    && python -m pip install --no-cache-dir ./packages/ingestion ./apps/api

EXPOSE 8000

CMD ["uvicorn", "mitorag_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

