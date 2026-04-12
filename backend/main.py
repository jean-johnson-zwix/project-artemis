"""
FastAPI application entry point.

Startup responsibilities:
  1. Validate required env vars (fail fast with a clear message)
  2. Register APScheduler job: pipeline.run_all_assets() every 60 s
  3. Mount simulator router

TODO:
  - Add CORS middleware if the frontend is on a different origin
  - Add a GET /health endpoint (DB ping + scheduler status)
  - Add GET /detections and GET /detections/{detection_id} for the frontend
  - Add GET /assets/{asset_id} for the frontend asset detail page
"""

from fastapi import FastAPI

from simulator import router as simulator_router  # noqa: F401

app = FastAPI(title="Hackazona Detection API")

# TODO: mount simulator router
# app.include_router(simulator_router)

# TODO: start APScheduler on startup
# @app.on_event("startup")
# def start_scheduler():
#     ...

# TODO: GET /health
# TODO: GET /detections
# TODO: GET /detections/{detection_id}
# TODO: GET /assets/{asset_id}
