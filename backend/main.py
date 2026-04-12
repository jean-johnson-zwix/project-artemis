"""
FastAPI application entry point.

Startup responsibilities:
  1. Validate required env vars (fail fast with a clear message)
  2. Register APScheduler job: pipeline.run_all_assets() every 60 s
  3. Mount simulator router

TODO:
  - Add CORS middleware if the frontend is on a different origin
  - Add GET /detections and GET /detections/{detection_id} for the frontend
  - Add GET /assets/{asset_id} for the frontend asset detail page
"""

import logging

from fastapi import FastAPI

from routers.detections import router as detections_router
from routers.ingest import router as ingest_router

# TODO: mount simulator router
# from simulator import router as simulator_router

# TODO: start APScheduler on startup
# @app.on_event("startup")
# def start_scheduler():
#     ...

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Hackazona Detection API")

app.include_router(ingest_router)
app.include_router(detections_router)


@app.get("/health")
def health():
    return {"status": "ok"}
