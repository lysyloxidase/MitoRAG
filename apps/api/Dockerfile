FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PAPERS_DIR=/app/data/papers

WORKDIR /app

COPY packages/ingestion ./packages/ingestion
COPY packages/knowledge_graph ./packages/knowledge_graph
COPY packages/agents ./packages/agents
COPY packages/retrieval ./packages/retrieval
COPY packages/internet ./packages/internet
COPY apps/api ./apps/api

RUN python -m pip install --no-cache-dir -U pip \
    && python -m pip install --no-cache-dir \
       ./packages/knowledge_graph \
       ./packages/ingestion \
       ./packages/internet \
       ./packages/retrieval \
       ./packages/agents \
       ./apps/api

EXPOSE 8000

CMD ["uvicorn", "mitorag_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

