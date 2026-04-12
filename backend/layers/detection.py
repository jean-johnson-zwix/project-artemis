"""
Layer 1 — Detection

No Azure AI keys required. Can run from Hour 0.

Scans timeseries data for signals worth acting on and writes Detection
records to the DB. Called by pipeline.py on a 60-second APScheduler tick.

Detection strategies to implement:
  1. Threshold breaches  — sensor value vs alarm_low/high, trip_low/high
  2. Statistical anomalies — Z-score over 24h rolling window, flag |z| > 3
  3. Corrosion rate trending:
       adjusted_rate   = base_rate × temp_factor × coating_factor
       remaining_life  = remaining_allowance / adjusted_rate
       → fire when remaining_life < threshold
  4. Transmitter divergence — two same-type sensors on same asset diverge
       beyond tolerance (e.g. PT-101A vs PT-101B > 5%)

Each strategy should produce zero or more Detection objects.
write_detection() (from db.py) persists each one.
"""

from __future__ import annotations

from models import Detection  # noqa: F401


def run_detection(asset_id: str) -> list[Detection]:
    """
    Run all detection strategies for the given asset.

    Returns the list of new Detection records created (already persisted).
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Individual strategy stubs — implement each separately
# ---------------------------------------------------------------------------


def _check_threshold_breach(asset_id: str) -> list[Detection]:
    """Flag readings outside alarm_low / alarm_high / trip_low / trip_high."""
    raise NotImplementedError


def _check_statistical_anomaly(asset_id: str) -> list[Detection]:
    """Z-score over 24h rolling window; flag |z| > 3."""
    raise NotImplementedError


def _check_corrosion_rate(asset_id: str) -> list[Detection]:
    """Compute adjusted corrosion rate and flag low remaining-life assets."""
    raise NotImplementedError


def _check_transmitter_divergence(asset_id: str) -> list[Detection]:
    """Detect divergence between redundant sensors on the same asset."""
    raise NotImplementedError
