"""
Shared Pydantic models for the detection pipeline.

Agree on these shapes before splitting work across layers.
All layers import from here — do not define models inline.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DetectionType(str, Enum):
    CORROSION_THRESHOLD = "CORROSION_THRESHOLD"
    SENSOR_ANOMALY = "SENSOR_ANOMALY"
    TRANSMITTER_DIVERGENCE = "TRANSMITTER_DIVERGENCE"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Confidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SimulationScenario(str, Enum):
    CORROSION_SPIKE = "corrosion_spike"
    SENSOR_ANOMALY = "sensor_anomaly"
    TRANSMITTER_DIVERGENCE = "transmitter_divergence"
    INSPECTION_OVERDUE = "inspection_overdue"


# ---------------------------------------------------------------------------
# Layer 1 — Ingest / Detection
# ---------------------------------------------------------------------------


class SensorReading(BaseModel):
    sensor_id: str
    asset_id: str
    timestamp: datetime
    value: float
    unit: str
    quality_flag: str  # GOOD | BAD | INTERPOLATED | OFFLINE | UNCERTAIN


class IngestResponse(BaseModel):
    written: bool
    detections_fired: list[str]


class DetectionRecord(BaseModel):
    detection_id: str
    detected_at: datetime
    detection_type: str
    severity: str
    asset_id: str
    asset_tag: str
    asset_name: str
    area: str
    detection_data: dict[str, Any]


# ---------------------------------------------------------------------------
# Layer 2 — Context output
# ---------------------------------------------------------------------------


class ParsedInspectionValues(BaseModel):
    wall_thickness_mm: float | None = None
    coating_failure_pct: float | None = None
    corrosion_rate_mm_per_year: float | None = None
    remaining_allowance_mm: float | None = None


class RelevantDoc(BaseModel):
    doc_id: str
    title: str
    doc_type: str
    snippet: str
    tree_path: str | None = None  # breadcrumb from PageIndex navigation, e.g. "Section 3 › 3.2 Wall Thickness"


class DetectionContext(BaseModel):
    detection_id: UUID
    sensor_trend: list[SensorReading]
    relevant_docs: list[RelevantDoc]
    last_inspection_date: datetime | None
    last_work_order: dict[str, Any] | None
    parsed_inspection_values: ParsedInspectionValues | None


# ---------------------------------------------------------------------------
# Layer 3 — Reasoning / Insight output
# ---------------------------------------------------------------------------


class Insight(BaseModel):
    detection_id: UUID
    what: str
    why: str
    evidence: list[str]
    confidence: Confidence
    remaining_life_years: float | None
    recommended_actions: list[str]


# ---------------------------------------------------------------------------
# PageIndex — tree structure and retrieval models
# ---------------------------------------------------------------------------


class PageIndexNode(BaseModel):
    """One node in the hierarchical document tree. Recursive via `nodes`."""
    title: str
    node_id: str
    start_index: int = Field(description="Character offset into raw document text where this section starts")
    end_index: int = Field(description="Character offset into raw document text where this section ends")
    summary: str = Field(description="One-paragraph summary of this section. MUST list all asset tags (e.g. V-101, PT-101-PV) mentioned in this section.")
    nodes: list[PageIndexNode] = Field(default_factory=list)

PageIndexNode.model_rebuild()


class NodeSelection(BaseModel):
    """Instructor-enforced output of tree navigation — which node is most relevant."""
    node_id: str
    tree_path: str = Field(description="Human-readable breadcrumb, e.g. 'Inspection Report › Section 3 › 3.2 Wall Thickness'")
    start_index: int
    end_index: int
    reasoning: str = Field(description="One sentence explaining why this node is most relevant to the detection")


class CandidateSelection(BaseModel):
    """Instructor-enforced output of wiki index selector — which doc_ids to tree-search."""
    doc_ids: list[str] = Field(description="2-3 most relevant doc_ids from the wiki index, ordered by relevance")
    reasoning: str = Field(description="One sentence explaining the selection")


# ---------------------------------------------------------------------------
# Document ingestion
# ---------------------------------------------------------------------------


class DocumentIngestRequest(BaseModel):
    doc_id: str
    asset_id: str | None = None
    doc_type: str
    title: str
    revision: str | None = None
    author: str | None = None
    issue_date: datetime | None = None
    content: str


# ---------------------------------------------------------------------------
# Simulator request
# ---------------------------------------------------------------------------


class SimulateEventRequest(BaseModel):
    scenario: SimulationScenario
    asset_id: str = "AREA-HP-SEP:V-101"
    overrides: dict[str, Any] = {}
