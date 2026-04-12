import math
from datetime import datetime
from typing import Any


def check_statistical(
    reading_value: float,
    reading_unit: str,
    reading_timestamp: datetime,
    quality_flag: str,
    sensor_meta: dict[str, Any],
    recent_values: list[float],
) -> dict[str, Any] | None:
    """
    Z-score anomaly detection over a 24h rolling window.
    Returns detection payload dict (with 'severity' key) or None.
    """
    if quality_flag != "GOOD":
        return None

    if len(recent_values) < 30:
        return None

    n = len(recent_values)
    mean = sum(recent_values) / n
    variance = sum((v - mean) ** 2 for v in recent_values) / n
    stddev = math.sqrt(variance)

    if stddev == 0:
        return None

    z = (reading_value - mean) / stddev

    if abs(z) <= 3.0:
        return None

    severity = "HIGH" if abs(z) > 4.0 else "MEDIUM"

    return {
        "severity": severity,
        "detection_data": {
            "sensor_id": sensor_meta["sensor_id"],
            "sensor_tag": sensor_meta.get("sensor_tag"),
            "sensor_type": sensor_meta.get("sensor_type"),
            "anomaly_value": reading_value,
            "anomaly_unit": reading_unit,
            "anomaly_timestamp": reading_timestamp.isoformat(),
            "rolling_mean": round(mean, 4),
            "rolling_stddev": round(stddev, 4),
            "z_score": round(z, 4),
            "window_hours": 24,
        },
    }
