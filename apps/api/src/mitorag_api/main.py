"""MitoRAG FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

from mitorag_api.routers import health, ingest, kg, query


def create_app() -> FastAPI:
    app = FastAPI(title="MitoRAG API", version="1.0.0")
    app.include_router(health.router)
    app.include_router(query.router, prefix="/query", tags=["query"])
    app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
    app.include_router(kg.router, prefix="/kg", tags=["knowledge-graph"])
    return app


app = create_app()
