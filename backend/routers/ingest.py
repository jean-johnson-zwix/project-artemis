import logging
import os
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import get_db
from detection.corrosion import check_corrosion
from detection.divergence import check_divergence
from detection.statistical import check_statistical
from detection.threshold import check_threshold
from models import DetectionRecord, IngestResponse, SensorReading

logger = logging.getLogger(__name__)

router = APIRouter()

LAYER2_WEBHOOK_URL = os.getenv("LAYER2_WEBHOOK_URL")

COOLDOWNS = {
    "SENSOR_ANOMALY": 1,
    "CORROSION_THRESHOLD": 4,
    "TRANSMITTER_DIVERGENCE": 1,
}

DIVERGENCE_PAIR = {"PT-101-PV", "PT-102-PV"}


def _is_duplicate(db: Session, asset_id: str, detection_type: str, cooldown_hours: int) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM detections WHERE asset_id = :asset_id "
            "AND detection_type = :type "
            "AND detected_at > now() - interval '1 hour' * :hours "
            "LIMIT 1"
        ),
        {"asset_id": asset_id, "type": detection_type, "hours": cooldown_hours},
    ).fetchone()
    return row is not None


def _write_detection(db: Session, record: DetectionRecord) -> None:
    db.execute(
        text(
            "INSERT INTO detections "
            "(detection_id, detected_at, detection_type, severity, asset_id, asset_tag, asset_name, area, detection_data) "
            "VALUES (:id, :detected_at, :type, :severity, :asset_id, :asset_tag, :asset_name, :area, :data::jsonb)"
        ),
        {
            "id": record.detection_id,
            "detected_at": record.detected_at,
            "type": record.detection_type,
            "severity": record.severity,
            "asset_id": record.asset_id,
            "asset_tag": record.asset_tag,
            "asset_name": record.asset_name,
            "area": record.area,
            "data": __import__("json").dumps(record.detection_data),
        },
    )
    db.commit()


def _fire_webhook(detection: DetectionRecord) -> None:
    if not LAYER2_WEBHOOK_URL:
        return
    try:
        httpx.post(LAYER2_WEBHOOK_URL, json=detection.model_dump(mode="json"), timeout=5.0)
    except Exception as exc:
        logger.warning("Layer 2 webhook failed: %s", exc)


@router.post("/ingest/reading", response_model=IngestResponse)
def ingest_reading(reading: SensorReading, db: Session = Depends(get_db)):
    # 1. Load sensor metadata
    meta_row = db.execute(
        text("SELECT * FROM sensor_metadata WHERE sensor_id = :sid"),
        {"sid": reading.sensor_id},
    ).mappings().fetchone()

    if meta_row is None:
        raise HTTPException(status_code=404, detail=f"Unknown sensor_id: {reading.sensor_id}")

    sensor_meta = dict(meta_row)
    sensor_meta["sensor_id"] = reading.sensor_id

    # 2. Load asset info
    asset_row = db.execute(
        text("SELECT * FROM assets WHERE asset_id = :aid"),
        {"aid": reading.asset_id},
    ).mappings().fetchone()

    if asset_row is None:
        raise HTTPException(status_code=404, detail=f"Unknown asset_id: {reading.asset_id}")

    asset = dict(asset_row)

    # 3. Write reading to timeseries
    db.execute(
        text(
            "INSERT INTO timeseries (timestamp, sensor_id, asset_id, sensor_type, value, unit, quality_flag) "
            'VALUES (:ts, :sid, :aid, :stype, :val, :unit, :qf::"QualityFlag")'
        ),
        {
            "ts": reading.timestamp,
            "sid": reading.sensor_id,
            "aid": reading.asset_id,
            "stype": sensor_meta["sensor_type"],
            "val": reading.value,
            "unit": reading.unit,
            "qf": reading.quality_flag,
        },
    )
    db.commit()

    fired_detections: list[DetectionRecord] = []

    def _make_record(detection_type: str, result: dict) -> DetectionRecord:
        return DetectionRecord(
            detection_id=str(uuid.uuid4()),
            detected_at=datetime.now(timezone.utc),
            detection_type=detection_type,
            severity=result["severity"],
            asset_id=reading.asset_id,
            asset_tag=asset["tag"],
            asset_name=asset["name"],
            area=asset.get("area") or "",
            detection_data=result["detection_data"],
        )

    def _maybe_fire(detection_type: str, result: dict | None) -> None:
        if result is None:
            return
        cooldown = COOLDOWNS.get(detection_type, 1)
        if _is_duplicate(db, reading.asset_id, detection_type, cooldown):
            return
        record = _make_record(detection_type, result)
        _write_detection(db, record)
        _fire_webhook(record)
        fired_detections.append(record)

    # 4a. Threshold detection
    threshold_result = check_threshold(
        reading_value=reading.value,
        reading_unit=reading.unit,
        reading_timestamp=reading.timestamp,
        sensor_meta=sensor_meta,
    )
    _maybe_fire("SENSOR_ANOMALY", threshold_result)

    # 4b. Statistical (Z-score) detection
    recent_rows = db.execute(
        text(
            "SELECT value FROM timeseries "
            "WHERE sensor_id = :sid AND timestamp >= now() - interval '24 hours' "
            "ORDER BY timestamp"
        ),
        {"sid": reading.sensor_id},
    ).fetchall()
    recent_values = [r[0] for r in recent_rows]

    statistical_result = check_statistical(
        reading_value=reading.value,
        reading_unit=reading.unit,
        reading_timestamp=reading.timestamp,
        quality_flag=reading.quality_flag,
        sensor_meta=sensor_meta,
        recent_values=recent_values,
    )
    _maybe_fire("SENSOR_ANOMALY", statistical_result)

    # 4c. Transmitter divergence (PT-101-PV / PT-102-PV only)
    if reading.sensor_id in DIVERGENCE_PAIR:
        other_id = (DIVERGENCE_PAIR - {reading.sensor_id}).pop()
        other_row = db.execute(
            text(
                "SELECT value, timestamp, unit FROM timeseries "
                "WHERE sensor_id = :sid ORDER BY timestamp DESC LIMIT 1"
            ),
            {"sid": other_id},
        ).fetchone()

        if other_row is not None:
            other_meta = db.execute(
                text("SELECT tag FROM sensor_metadata WHERE sensor_id = :sid"),
                {"sid": other_id},
            ).mappings().fetchone()

            sensor_tags = {
                reading.sensor_id: sensor_meta.get("tag", reading.sensor_id),
                other_id: dict(other_meta)["tag"] if other_meta else other_id,
            }

            divergence_result = check_divergence(
                current_sensor_id=reading.sensor_id,
                current_value=reading.value,
                current_timestamp=reading.timestamp,
                other_sensor_id=other_id,
                other_value=other_row[0],
                other_timestamp=other_row[1],
                unit=reading.unit,
                sensor_tags=sensor_tags,
            )
            _maybe_fire("TRANSMITTER_DIVERGENCE", divergence_result)

    # 4d. Corrosion detection (temperature sensors only)
    if sensor_meta.get("sensor_type") == "TEMPERATURE":
        corrosion_result = check_corrosion(
            asset_id=reading.asset_id,
            current_temp=reading.value,
        )
        _maybe_fire("CORROSION_THRESHOLD", corrosion_result)

    return IngestResponse(
        written=True,
        detections_fired=[d.detection_id for d in fired_detections],
    )
