"""
Layer 2 — Context Gathering

Given a DetectionRecord, pulls all supporting material:
  1. Last 24h sensor trend for the affected asset
  2. Relevant documents via hybrid PageIndex retrieval (wiki index + tree search),
     with keyword ILIKE fallback when no API key is set
  3. Most recent work order + last inspection date for the asset
  4. For CORROSION_THRESHOLD: parses inspection report for wall thickness,
     coating %, corrosion rate, remaining allowance

Returns a DetectionContext passed directly to Layer 3.

Document retrieval latency budget (background task — not on hot path):
  Step 1 — wiki index DB read:          ~0s
  Step 2 — candidate selector LLM call: ~1.5s
  Step 3 — tree navigation (parallel):  ~2.0s
  Total:                                ~3.5–4.0s
"""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any
from uuid import UUID

import instructor
from openai import AzureOpenAI
from sqlalchemy import text
from sqlalchemy.orm import Session

from models import (
    CandidateSelection,
    DetectionContext,
    DetectionRecord,
    NodeSelection,
    PageIndexNode,
    ParsedInspectionValues,
    PastResolution,
    RelevantDoc,
    SensorReading,
)

logger = logging.getLogger(__name__)

# Max characters to include from a selected tree node as the snippet sent to Layer 3.
# Unlike the old approach (first 400 chars of the whole doc), this is the actual
# relevant section — so a larger window is safe and more useful.
SECTION_SNIPPET_LENGTH = 800


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
    past_resolutions = _fetch_past_resolutions(db, asset_id, detection_type)

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
        past_resolutions=past_resolutions,
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
    """Route to PageIndex hybrid search or keyword fallback."""
    if os.getenv("AZURE_OPENAI_API_KEY"):
        try:
            return _search_documents_pageindex(db, detection_type, asset_id, asset_name)
        except Exception as exc:
            logger.warning("PageIndex search failed, falling back to keyword: %s", exc)
    return _search_documents_keyword(db, detection_type, asset_id, asset_name)


# ---------------------------------------------------------------------------
# PageIndex hybrid retrieval
# ---------------------------------------------------------------------------


def _get_instructor_client() -> instructor.Instructor:
    raw = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )
    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


