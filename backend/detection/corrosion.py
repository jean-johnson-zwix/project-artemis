from typing import Any

CORROSION_BASELINE = {
    "AREA-HP-SEP:V-101": {
        "base_corrosion_rate_mm_per_year": 0.25,
        "remaining_allowance_mm": 1.2,
        "wall_thickness_mm": 17.2,
        "coating_failure_pct": 40.0,
        "design_temp_celsius": 120.0,
        "temp_sensor_id": "TT-101-PV",
    }
}


def check_corrosion(
    asset_id: str,
    current_temp: float,
) -> dict[str, Any] | None:
    """
    Corrosion remaining life detection based on live temp + static inspection data.
    Returns detection payload dict (with 'severity' key) or None.
    """
    baseline = CORROSION_BASELINE.get(asset_id)
    if baseline is None:
        return None

    base_rate = baseline["base_corrosion_rate_mm_per_year"]
    remaining_allowance = baseline["remaining_allowance_mm"]
    wall_thickness = baseline["wall_thickness_mm"]
    coating_failure_pct = baseline["coating_failure_pct"]
    design_temp = baseline["design_temp_celsius"]
    temp_sensor_id = baseline["temp_sensor_id"]

    temp_factor = 1 + 0.02 * max(0, current_temp - design_temp)
    coating_factor = 1 + (coating_failure_pct / 100)
    adjusted_rate = base_rate * temp_factor * coating_factor

    if adjusted_rate == 0:
        return None

    remaining_life = remaining_allowance / adjusted_rate

    if remaining_life >= 5.0:
        return None

    if remaining_life < 2.0:
        severity = "CRITICAL"
    elif remaining_life < 3.0:
        severity = "HIGH"
    else:
        severity = "MEDIUM"

    return {
        "severity": severity,
        "detection_data": {
            "base_corrosion_rate_mm_per_year": base_rate,
            "temp_factor": round(temp_factor, 4),
            "coating_factor": round(coating_factor, 4),
            "adjusted_rate_mm_per_year": round(adjusted_rate, 4),
            "remaining_allowance_mm": remaining_allowance,
            "remaining_life_years": round(remaining_life, 4),
            "design_temp_celsius": design_temp,
            "current_temp_celsius": current_temp,
            "temp_sensor_id": temp_sensor_id,
            "coating_failure_pct": coating_failure_pct,
            "wall_thickness_mm": wall_thickness,
        },
    }
