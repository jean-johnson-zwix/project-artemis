"""
Simulator — injects synthetic data then runs the full pipeline.

Mounted in main.py as a router under /simulate.

POST /simulate/event
  body: SimulateEventRequest

Scenarios (see tasks.md for full spec):
  corrosion_spike        — elevated temp + degraded coating → CORROSION_THRESHOLD
  sensor_anomaly         — sensor value jumps 4σ            → SENSOR_ANOMALY
  transmitter_divergence — PT-101A/B diverge >5%            → TRANSMITTER_DIVERGENCE
  inspection_overdue     — last inspection = 18 mo ago      → overdue signal

Flow:
  1. Validate request (FastAPI does this via SimulateEventRequest)
  2. Inject synthetic timeseries / metadata rows into DB based on scenario
     + overrides (defaults come from seed data when override is absent)
  3. Call pipeline.run(asset_id) — goes through all layers including Teams

TODO: implement _inject_* helpers for each scenario, then wire into the
      route handler below.
"""

from __future__ import annotations

from fastapi import APIRouter

from models import SimulateEventRequest, SimulationScenario  # noqa: F401

router = APIRouter(prefix="/simulate", tags=["simulator"])


@router.post("/event")
def simulate_event(body: SimulateEventRequest):
    """
    Inject data for the requested scenario and trigger the full pipeline.

    Returns the detection IDs produced (empty list if nothing fired).
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Scenario injection stubs
# ---------------------------------------------------------------------------


def _inject_corrosion_spike(asset_id: str, overrides: dict) -> None:
    """Write elevated-temp + degraded-coating rows for the asset."""
    raise NotImplementedError


def _inject_sensor_anomaly(asset_id: str, overrides: dict) -> None:
    """Write a single timeseries row that is ~4σ above the rolling mean."""
    raise NotImplementedError


def _inject_transmitter_divergence(asset_id: str, overrides: dict) -> None:
    """Write diverging readings for the A/B sensor pair on the asset."""
    raise NotImplementedError


def _inject_inspection_overdue(asset_id: str, overrides: dict) -> None:
    """Back-date the last inspection work order to 18 months ago."""
    raise NotImplementedError
