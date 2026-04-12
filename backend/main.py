"""
FastAPI application entry point.
"""

import logging

from fastapi import FastAPI

from routers.detections import router as detections_router
from routers.ingest import router as ingest_router
from simulator import router as simulator_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Hackazona Detection API")

app.include_router(ingest_router)
app.include_router(detections_router)
app.include_router(simulator_router)


@app.get("/health")
def health():
    return {"status": "ok"}
