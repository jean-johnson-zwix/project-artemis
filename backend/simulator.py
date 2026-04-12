"""
Simulator — injects synthetic data then runs the full pipeline.

Mounted in main.py as a router under /simulate.

POST /simulate/event
  body: SimulateEventRequest

Scenarios:
  corrosion_spike        — elevated temp + optional degraded-coating overrides → CORROSION_THRESHOLD
  sensor_anomaly         — seed 30 normal readings + one spike_multiplier*σ outlier → SENSOR_ANOMALY
  transmitter_divergence — PT-101-PV / PT-102-PV diverge > 5% → TRANSMITTER_DIVERGENCE
  inspection_overdue     — backdate last INSPECTION work order to 18 months ago + inject temp reading

Flow:
  1. Validate request (FastAPI does this via SimulateEventRequest)
  2. Resolve asset_id tag → full DB key (e.g. "V-101" → "AREA-HP-SEP:V-101")
  3. Inject synthetic timeseries / metadata rows into DB based on scenario + overrides
  4. Call pipeline.run(asset_id) — goes through all layers including Teams
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import text

from db import SessionLocal
from detection.corrosion import CORROSION_BASELINE
from layers import pipeline
from models import SimulateEventRequest, SimulationScenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulate", tags=["simulator"])

# Defaults for sensor_anomaly when no override provided
_DEFAULT_ANOMALY_SENSOR = "V-101-PRESS"
_DEFAULT_ANOMALY_BASELINE = 55.0
_DEFAULT_ANOMALY_STDDEV = 2.0


@router.post("/event")
def simulate_event(body: SimulateEventRequest) -> dict:
    """
    Inject data for the requested scenario and trigger the full pipeline.
    Returns the detection IDs produced (empty list if nothing fired).
    """
    # For transmitter_divergence the run target is derived from the sensor pair,
    # not the request asset_id.
    if body.scenario == SimulationScenario.TRANSMITTER_DIVERGENCE:
        fired = _inject_transmitter_divergence(body.overrides)
        return {"detections_fired": fired}

    # Resolve tag → full asset_id for all other scenarios
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                "SELECT asset_id FROM assets "
                "WHERE tag = :q OR asset_id = :q "
                "LIMIT 1"
            ),
            {"q": body.asset_id},
        ).fetchone()
    finally:
        db.close()

    if not row:
        return {"error": f"Asset not found: {body.asset_id}", "detections_fired": []}

    full_asset_id = row[0]

    if body.scenario == SimulationScenario.CORROSION_SPIKE:
        _inject_corrosion_spike(full_asset_id, body.overrides)
    elif body.scenario == SimulationScenario.SENSOR_ANOMALY:
        _inject_sensor_anomaly(full_asset_id, body.overrides)
    elif body.scenario == SimulationScenario.INSPECTION_OVERDUE:
        _inject_inspection_overdue(full_asset_id, body.overrides)

    fired = pipeline.run(full_asset_id)
    return {"detections_fired": fired}


# ---------------------------------------------------------------------------
# Scenario injection helpers
# ---------------------------------------------------------------------------


def _inject_corrosion_spike(asset_id: str, overrides: dict) -> None:
    """
    Write an elevated-temperature reading for the asset's temperature sensor,
    and apply any baseline overrides (coating_failure_pct, wall_thickness_mm,
    remaining_allowance_mm, base_corrosion_rate_mm_per_year) directly to the
    in-memory CORROSION_BASELINE so the detector picks them up when pipeline.run()
    is called immediately after.
    """
    baseline = CORROSION_BASELINE.get(asset_id)
    if baseline is None:
        logger.warning("No corrosion baseline for %s — corrosion injection skipped", asset_id)
        return

    temp_celsius = overrides.get("temperature_celsius", 135.0)

    # Apply baseline overrides before pipeline.run() reads them
    for key in (
        "coating_failure_pct",
        "wall_thickness_mm",
        "remaining_allowance_mm",
        "base_corrosion_rate_mm_per_year",
    ):
        if key in overrides:
            baseline[key] = float(overrides[key])

    db = SessionLocal()
    try:
        db.execute(
            text(
                "INSERT INTO timeseries "
                "(timestamp, sensor_id, asset_id, sensor_type, value, unit, quality_flag) "
                "VALUES (:ts, :sid, :aid, 'TEMPERATURE', :val, 'degC', 'GOOD')"
            ),
            {
                "ts": datetime.now(timezone.utc),
                "sid": baseline["temp_sensor_id"],
                "aid": asset_id,
                "val": temp_celsius,
            },
        )
        db.commit()
    finally:
        db.close()


def _inject_sensor_anomaly(asset_id: str, overrides: dict) -> None:
    """
    Seed 30 normal readings over the last 23 hours for a sensor on the asset,
    then inject one outlier at spike_multiplier × stddev above the mean.
    This ensures the Z-score window has enough data (≥30) and the outlier
    exceeds the |z| > 3 threshold.
    """
    sensor_id = overrides.get("sensor_id", _DEFAULT_ANOMALY_SENSOR)
    baseline_value = float(overrides.get("baseline_value", _DEFAULT_ANOMALY_BASELINE))
    stddev = float(overrides.get("stddev", _DEFAULT_ANOMALY_STDDEV))
    spike_multiplier = float(overrides.get("spike_multiplier", 4.5))

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=23)

    db = SessionLocal()
    try:
        # Seed 30 readings spaced 45 min apart within the 24h window
        for i in range(30):
            ts = window_start + timedelta(minutes=i * 45)
            val = baseline_value + random.gauss(0, stddev * 0.3)  # tight cluster
            db.execute(
                text(
                    "INSERT INTO timeseries "
                    "(timestamp, sensor_id, asset_id, sensor_type, value, unit, quality_flag) "
                    "SELECT :ts, :sid, asset_id, sensor_type, :val, unit, 'GOOD' "
                    "FROM sensor_metadata WHERE sensor_id = :sid"
                ),
                {"ts": ts, "sid": sensor_id, "val": val},
            )

        # Inject the outlier as the most recent reading
        outlier_val = baseline_value + spike_multiplier * stddev
        db.execute(
            text(
                "INSERT INTO timeseries "
                "(timestamp, sensor_id, asset_id, sensor_type, value, unit, quality_flag) "
                "SELECT :ts, :sid, asset_id, sensor_type, :val, unit, 'GOOD' "
                "FROM sensor_metadata WHERE sensor_id = :sid"
            ),
            {"ts": now, "sid": sensor_id, "val": outlier_val},
        )
        db.commit()
    finally:
        db.close()


def _inject_transmitter_divergence(overrides: dict) -> list[str]:
    """
    Write diverging readings for PT-101-PV and PT-102-PV timestamped within
    5 minutes of each other (staleness check passes), with divergence_pct > 5%.
    Then calls pipeline.run() on the asset that owns PT-101-PV.
    Returns fired detection IDs.
    """
    base_pressure = float(overrides.get("base_pressure", 52.0))
    divergence_pct = float(overrides.get("divergence_pct", 8.0))

    p1_val = base_pressure
    p2_val = base_pressure * (1 - divergence_pct / 100)

    now = datetime.now(timezone.utc)
    pt101_asset_id = None

    db = SessionLocal()
    try:
        for sensor_id, val in [("PT-101-PV", p1_val), ("PT-102-PV", p2_val)]:
            row = db.execute(
                text("SELECT asset_id, sensor_type, unit FROM sensor_metadata WHERE sensor_id = :sid"),
                {"sid": sensor_id},
            ).fetchone()
            if not row:
                logger.warning("Sensor %s not found — skipping divergence inject", sensor_id)
                continue

            sensor_asset_id, sensor_type, unit = row
            if sensor_id == "PT-101-PV":
                pt101_asset_id = sensor_asset_id

            db.execute(
                text(
                    "INSERT INTO timeseries "
                    "(timestamp, sensor_id, asset_id, sensor_type, value, unit, quality_flag) "
                    "VALUES (:ts, :sid, :aid, CAST(:stype AS \"SensorType\"), :val, :unit, 'GOOD')"
                ),
                {
                    "ts": now,
                    "sid": sensor_id,
                    "aid": sensor_asset_id,
                    "stype": sensor_type,
                    "val": val,
                    "unit": unit,
                },
            )
        db.commit()
    finally:
        db.close()

    if pt101_asset_id is None:
        logger.warning("PT-101-PV not found in sensor_metadata — divergence run skipped")
        return []

    return pipeline.run(pt101_asset_id)


def _inject_inspection_overdue(asset_id: str, overrides: dict) -> None:
    """
    Back-date the most recent INSPECTION work order to months_ago months ago.
    Also injects a temperature reading above design temp so the corrosion
    detector fires and Layer 2 picks up the overdue inspection in context.
    """
    months_ago = int(overrides.get("months_ago", 18))
    backdated = datetime.now(timezone.utc) - timedelta(days=months_ago * 30)

    db = SessionLocal()
    try:
        db.execute(
            text(
                "UPDATE work_orders SET completed_date = :dt, scheduled_date = :dt "
                "WHERE work_order_id = ("
                "  SELECT work_order_id FROM work_orders "
                "  WHERE asset_id = :aid AND work_order_type = 'INSPECTION' "
                "  AND completed_date IS NOT NULL "
                "  ORDER BY completed_date DESC LIMIT 1"
                ")"
            ),
            {"dt": backdated, "aid": asset_id},
        )
        db.commit()
    finally:
        db.close()

    # Inject a high-temp reading so corrosion detection fires with this context
    baseline = CORROSION_BASELINE.get(asset_id)
    if baseline:
        temp_celsius = float(overrides.get("temperature_celsius", 130.0))
        db2 = SessionLocal()
        try:
            db2.execute(
                text(
                    "INSERT INTO timeseries "
                    "(timestamp, sensor_id, asset_id, sensor_type, value, unit, quality_flag) "
                    "VALUES (:ts, :sid, :aid, 'TEMPERATURE', :val, 'degC', 'GOOD')"
                ),
                {
                    "ts": datetime.now(timezone.utc),
                    "sid": baseline["temp_sensor_id"],
                    "aid": asset_id,
                    "val": temp_celsius,
                },
            )
            db2.commit()
        finally:
            db2.close()
