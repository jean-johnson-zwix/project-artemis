from datetime import datetime
from typing import Any


def check_threshold(
    reading_value: float,
    reading_unit: str,
    reading_timestamp: datetime,
    sensor_meta: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Returns detection_data dict if a threshold breach is detected, else None.
    Severity is returned alongside as a tuple.
    """
    alarm_low = sensor_meta.get("alarm_low")
    alarm_high = sensor_meta.get("alarm_high")
    trip_low = sensor_meta.get("trip_low")
    trip_high = sensor_meta.get("trip_high")

    severity = None

    if trip_high is not None and reading_value > trip_high:
        severity = "CRITICAL"
    elif trip_low is not None and reading_value < trip_low:
        severity = "CRITICAL"
    elif alarm_high is not None and reading_value > alarm_high:
        severity = "HIGH"
    elif alarm_low is not None and reading_value < alarm_low:
        severity = "HIGH"

    if severity is None:
        return None

    return {
        "severity": severity,
        "detection_data": {
            "sensor_id": sensor_meta["sensor_id"],
            "sensor_tag": sensor_meta.get("sensor_tag"),
            "sensor_type": sensor_meta.get("sensor_type"),
            "anomaly_value": reading_value,
            "anomaly_unit": reading_unit,
            "anomaly_timestamp": reading_timestamp.isoformat(),
            "rolling_mean": None,
            "rolling_stddev": None,
            "z_score": None,
            "window_hours": None,
        },
    }