def _search_documents_pageindex(
    db: Session,
    detection_type: str,
    asset_id: str,
    asset_name: str,
) -> list[RelevantDoc]:
    """
    Hybrid retrieval:
      Step 1 — fast DB read: load wiki index (no LLM)
      Step 2 — LLM call: select 2-3 candidate doc_ids from wiki index
      Step 3 — parallel LLM calls: navigate each candidate's PageIndex tree
      Step 4 — slice section text from document content by char offsets
    """
    # Step 1: read wiki index — fast, no LLM
    wiki_rows = db.execute(
        text(
            "SELECT w.doc_id, w.doc_type, w.title, w.one_line_summary "
            "FROM wiki_index w "
            "JOIN documents d ON d.doc_id = w.doc_id "
            "WHERE d.indexed_at IS NOT NULL "
            "ORDER BY w.doc_type, w.title"
        )
    ).fetchall()

    if not wiki_rows:
        logger.warning("Wiki index is empty — falling back to keyword search")
        return _search_documents_keyword(db, detection_type, asset_id, asset_name)

    # Step 2: LLM selects candidates from wiki index
    candidate_ids = _select_candidates(wiki_rows, detection_type, asset_id, asset_name)
    if not candidate_ids:
        logger.warning("Candidate selector returned no results — falling back to keyword search")
        return _search_documents_keyword(db, detection_type, asset_id, asset_name)

    # Load trees for all candidates in one query
    placeholders = ", ".join(f":id{i}" for i in range(len(candidate_ids)))
    params = {f"id{i}": doc_id for i, doc_id in enumerate(candidate_ids)}
    tree_rows = db.execute(
        text(
            f"SELECT doc_id, title, doc_type, content, page_index_tree "
            f"FROM documents WHERE doc_id IN ({placeholders})"
        ),
        params,
    ).fetchall()

    if not tree_rows:
        return _search_documents_keyword(db, detection_type, asset_id, asset_name)

    # Step 3: parallel tree navigation across candidates
    query_context = _build_query_context(detection_type, asset_id, asset_name)
    results: list[RelevantDoc] = []

    with ThreadPoolExecutor(max_workers=len(tree_rows)) as executor:
        futures = {
            executor.submit(
                _navigate_and_slice,
                row[0],  # doc_id
                row[1],  # title
                row[2],  # doc_type
                row[3],  # content
                row[4],  # page_index_tree (dict from DB)
                query_context,
            ): row[0]
            for row in tree_rows
        }
        for future in as_completed(futures):
            doc_id = futures[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as exc:
                logger.warning("Tree navigation failed for %s: %s", doc_id, exc)

    # Sort by original candidate ranking (most relevant first)
    id_order = {doc_id: i for i, doc_id in enumerate(candidate_ids)}
    results.sort(key=lambda r: id_order.get(r.doc_id, 99))

    return results


def _select_candidates(
    wiki_rows: list,
    detection_type: str,
    asset_id: str,
    asset_name: str,
) -> list[str]:
    """
    LLM call (instructor-enforced) that reads the wiki index table and returns
    2-3 doc_ids most relevant to the detection. Fast: structured input, minimal output.
    """
    client = _get_instructor_client()
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    # Format wiki index as compact table for LLM
    table_lines = ["doc_id | doc_type | title | summary"]
    table_lines.append("-" * 80)
    for row in wiki_rows:
        table_lines.append(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")
    wiki_table = "\n".join(table_lines)

    detection_desc = _build_query_context(detection_type, asset_id, asset_name)

    user_message = (
        f"Detection: {detection_desc}\n\n"
        f"Available documents:\n{wiki_table}\n\n"
        f"Return the 2–3 most relevant doc_ids. "
        f"Prioritise documents that explicitly mention the asset tag in their summary."
    )

    selection: CandidateSelection = client.chat.completions.create(
        model=deployment,
        response_model=CandidateSelection,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are selecting technical documents relevant to an industrial maintenance detection. "
                    "Return only doc_ids that exist in the provided table. "
                    "Order by relevance — most relevant first."
                ),
            },
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
        max_tokens=200,
        max_retries=3,
    )

    logger.info("Candidate selection: %s — %s", selection.doc_ids, selection.reasoning)
    return selection.doc_ids


def _navigate_and_slice(
    doc_id: str,
    title: str,
    doc_type: str,
    content: str,
    tree_data: dict | None,
    query_context: str,
) -> RelevantDoc | None:
    """
    Navigate a document's PageIndex tree to find the most relevant section,
    then slice the section text from content using character offsets.
    Returns a RelevantDoc with tree_path populated, or None if navigation fails.
    """
    if not tree_data:
        logger.warning("No tree for %s — skipping", doc_id)
        return None

    try:
        tree = PageIndexNode.model_validate(tree_data)
    except Exception as exc:
        logger.warning("Tree validation failed for %s: %s", doc_id, exc)
        return None

    client = _get_instructor_client()
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    tree_json = tree.model_dump_json(indent=2)

    user_message = (
        f"Query: {query_context}\n\n"
        f"Document: {title} ({doc_type})\n\n"
        f"Index tree:\n{tree_json}\n\n"
        f"Navigate to the single most relevant section. Return its node details."
    )

    selection: NodeSelection = client.chat.completions.create(
        model=deployment,
        response_model=NodeSelection,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are navigating a document index tree to find the most relevant section "
                    "for an industrial maintenance detection. "
                    "Reason over node summaries to identify the best section. "
                    "Return start_index and end_index as character offsets from the tree. "
                    "tree_path must be a breadcrumb using › as separator."
                ),
            },
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
        max_tokens=300,
        max_retries=3,
    )

    logger.info(
        "Tree nav %s → %s (%s): %s",
        doc_id, selection.node_id, selection.tree_path, selection.reasoning,
    )

    # Slice section text — clamp to content bounds
    start = max(0, selection.start_index)
    end = min(len(content), selection.end_index)
    section_text = content[start:end]

    # Trim to snippet length for Layer 3 prompt budget
    snippet = section_text[:SECTION_SNIPPET_LENGTH]
    if len(section_text) > SECTION_SNIPPET_LENGTH:
        snippet += "…"

    return RelevantDoc(
        doc_id=doc_id,
        title=title,
        doc_type=doc_type,
        snippet=snippet,
        tree_path=selection.tree_path,
    )


