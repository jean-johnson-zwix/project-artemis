"""
Database connection and session management.

Provides:
  - get_db(): FastAPI dependency that yields a SQLAlchemy session
  - write_detection(detection): persist a DetectionRecord to the detections table
  - write_insight(insight): persist an Insight record to the insights table (TODO)
  - get_detection(detection_id): fetch a single Detection by ID (TODO)
"""

import json
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from models import DetectionRecord

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


def write_detection(db: Session, record: DetectionRecord) -> None:
    """Persist a DetectionRecord to the detections table."""
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


def write_insight(insight) -> None:
    """Persist an Insight record to the insights table."""
    raise NotImplementedError


def get_detection(detection_id) -> None:
    """Fetch a single Detection by ID."""
    raise NotImplementedError
