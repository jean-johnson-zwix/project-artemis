"""
Pipeline orchestrator — runs Layer 1 → 2 → 3 for a given asset.

Called two ways:
  1. APScheduler tick (every 60 s) — run_all_assets() scans all OPERATING assets
  2. Simulator endpoint (POST /simulate/event) — run(asset_id) for one asset on demand
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from db import SessionLocal, write_detection
from detection.corrosion import check_corrosion
from detection.divergence import check_divergence
from detection.statistical import check_statistical
from detection.threshold import check_threshold
from models import DetectionRecord

logger = logging.getLogger(__name__)

COOLDOWNS = {
    "SENSOR_ANOMALY": 1,
    "CORROSION_THRESHOLD": 4,
    "TRANSMITTER_DIVERGENCE": 1,
}

DIVERGENCE_PAIR = {"PT-101-PV", "PT-102-PV"}


def run(asset_id: str) -> list[str]:
    """
    Run the full detection pipeline for one asset.
    Reads the latest timeseries value per sensor, runs all detectors,
    writes confirmed detections, and triggers Layer 2+3 in background threads.
    Returns a list of detection_ids that fired.
    """
    from routers.detections import _process_detection

    fired: list[DetectionRecord] = []
    db = SessionLocal()

    try:
        asset_row = db.execute(
            text("SELECT * FROM assets WHERE asset_id = :aid"),
            {"aid": asset_id},
        ).mappings().fetchone()

        if not asset_row:
            logger.warning("pipeline.run: unknown asset_id %s", asset_id)
            return []

        asset = dict(asset_row)

        sensors = db.execute(
            text("SELECT * FROM sensor_metadata WHERE asset_id = :aid"),
            {"aid": asset_id},
        ).mappings().fetchall()

        for sensor_row in sensors:
            sensor_meta = dict(sensor_row)
            sensor_id = sensor_meta["sensor_id"]

            latest = db.execute(
                text(
                    "SELECT value, unit, timestamp, quality_flag FROM timeseries "
                    "WHERE sensor_id = :sid ORDER BY timestamp DESC LIMIT 1"
                ),
                {"sid": sensor_id},
            ).fetchone()

            if not latest:
                continue

            value, unit, ts, quality_flag = latest
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            # Threshold
            record = _maybe_fire(db, asset, "SENSOR_ANOMALY",
                                 check_threshold(value, unit, ts, sensor_meta))
            if record:
                fired.append(record)

            # Statistical (Z-score)
            recent = db.execute(
                text(
                    "SELECT value FROM timeseries "
                    "WHERE sensor_id = :sid AND timestamp >= now() - interval '24 hours' "
                    "ORDER BY timestamp"
                ),
                {"sid": sensor_id},
            ).fetchall()
            record = _maybe_fire(db, asset, "SENSOR_ANOMALY",
                                 check_statistical(value, unit, ts, quality_flag,
                                                   sensor_meta, [r[0] for r in recent]))
            if record:
                fired.append(record)

            # Transmitter divergence (PT-101-PV / PT-102-PV only)
            if sensor_id in DIVERGENCE_PAIR:
                other_id = (DIVERGENCE_PAIR - {sensor_id}).pop()
                other = db.execute(
                    text(
                        "SELECT value, timestamp, unit FROM timeseries "
                        "WHERE sensor_id = :sid ORDER BY timestamp DESC LIMIT 1"
                    ),
                    {"sid": other_id},
                ).fetchone()
                if other:
                    other_ts = other[1]
                    if other_ts.tzinfo is None:
                        other_ts = other_ts.replace(tzinfo=timezone.utc)
                    other_meta = db.execute(
                        text("SELECT tag FROM sensor_metadata WHERE sensor_id = :sid"),
                        {"sid": other_id},
                    ).mappings().fetchone()
                    sensor_tags = {
                        sensor_id: sensor_meta.get("tag", sensor_id),
                        other_id: dict(other_meta)["tag"] if other_meta else other_id,
                    }
                    record = _maybe_fire(
                        db, asset, "TRANSMITTER_DIVERGENCE",
                        check_divergence(sensor_id, value, ts,
                                         other_id, other[0], other_ts,
                                         unit, sensor_tags),
                    )
                    if record:
                        fired.append(record)

            # Corrosion (temperature sensors only)
            if sensor_meta.get("sensor_type") == "TEMPERATURE":
                record = _maybe_fire(db, asset, "CORROSION_THRESHOLD",
                                     check_corrosion(asset_id, value))
                if record:
                    fired.append(record)

    except Exception as exc:
        logger.error("pipeline.run failed for asset %s: %s", asset_id, exc, exc_info=True)
    finally:
        db.close()

    # Trigger Layer 2+3 after DB session is closed — each opens its own session
    for record in fired:
        threading.Thread(target=_process_detection, args=(record,), daemon=True).start()

    return [r.detection_id for r in fired]


def run_all_assets() -> None:
    """
    Fetch all OPERATING assets and run the pipeline for each.
    Registered with APScheduler — runs every 60 seconds.
    Failures per asset are caught individually so one bad asset doesn't halt the tick.
    """
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT asset_id FROM assets WHERE status = 'OPERATING'"),
        ).fetchall()
        asset_ids = [r[0] for r in rows]
    except Exception as exc:
        logger.error("run_all_assets: failed to fetch assets: %s", exc)
        return
    finally:
        db.close()

    logger.info("APScheduler tick: scanning %d active assets", len(asset_ids))
    for asset_id in asset_ids:
        try:
            fired = run(asset_id)
            if fired:
                logger.info("Detections fired for %s: %s", asset_id, fired)
        except Exception as exc:
            logger.error("pipeline.run failed for asset %s: %s", asset_id, exc)


def _maybe_fire(
    db,
    asset: dict,
    detection_type: str,
    result: dict | None,
) -> DetectionRecord | None:
    """
    Deduplication check + write. Returns the DetectionRecord if fired, else None.
    """
    if result is None:
        return None

    asset_id = asset["asset_id"]
    cooldown = COOLDOWNS.get(detection_type, 1)

    exists = db.execute(
        text(
            "SELECT 1 FROM detections "
            "WHERE asset_id = :aid AND detection_type = :type "
            "AND detected_at > now() - interval '1 hour' * :hours "
            "LIMIT 1"
        ),
        {"aid": asset_id, "type": detection_type, "hours": cooldown},
    ).fetchone()

    if exists:
        return None

    record = DetectionRecord(
        detection_id=str(uuid.uuid4()),
        detected_at=datetime.now(timezone.utc),
        detection_type=detection_type,
        severity=result["severity"],
        asset_id=asset_id,
        asset_tag=asset.get("tag", ""),
        asset_name=asset.get("name", ""),
        area=asset.get("area") or "",
        detection_data=result["detection_data"],
    )
    write_detection(db, record)
    return record