def _build_query_context(detection_type: str, asset_id: str, asset_name: str) -> str:
    """Build a human-readable query description for the LLM calls."""
    if detection_type == "CORROSION_THRESHOLD":
        return (
            f"CORROSION_THRESHOLD on {asset_name} (asset_id: {asset_id}). "
            "Looking for: wall thickness measurements, corrosion rate, coating condition, "
            "remaining allowance, inspection findings."
        )
    if detection_type == "TRANSMITTER_DIVERGENCE":
        return (
            f"TRANSMITTER_DIVERGENCE on {asset_name} (asset_id: {asset_id}). "
            "Looking for: pressure transmitter calibration, divergence limits, "
            "instrument maintenance procedures."
        )
    return (
        f"SENSOR_ANOMALY on {asset_name} (asset_id: {asset_id}). "
        "Looking for: sensor alarm limits, anomaly response procedures, "
        "historical failure context."
    )


# ---------------------------------------------------------------------------
# Keyword fallback (no API key or PageIndex failure)
# ---------------------------------------------------------------------------


def _search_documents_keyword(
    db: Session,
    detection_type: str,
    asset_id: str,
    asset_name: str,
) -> list[RelevantDoc]:
    """ILIKE fallback — searches document content for key terms."""
    query = _build_keyword_query(detection_type, asset_name)
    stopwords = {"anomaly", "breach", "and", "the", "for", "via"}
    words = [w for w in query.split() if w.lower() not in stopwords]
    keyword = words[0] if words else query.split()[0]

    # Match exact asset, same area (asset_id starts with area prefix), or unlinked docs
    area_prefix = asset_id.split(":")[0] if ":" in asset_id else asset_id
    rows = db.execute(
        text(
            "SELECT doc_id, title, doc_type, LEFT(content, 400) AS snippet "
            "FROM documents "
            "WHERE (asset_id = :aid OR asset_id LIKE :area OR asset_id IS NULL) "
            "  AND content ILIKE :kw "
            "ORDER BY issue_date DESC "
            "LIMIT 5"
        ),
        {"aid": asset_id, "area": f"{area_prefix}:%", "kw": f"%{keyword}%"},
    ).fetchall()

    return [RelevantDoc(doc_id=r[0], title=r[1], doc_type=r[2], snippet=r[3]) for r in rows]


def _build_keyword_query(detection_type: str, asset_name: str) -> str:
    if detection_type == "CORROSION_THRESHOLD":
        return f"corrosion inspection wall thickness coating rate allowance {asset_name}"
    if detection_type == "TRANSMITTER_DIVERGENCE":
        return f"pressure transmitter calibration divergence {asset_name}"
    return f"sensor anomaly threshold breach {asset_name}"


# ---------------------------------------------------------------------------
# Work order and inspection helpers (unchanged)
# ---------------------------------------------------------------------------


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


def _fetch_past_resolutions(
    db: Session, asset_id: str, detection_type: str, limit: int = 5
) -> list[PastResolution]:
    """
    Return the last `limit` resolved detections of the same type for this asset,
    newest first. Only includes detections that were explicitly resolved with notes.
    """
    rows = db.execute(
        text(
            "SELECT detection_id, detected_at, severity, resolution_notes, resolved_by, resolved_at "
            "FROM detections "
            "WHERE asset_id = :aid "
            "  AND detection_type = :dtype "
            "  AND resolved_at IS NOT NULL "
            "ORDER BY resolved_at DESC "
            "LIMIT :lim"
        ),
        {"aid": asset_id, "dtype": detection_type, "lim": limit},
    ).fetchall()

    return [
        PastResolution(
            detection_id=str(r[0]),
            detected_at=r[1],
            severity=r[2],
            resolution_notes=r[3],
            resolved_by=r[4],
            resolved_at=r[5],
        )
        for r in rows
    ]


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
