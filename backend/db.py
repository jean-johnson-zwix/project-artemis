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
