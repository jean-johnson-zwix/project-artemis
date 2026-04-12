"""
Database connection and session management.

Provides:
  - get_db(): FastAPI dependency that yields a SQLAlchemy session
  - write_detection(detection): persist a DetectionRecord to the detections table
  - write_insight(insight): persist an Insight record to the insights table (TODO)
  - get_detection(detection_id): fetch a single Detection by ID (TODO)
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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


# TODO: write_insight(insight: Insight) -> None
# TODO: get_detection(detection_id: UUID) -> Detection | None
