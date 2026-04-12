from datetime import datetime
from typing import Any
from pydantic import BaseModel


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
