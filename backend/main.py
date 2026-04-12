import logging

from fastapi import FastAPI

from routers.detections import router as detections_router
from routers.ingest import router as ingest_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Layer 1 Detection Engine")

app.include_router(ingest_router)
app.include_router(detections_router)


@app.get("/health")
def health():
    return {"status": "ok"}
