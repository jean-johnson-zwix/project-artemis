"""
Layer 2 — Context Gathering

Blocked on Azure keys for semantic search.
Stub with keyword search first; swap to embeddings when keys arrive.

Given a Detection, pulls all supporting material:
  1. Latest sensor readings for the affected asset (last 24 h trend)
  2. Relevant documents via semantic search (Azure embeddings) — or keyword
     fallback while keys are unavailable
  3. Last work orders + last inspection date for the asset
  4. For corrosion detections: parse inspection report for wall thickness,
     coating %, corrosion rate, remaining allowance

Returns a DetectionContext.
"""

from __future__ import annotations

from models import Detection, DetectionContext  # noqa: F401


def gather_context(detection: Detection) -> DetectionContext:
    """
    Fetch all context relevant to the given detection.

    Uses semantic search when AZURE_OPENAI_API_KEY is set,
    falls back to keyword search otherwise.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Sub-task stubs
# ---------------------------------------------------------------------------


def _fetch_sensor_trend(asset_id: str, hours: int = 24):
    """Return the last `hours` of timeseries rows for the asset."""
    raise NotImplementedError


def _search_documents_semantic(asset_id: str, query: str):
    """Embed the query and retrieve top-k docs via pgvector cosine search."""
    raise NotImplementedError


def _search_documents_keyword(asset_id: str, query: str):
    """Keyword fallback — ILIKE search on document content."""
    raise NotImplementedError


def _fetch_last_work_order(asset_id: str):
    """Return the most recent WorkOrder for the asset."""
    raise NotImplementedError


def _fetch_last_inspection_date(asset_id: str):
    """Return the date of the last inspection-type WorkOrder."""
    raise NotImplementedError


def _parse_inspection_values(doc_content: str):
    """
    Extract wall_thickness_mm, coating_failure_pct, corrosion_rate,
    and remaining_allowance_mm from an inspection report text.
    """
    raise NotImplementedError
