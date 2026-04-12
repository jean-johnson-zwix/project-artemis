"""
Database connection and session management.

TODO: initialize SQLAlchemy engine + session factory from DATABASE_URL.
      Provide a get_db() dependency for FastAPI routes.
      Provide helpers used by layers:
        - write_detection(detection: Detection) -> None
        - write_insight(insight: Insight) -> None
        - get_detection(detection_id: UUID) -> Detection | None
"""

from models import Detection, Insight  # noqa: F401


def get_db():
    """FastAPI dependency — yields a DB session."""
    raise NotImplementedError


def write_detection(detection: Detection) -> None:
    """Persist a Detection record to the detections table."""
    raise NotImplementedError


def write_insight(insight: Insight) -> None:
    """Persist an Insight record to the insights table."""
    raise NotImplementedError


def get_detection(detection_id) -> Detection | None:
    """Fetch a single Detection by ID."""
    raise NotImplementedError
