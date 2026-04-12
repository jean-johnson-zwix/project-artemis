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

from pydantic import BaseModel


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
# Layer 1 — Detection output
# ---------------------------------------------------------------------------


class Detection(BaseModel):
    detection_id: UUID
    asset_id: str
    detection_type: DetectionType
    severity: Severity
    signal_value: float
    signal_unit: str
    threshold: float
    detected_at: datetime
    raw_inputs: dict[str, Any]


# ---------------------------------------------------------------------------
# Layer 2 — Context output
# ---------------------------------------------------------------------------


class ParsedInspectionValues(BaseModel):
    wall_thickness_mm: float | None = None
    coating_failure_pct: float | None = None
    corrosion_rate_mm_per_year: float | None = None
    remaining_allowance_mm: float | None = None


class SensorReading(BaseModel):
    timestamp: datetime
    sensor_id: str
    value: float
    unit: str


class RelevantDoc(BaseModel):
    doc_id: str
    title: str
    doc_type: str
    snippet: str


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
# Simulator request
# ---------------------------------------------------------------------------


class SimulateEventRequest(BaseModel):
    scenario: SimulationScenario
    asset_id: str = "V-101"
    overrides: dict[str, Any] = {}
