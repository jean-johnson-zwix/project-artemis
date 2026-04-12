"""
Standalone notification webhook diagnostic.

Usage:
    python test_teams.py                      # Teams minimal card
    python test_teams.py --full               # Teams full detection card
    python test_teams.py --discord            # Discord minimal embed
    python test_teams.py --discord --full     # Discord full detection embed

Prints the full HTTP response so you can see exactly what the webhook returns.
"""

from __future__ import annotations

import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------

MINIMAL_CARD = {
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
                        "text": "Teams webhook test — Artemis",
                        "weight": "Bolder",
                        "size": "Large",
                    },
                    {
                        "type": "TextBlock",
                        "text": "If you can read this, the webhook is working.",
                        "wrap": True,
                    },
                ],
            },
        }
    ],
}

FULL_CARD = {
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
                        "text": "🔴 CRITICAL — Corrosion Risk Detected",
                        "weight": "Bolder",
                        "size": "Large",
                        "color": "Attention",
                        "wrap": True,
                    },
                    {
                        "type": "TextBlock",
                        "text": "**Asset:** HP Separator V-101 | **Area:** AREA-HP-SEP",
                        "wrap": True,
                        "spacing": "Small",
                        "isSubtle": True,
                    },
                    {"type": "TextBlock", "text": "**What's happening:**", "weight": "Bolder", "spacing": "Medium"},
                    {"type": "TextBlock", "text": "Wall thickness at 4.7 mm is below the 5.0 mm design minimum.", "wrap": True, "spacing": "Small"},
                    {"type": "TextBlock", "text": "Estimated remaining life: **1.8 years**", "wrap": True, "spacing": "Small", "color": "Warning"},
                    {"type": "TextBlock", "text": "**Why:**", "weight": "Bolder", "spacing": "Medium"},
                    {"type": "TextBlock", "text": "Elevated temperature (135°C vs 120°C design) has accelerated the corrosion rate.", "wrap": True, "spacing": "Small"},
                    {"type": "TextBlock", "text": "**Evidence:**", "weight": "Bolder", "spacing": "Medium"},
                    {"type": "TextBlock", "text": "• Wall thickness 4.7 mm (design min 5.0 mm)", "wrap": True, "spacing": "None"},
                    {"type": "TextBlock", "text": "• Corrosion rate 0.38 mm/year", "wrap": True, "spacing": "None"},
                    {"type": "TextBlock", "text": "**Recommended actions:**", "weight": "Bolder", "spacing": "Medium"},
                    {"type": "TextBlock", "text": "• Schedule immediate re-inspection", "wrap": True, "spacing": "None"},
                    {"type": "TextBlock", "text": "• Review coating condition", "wrap": True, "spacing": "None"},
                    {
                        "type": "TextBlock",
                        "text": "Confidence: **HIGH**  |  Detected: 13 Apr 2026 00:00",
                        "isSubtle": True,
                        "spacing": "Medium",
                        "wrap": True,
                    },
                ],
                "actions": [
                    {"type": "Action.OpenUrl", "title": "View Full Analysis →", "url": "http://localhost:3000/detections/test", "style": "positive"},
                    {"type": "Action.OpenUrl", "title": "View Asset →", "url": "http://localhost:3000/assets/AREA-HP-SEP:V-101"},
                ],
            },
        }
    ],
}


# ---------------------------------------------------------------------------
# Discord payloads
# ---------------------------------------------------------------------------

DISCORD_MINIMAL = {
    "embeds": [
        {
            "title": "Artemis webhook test",
            "description": "If you can read this, the Discord webhook is working.",
            "color": 0x3498DB,
        }
    ]
}

DISCORD_FULL = {
    "embeds": [
        {
            "title": "🔴 CRITICAL — Corrosion Risk Detected",
            "url": "http://localhost:3000/detections/test",
            "color": 0xE74C3C,
            "fields": [
                {"name": "Asset", "value": "HP Separator V-101 (`AREA-HP-SEP:V-101`)", "inline": True},
                {"name": "Area",  "value": "AREA-HP-SEP", "inline": True},
                {"name": "Remaining Life", "value": "1.8 years", "inline": True},
                {"name": "What",  "value": "Wall thickness at 4.7 mm is below the 5.0 mm design minimum.", "inline": False},
                {"name": "Why",   "value": "Elevated temperature (135°C vs 120°C design) has accelerated the corrosion rate.", "inline": False},
                {"name": "Evidence", "value": "• Wall thickness 4.7 mm (design min 5.0 mm)\n• Corrosion rate 0.38 mm/year", "inline": False},
                {"name": "Recommended Actions", "value": "• Schedule immediate re-inspection\n• Review coating condition", "inline": False},
            ],
            "footer": {"text": "Confidence: HIGH  •  13 Apr 2026 00:00 UTC"},
        }
    ]
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _send(url: str, payload: dict, label: str) -> None:
    print(f"Target      : {label}")
    print(f"Webhook URL : {url[:80]}{'...' if len(url) > 80 else ''}")
    print(f"Payload JSON (first 200 chars): {json.dumps(payload)[:200]}")
    print()

    try:
        response = httpx.post(url, json=payload, timeout=15.0)
    except httpx.ConnectError as exc:
        print(f"CONNECT ERROR — could not reach the webhook endpoint:\n  {exc}")
        sys.exit(1)
    except httpx.TimeoutException:
        print("TIMEOUT — the webhook did not respond within 15 seconds.")
        sys.exit(1)

    print(f"Status      : {response.status_code} {response.reason_phrase}")
    print(f"Headers     : {dict(response.headers)}")
    print(f"Body        : {response.text[:500] or '(empty)'}")

    if response.status_code < 300:
        print("\nSUCCESS — webhook accepted the payload.\n")
    else:
        print(f"\nFAILED — webhook returned {response.status_code}.\n")
        sys.exit(1)


if __name__ == "__main__":
    discord = "--discord" in sys.argv
    full    = "--full"    in sys.argv

    if discord:
        if not DISCORD_WEBHOOK_URL:
            print("ERROR: DISCORD_WEBHOOK_URL is not set in .env")
            sys.exit(1)
        _send(DISCORD_WEBHOOK_URL, DISCORD_FULL if full else DISCORD_MINIMAL, "Discord")
    else:
        if not TEAMS_WEBHOOK_URL:
            print("ERROR: TEAMS_WEBHOOK_URL is not set in .env")
            sys.exit(1)
        _send(TEAMS_WEBHOOK_URL, FULL_CARD if full else MINIMAL_CARD, "Teams")
