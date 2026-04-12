from datetime import datetime
from typing import Any

TOLERANCE_PCT = 5.0
STALENESS_MINUTES = 5


def check_divergence(
    current_sensor_id: str,
    current_value: float,
    current_timestamp: datetime,
    other_sensor_id: str,
    other_value: float,
    other_timestamp: datetime,
    unit: str,
    sensor_tags: dict[str, str],  # sensor_id -> sensor_tag
) -> dict[str, Any] | None:
    """
    Compares PT-101-PV vs PT-102-PV readings.
    Returns detection payload dict (with 'severity' key) or None.
    """
    delta_seconds = abs((current_timestamp - other_timestamp).total_seconds())
    if delta_seconds > STALENESS_MINUTES * 60:
        return None

    avg = (current_value + other_value) / 2
    if avg == 0:
        return None

    divergence_pct = abs(current_value - other_value) / avg * 100

    if divergence_pct <= TOLERANCE_PCT:
        return None

    severity = "HIGH" if divergence_pct > 10.0 else "MEDIUM"

    return {
        "severity": severity,
        "detection_data": {
            "sensor_a_id": current_sensor_id,
            "sensor_a_tag": sensor_tags.get(current_sensor_id),
            "sensor_a_value": current_value,
            "sensor_b_id": other_sensor_id,
            "sensor_b_tag": sensor_tags.get(other_sensor_id),
            "sensor_b_value": other_value,
            "divergence_pct": round(divergence_pct, 4),
            "divergence_absolute": round(abs(current_value - other_value), 4),
            "unit": unit,
            "tolerance_pct": TOLERANCE_PCT,
            "measurement_timestamp": current_timestamp.isoformat(),
        },
    }
