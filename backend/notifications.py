"""
MS Teams Incoming Webhook integration.

TODO: Build an Adaptive Card JSON payload from an Insight + Detection,
      then POST it to TEAMS_WEBHOOK_URL.

Card format (see tasks.md for full spec):
  - Title: "<severity emoji> <SEVERITY> — <detection_type human label>"
  - Asset line, what/why sections, evidence bullets, recommended actions
  - Two action buttons:
      "View Full Analysis" → {FRONTEND_BASE_URL}/detections/{detection_id}
      "View Asset"        → {FRONTEND_BASE_URL}/assets/{asset_id}
  - Accent colour: CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=blue
"""

from models import Detection, Insight  # noqa: F401


def send_teams_alert(detection: Detection, insight: Insight) -> None:
    """
    Build and POST an Adaptive Card to the Teams Incoming Webhook.

    Raises on non-2xx response.
    """
    raise NotImplementedError
