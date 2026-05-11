"""MitoRAG FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mitorag_api.routers import health, ingest, kg, query


def _enable_cors(app: FastAPI) -> None:
    # FastAPI's add_middleware signature uses ParamSpec generics that pyright
    # cannot fully resolve through Starlette's stubs, so we isolate the call
    # behind a typed helper that the rest of the module can use cleanly.
    app.add_middleware(  # pyright: ignore[reportUnknownMemberType, reportArgumentType, reportCallIssue]
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_app() -> FastAPI:
    app = FastAPI(title="MitoRAG API", version="1.0.0")
    _enable_cors(app)
    app.include_router(health.router)
    app.include_router(query.router, prefix="/query", tags=["query"])
    app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
    app.include_router(kg.router, prefix="/kg", tags=["knowledge-graph"])
    return app


app = create_app()
