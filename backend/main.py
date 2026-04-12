"""
FastAPI application entry point.
"""

import logging

from fastapi import FastAPI

from db import SessionLocal
from layers.indexing import seed_unindexed_documents
from routers.detections import router as detections_router
from routers.documents import router as documents_router
from routers.ingest import router as ingest_router
from simulator import router as simulator_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Hackazona Detection API")

app.include_router(ingest_router)
app.include_router(detections_router)
app.include_router(documents_router)
app.include_router(simulator_router)


@app.on_event("startup")
def _seed_page_index() -> None:
    """
    On startup, build PageIndex trees for any documents that don't have one yet.
    Runs synchronously so trees are ready before the first detection arrives.
    For large corpora, swap to a BackgroundTask — acceptable for hackathon scale.
    """
    if not __import__("os").getenv("AZURE_OPENAI_API_KEY"):
        return  # skip indexing when no key is configured (keyword-only mode)

    db = SessionLocal()
    try:
        seed_unindexed_documents(db)
    except Exception as exc:
        __import__("logging").getLogger(__name__).error(
            "Startup PageIndex seeding failed: %s", exc, exc_info=True
        )
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}
