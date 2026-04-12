"""
MS Teams Incoming Webhook integration.

Builds an Adaptive Card JSON payload from a DetectionRecord + Insight,
then POSTs it to TEAMS_WEBHOOK_URL.
"""

from __future__ import annotations

import logging
import os

import httpx

from models import DetectionRecord, Insight

logger = logging.getLogger(__name__)

SEVERITY_COLOURS = {
    "CRITICAL": "attention",   # red
    "HIGH":     "warning",     # orange
    "MEDIUM":   "good",        # yellow/green
    "LOW":      "accent",      # blue
}

SEVERITY_EMOJI = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
    "LOW":      "🔵",
}

DETECTION_TYPE_LABELS = {
    "CORROSION_THRESHOLD":    "Corrosion Risk Detected",
    "SENSOR_ANOMALY":         "Sensor Anomaly Detected",
    "TRANSMITTER_DIVERGENCE": "Transmitter Divergence Detected",
}


def send_teams_alert(detection: DetectionRecord, insight: Insight) -> None:
    """
    Build and POST an Adaptive Card to the Teams Incoming Webhook.
    Raises on non-2xx response.
    """
    webhook_url = os.getenv("TEAMS_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("TEAMS_WEBHOOK_URL not set — skipping notification")
        return

    frontend_base = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
    detection_url = f"{frontend_base}/detections/{detection.detection_id}"
    asset_url = f"{frontend_base}/assets/{detection.asset_id}"

    colour = SEVERITY_COLOURS.get(detection.severity, "accent")
    emoji = SEVERITY_EMOJI.get(detection.severity, "")
    type_label = DETECTION_TYPE_LABELS.get(detection.detection_type, detection.detection_type)

    title = f"{emoji} {detection.severity} — {type_label}"

    # Build evidence bullets
    evidence_blocks = [
        {
            "type": "TextBlock",
            "text": f"• {e}",
            "wrap": True,
            "spacing": "None",
            "color": "Default",
        }
        for e in insight.evidence
    ]

    # Build recommended action bullets
    action_blocks = [
        {
            "type": "TextBlock",
            "text": f"• {a}",
            "wrap": True,
            "spacing": "None",
            "color": "Default",
        }
        for a in insight.recommended_actions
    ]

    # Remaining life line (corrosion only)
    remaining_life_block = []
    if insight.remaining_life_years is not None:
        remaining_life_block = [
            {
                "type": "TextBlock",
                "text": f"Estimated remaining life: **{insight.remaining_life_years:.1f} years**",
                "wrap": True,
                "spacing": "Small",
                "color": "Warning" if insight.remaining_life_years < 3 else "Default",
            }
        ]

    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        # Title bar
                        {
                            "type": "TextBlock",
                            "text": title,
                            "weight": "Bolder",
                            "size": "Large",
                            "color": colour.capitalize() if colour != "accent" else "Accent",
                            "wrap": True,
                        },
                        # Asset line
                        {
                            "type": "TextBlock",
                            "text": f"**Asset:** {detection.asset_name} | **Area:** {detection.area}",
                            "wrap": True,
                            "spacing": "Small",
                            "isSubtle": True,
                        },
                        # What
                        {
                            "type": "TextBlock",
                            "text": "**What's happening:**",
                            "weight": "Bolder",
                            "spacing": "Medium",
                        },
                        {
                            "type": "TextBlock",
                            "text": insight.what,
                            "wrap": True,
                            "spacing": "Small",
                        },
                        *remaining_life_block,
                        # Why
                        {
                            "type": "TextBlock",
                            "text": "**Why:**",
                            "weight": "Bolder",
                            "spacing": "Medium",
                        },
                        {
                            "type": "TextBlock",
                            "text": insight.why,
                            "wrap": True,
                            "spacing": "Small",
                        },
                        # Evidence
                        {
                            "type": "TextBlock",
                            "text": "**Evidence:**",
                            "weight": "Bolder",
                            "spacing": "Medium",
                        },
                        *evidence_blocks,
                        # Recommended actions
                        {
                            "type": "TextBlock",
                            "text": "**Recommended actions:**",
                            "weight": "Bolder",
                            "spacing": "Medium",
                        },
                        *action_blocks,
                        # Footer
                        {
                            "type": "TextBlock",
                            "text": (
                                f"Confidence: **{insight.confidence.value}**  |  "
                                f"Detected: {detection.detected_at.strftime('%d %b %Y %H:%M') if hasattr(detection.detected_at, 'strftime') else detection.detected_at}"
                            ),
                            "isSubtle": True,
                            "spacing": "Medium",
                            "wrap": True,
                        },
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "View Full Analysis →",
                            "url": detection_url,
                            "style": "positive",
                        },
                        {
                            "type": "Action.OpenUrl",
                            "title": "View Asset →",
                            "url": asset_url,
                        },
                    ],
                },
            }
        ],
    }

    response = httpx.post(webhook_url, json=card, timeout=10.0)
    if response.status_code >= 300:
        raise RuntimeError(
            f"Teams webhook returned {response.status_code}: {response.text[:200]}"
        )
    logger.info("Teams alert sent for detection %s", detection.detection_id)
