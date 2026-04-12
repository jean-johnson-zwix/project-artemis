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

DISCORD_COLORS = {
    "CRITICAL": 0xE74C3C,
    "HIGH":     0xE67E22,
    "MEDIUM":   0xF1C40F,
    "LOW":      0x3498DB,
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


def send_discord_alert(detection: DetectionRecord, insight: Insight) -> None:
    """
    Build and POST a Discord embed to a Discord Incoming Webhook.
    Raises on non-2xx response.
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL not set — skipping Discord notification")
        return

    frontend_base = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
    detection_url = f"{frontend_base}/detections/{detection.detection_id}"

    colour = DISCORD_COLORS.get(detection.severity, 0x99AAB5)
    emoji = SEVERITY_EMOJI.get(detection.severity, "")
    type_label = DETECTION_TYPE_LABELS.get(detection.detection_type, detection.detection_type)

    detected_str = (
        detection.detected_at.strftime("%d %b %Y %H:%M UTC")
        if hasattr(detection.detected_at, "strftime")
        else str(detection.detected_at)
    )

    fields = [
        {"name": "Asset", "value": f"{detection.asset_name} (`{detection.asset_tag}`)", "inline": True},
        {"name": "Area",  "value": detection.area or "—", "inline": True},
        {"name": "What",  "value": insight.what,  "inline": False},
        {"name": "Why",   "value": insight.why,   "inline": False},
        {"name": "Evidence", "value": "\n".join(f"• {e}" for e in insight.evidence) or "—", "inline": False},
        {"name": "Recommended Actions", "value": "\n".join(f"• {a}" for a in insight.recommended_actions) or "—", "inline": False},
    ]

    if insight.remaining_life_years is not None:
        fields.insert(2, {
            "name": "Remaining Life",
            "value": f"{insight.remaining_life_years:.1f} years",
            "inline": True,
        })

    embed = {
        "title": f"{emoji} {detection.severity} — {type_label}",
        "url": detection_url,
        "color": colour,
        "fields": fields,
        "footer": {"text": f"Confidence: {insight.confidence.value}  •  {detected_str}"},
    }

    response = httpx.post(webhook_url, json={"embeds": [embed]}, timeout=10.0)
    if response.status_code >= 300:
        raise RuntimeError(
            f"Discord webhook returned {response.status_code}: {response.text[:200]}"
        )
    logger.info("Discord alert sent for detection %s", detection.detection_id)


def send_teams_resolved(resolved: dict) -> None:
    """Post an Adaptive Card to Teams when an alert is marked resolved."""
    webhook_url = os.getenv("TEAMS_WEBHOOK_URL")
    if not webhook_url:
        return

    type_label = DETECTION_TYPE_LABELS.get(resolved["detection_type"], resolved["detection_type"])

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
                        {
                            "type": "TextBlock",
                            "text": f"✅ Alert Resolved — {type_label}",
                            "weight": "Bolder",
                            "size": "Large",
                            "color": "Good",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"**Asset:** {resolved['asset_name']} | **Area:** {resolved['area']}",
                            "wrap": True,
                            "spacing": "Small",
                            "isSubtle": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"Resolved by **{resolved['resolved_by']}**",
                            "wrap": True,
                            "spacing": "Medium",
                        },
                        {
                            "type": "TextBlock",
                            "text": f"Original severity: {resolved['severity']}",
                            "wrap": True,
                            "spacing": "Small",
                            "isSubtle": True,
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
    logger.info("Teams resolved notification sent for detection %s", resolved["detection_id"])


def send_discord_resolved(resolved: dict) -> None:
    """Post a Discord embed when an alert is marked resolved."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return

    type_label = DETECTION_TYPE_LABELS.get(resolved["detection_type"], resolved["detection_type"])

    embed = {
        "title": f"✅ Alert Resolved — {type_label}",
        "color": 0x57F287,
        "fields": [
            {"name": "Asset",     "value": f"{resolved['asset_name']} (`{resolved['asset_tag']}`)", "inline": True},
            {"name": "Area",      "value": resolved["area"] or "—",  "inline": True},
            {"name": "Severity",  "value": resolved["severity"],      "inline": True},
            {"name": "Resolved by", "value": resolved["resolved_by"], "inline": False},
        ],
    }

    response = httpx.post(webhook_url, json={"embeds": [embed]}, timeout=10.0)
    if response.status_code >= 300:
        raise RuntimeError(
            f"Discord webhook returned {response.status_code}: {response.text[:200]}"
        )
    logger.info("Discord resolved notification sent for detection %s", resolved["detection_id"])
