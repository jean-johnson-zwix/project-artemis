"""
Layer 2 — Context Gathering

Given a DetectionRecord, pulls all supporting material:
  1. Last 24h sensor trend for the affected asset
  2. Relevant documents via semantic search (Azure embeddings) with keyword fallback
  3. Most recent work order + last inspection date for the asset
  4. For CORROSION_THRESHOLD: parses inspection report for wall thickness,
     coating %, corrosion rate, remaining allowance

Returns a DetectionContext passed directly to Layer 3.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import (
    DetectionContext,
    DetectionRecord,
    ParsedInspectionValues,
    RelevantDoc,
    SensorReading,
)

logger = logging.getLogger(__name__)

SNIPPET_LENGTH = 400


def gather_context(detection: DetectionRecord, db: Session) -> DetectionContext:
    """
    Fetch all context relevant to the given detection and return a DetectionContext.
    Called from routers/detections.py as a background task.
    """
    asset_id = detection.asset_id
    detection_type = detection.detection_type

    sensor_trend = _fetch_sensor_trend(db, asset_id)
    relevant_docs = _search_documents(db, detection_type, asset_id, detection.asset_name)
    last_work_order = _fetch_last_work_order(db, asset_id)
    last_inspection_date = _fetch_last_inspection_date(db, asset_id)

    parsed_inspection_values = None
    if detection_type == "CORROSION_THRESHOLD":
        inspection_docs = [d for d in relevant_docs if "INSPECTION" in d.doc_type.upper()]
        if inspection_docs:
            full_row = db.execute(
                text("SELECT content FROM documents WHERE doc_id = :did"),
                {"did": inspection_docs[0].doc_id},
            ).fetchone()
            if full_row:
                parsed_inspection_values = _parse_inspection_values(full_row[0])

    return DetectionContext(
        detection_id=UUID(detection.detection_id),
        sensor_trend=sensor_trend,
        relevant_docs=relevant_docs,
        last_inspection_date=last_inspection_date,
        last_work_order=last_work_order,
        parsed_inspection_values=parsed_inspection_values,
    )


# ---------------------------------------------------------------------------
# Sub-tasks
# ---------------------------------------------------------------------------


def _fetch_sensor_trend(db: Session, asset_id: str, hours: int = 24) -> list[SensorReading]:
    """Return the last `hours` of timeseries rows for the asset."""
    rows = db.execute(
        text(
            "SELECT sensor_id, asset_id, timestamp, value, unit, quality_flag "
            "FROM timeseries "
            "WHERE asset_id = :aid "
            "  AND timestamp >= now() - interval '1 hour' * :hours "
            "ORDER BY timestamp"
        ),
        {"aid": asset_id, "hours": hours},
    ).fetchall()

    return [
        SensorReading(
            sensor_id=r[0],
            asset_id=r[1],
            timestamp=r[2],
            value=r[3],
            unit=r[4],
            quality_flag=r[5],
        )
        for r in rows
    ]


def _search_documents(
    db: Session,
    detection_type: str,
    asset_id: str,
    asset_name: str,
) -> list[RelevantDoc]:
    """Route to semantic or keyword search depending on whether Azure key is set."""
    if os.getenv("AZURE_OPENAI_API_KEY"):
        try:
            return _search_documents_semantic(db, detection_type, asset_id, asset_name)
        except Exception as exc:
            logger.warning("Semantic search failed, falling back to keyword: %s", exc)
    return _search_documents_keyword(db, detection_type, asset_id, asset_name)


def _build_query_string(detection_type: str, asset_name: str) -> str:
    if detection_type == "CORROSION_THRESHOLD":
        return f"corrosion inspection wall thickness coating rate allowance {asset_name}"
    if detection_type == "TRANSMITTER_DIVERGENCE":
        return f"pressure transmitter calibration divergence {asset_name}"
    return f"sensor anomaly threshold breach {asset_name}"


def _search_documents_semantic(
    db: Session,
    detection_type: str,
    asset_id: str,
    asset_name: str,
) -> list[RelevantDoc]:
    """Embed the query and retrieve top-5 docs via pgvector cosine search."""
    from openai import AzureOpenAI

    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )

    query = _build_query_string(detection_type, asset_name)
    response = client.embeddings.create(
        input=query,
        model=os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
    )
    vec = response.data[0].embedding
    vec_str = "[" + ",".join(str(v) for v in vec) + "]"

    rows = db.execute(
        text(
            f"SELECT doc_id, title, doc_type, LEFT(content, {SNIPPET_LENGTH}) AS snippet "
            "FROM documents "
            "WHERE embedding IS NOT NULL "
            "ORDER BY embedding <=> CAST(:vec AS vector) "
            "LIMIT 5"
        ),
        {"vec": vec_str},
    ).fetchall()

    return [RelevantDoc(doc_id=r[0], title=r[1], doc_type=r[2], snippet=r[3]) for r in rows]


def _search_documents_keyword(
    db: Session,
    detection_type: str,
    asset_id: str,
    asset_name: str,
) -> list[RelevantDoc]:
    """ILIKE fallback — searches document content for key terms."""
    query = _build_query_string(detection_type, asset_name)
    # Take the two most meaningful words from the query (skip generic ones)
    stopwords = {"anomaly", "breach", "and", "the", "for", "via"}
    words = [w for w in query.split() if w.lower() not in stopwords]
    keyword = words[0] if words else query.split()[0]

    rows = db.execute(
        text(
            f"SELECT doc_id, title, doc_type, LEFT(content, {SNIPPET_LENGTH}) AS snippet "
            "FROM documents "
            "WHERE (asset_id = :aid OR asset_id IS NULL) "
            "  AND content ILIKE :kw "
            "ORDER BY issue_date DESC "
            "LIMIT 5"
        ),
        {"aid": asset_id, "kw": f"%{keyword}%"},
    ).fetchall()

    return [RelevantDoc(doc_id=r[0], title=r[1], doc_type=r[2], snippet=r[3]) for r in rows]


def _fetch_last_work_order(db: Session, asset_id: str) -> dict[str, Any] | None:
    """Return the most recent WorkOrder for the asset."""
    row = db.execute(
        text(
            "SELECT work_order_id, work_order_type, priority, status, "
            "       raised_date, work_description, findings, actions_taken "
            "FROM work_orders "
            "WHERE asset_id = :aid "
            "ORDER BY raised_date DESC LIMIT 1"
        ),
        {"aid": asset_id},
    ).mappings().fetchone()

    return dict(row) if row else None


def _fetch_last_inspection_date(db: Session, asset_id: str) -> datetime | None:
    """Return the completed date of the most recent INSPECTION work order."""
    row = db.execute(
        text(
            "SELECT completed_date FROM work_orders "
            "WHERE asset_id = :aid "
            "  AND work_order_type = 'INSPECTION' "
            "  AND completed_date IS NOT NULL "
            "ORDER BY completed_date DESC LIMIT 1"
        ),
        {"aid": asset_id},
    ).fetchone()

    return row[0] if row else None


def _parse_inspection_values(content: str) -> ParsedInspectionValues | None:
    """
    Extract corrosion-related values from inspection report text using regex.
    Patterns matched against RPT-INSPECT-001 format — tolerant of spacing variation.
    Returns None if no values found at all.
    """

    def extract(pattern: str) -> float | None:
        m = re.search(pattern, content, re.IGNORECASE)
        return float(m.group(1)) if m else None

    wall_thickness = extract(r"[Mm]inimum recorded[^:]*:\s*([\d.]+)\s*mm")
    coating_pct = extract(r"([\d.]+)\s*%\s*holiday")
    corrosion_rate = extract(r"[Cc]orrosion rate[^:]*:\s*([\d.]+)\s*mm/year")
    remaining_allowance = extract(r"[Rr]emaining corrosion allowance[^:]*:\s*([\d.]+)\s*mm")

    if not any([wall_thickness, coating_pct, corrosion_rate, remaining_allowance]):
        return None

    return ParsedInspectionValues(
        wall_thickness_mm=wall_thickness,
        coating_failure_pct=coating_pct,
        corrosion_rate_mm_per_year=corrosion_rate,
        remaining_allowance_mm=remaining_allowance,
    )
