"""
Database connection and session management.

Provides:
  - get_db(): FastAPI dependency that yields a SQLAlchemy session
  - write_detection(db, detection): persist a DetectionRecord to the detections table
  - write_insight(db, insight): persist an Insight to the insights table
"""

import json
import os
import uuid

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from models import DetectionRecord, Insight, RelevantDoc

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_SEVERITY_TO_ASSET_STATUS = {
    "CRITICAL": "MAINTENANCE",
    "HIGH": "MAINTENANCE",
    "MEDIUM": "STANDBY",
    "LOW": "STANDBY",
}


def update_asset_status(db: Session, asset_id: str, status: str) -> None:
    """Update the operational status of an asset in the assets table."""
    db.execute(
        text('UPDATE assets SET status = CAST(:status AS "AssetStatus") WHERE asset_id = :asset_id'),
        {"asset_id": asset_id, "status": status},
    )
    db.commit()


def write_detection(db: Session, record: DetectionRecord) -> None:
    """Persist a DetectionRecord to the detections table and update the asset status."""
    db.execute(
        text(
            "INSERT INTO detections "
            "(detection_id, detected_at, detection_type, severity, asset_id, asset_tag, asset_name, area, detection_data) "
            "VALUES (:id, :detected_at, :type, :severity, :asset_id, :asset_tag, :asset_name, :area, CAST(:data AS jsonb))"
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
            "data": json.dumps(record.detection_data),
        },
    )
    db.commit()

    new_status = _SEVERITY_TO_ASSET_STATUS.get(str(record.severity).upper())
    if new_status:
        update_asset_status(db, record.asset_id, new_status)


def resolve_detection(db: Session, detection_id: str, resolved_by: str) -> dict | None:
    """
    Mark a detection as resolved and restore the asset to OPERATING status.

    Returns a dict with detection metadata on success, or None if the detection
    was not found or was already resolved.
    """
    import datetime as _dt

    result = db.execute(
        text(
            "UPDATE detections "
            "SET resolved_at = :now, resolved_by = :by "
            "WHERE detection_id = CAST(:id AS uuid) "
            "  AND resolved_at IS NULL "
            "RETURNING asset_id, asset_tag, asset_name, area, detection_type, severity"
        ),
        {"now": _dt.datetime.now(_dt.timezone.utc), "by": resolved_by, "id": detection_id},
    )
    row = result.fetchone()
    db.commit()

    if row is None:
        return None

    asset_id, asset_tag, asset_name, area, detection_type, severity = row

    # Restore asset to OPERATING only when no other active detections remain
    remaining = db.execute(
        text(
            "SELECT COUNT(*) FROM detections "
            "WHERE asset_id = :asset_id AND resolved_at IS NULL"
        ),
        {"asset_id": asset_id},
    ).scalar()
    if remaining == 0:
        update_asset_status(db, asset_id, "OPERATING")

    return {
        "detection_id": detection_id,
        "resolved_by": resolved_by,
        "asset_id": asset_id,
        "asset_tag": asset_tag,
        "asset_name": asset_name,
        "area": area,
        "detection_type": detection_type,
        "severity": severity,
    }


def write_insight(
    db: Session,
    insight: Insight,
    relevant_docs: list[RelevantDoc] | None = None,
) -> None:
    """Persist an Insight to the insights table, including relevant_docs if provided."""
    docs_json = json.dumps([d.model_dump() for d in relevant_docs]) if relevant_docs else None
    db.execute(
        text(
            "INSERT INTO insights "
            "(insight_id, detection_id, what, why, evidence, confidence, "
            " remaining_life_years, recommended_actions, relevant_docs) "
            "VALUES (:id, :did, :what, :why, CAST(:evidence AS jsonb), :confidence, "
            "        :rl, CAST(:actions AS jsonb), CAST(:docs AS jsonb))"
        ),
        {
            "id": str(uuid.uuid4()),
            "did": str(insight.detection_id),
            "what": insight.what,
            "why": insight.why,
            "evidence": json.dumps(insight.evidence),
            "confidence": insight.confidence.value,
            "rl": insight.remaining_life_years,
            "actions": json.dumps(insight.recommended_actions),
            "docs": docs_json,
        },
    )
    db.commit()
