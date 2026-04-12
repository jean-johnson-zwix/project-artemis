"""
Layer 3 — Reasoning + Explanation

Takes a DetectionRecord + DetectionContext, calls Azure OpenAI (gpt-4o-mini),
and parses the structured response into an Insight via Pydantic.

After producing the Insight:
  1. Write it to the insights table via db.write_insight()
  2. Call notifications.send_teams_alert(detection, insight)
"""

from __future__ import annotations

import json
import logging
import os
from uuid import UUID

from openai import AzureOpenAI
from sqlalchemy.orm import Session

from db import write_insight
from models import Confidence, DetectionContext, DetectionRecord, Insight
from notifications import send_discord_alert, send_teams_alert

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an industrial asset integrity advisor for an offshore oil platform.
Analyze the detection and supporting context below and respond with a single
JSON object that exactly matches this schema — no extra keys, no markdown:

{
  "what": "<one sentence describing what is happening>",
  "why": "<one sentence explaining the root cause>",
  "evidence": ["<fact from context>", ...],
  "confidence": "LOW" | "MEDIUM" | "HIGH",
  "remaining_life_years": <float or null>,
  "recommended_actions": ["<action>", ...]
}

Rules:
- Base all claims strictly on the provided context. Do not invent data.
- remaining_life_years: include only for CORROSION_THRESHOLD detections, otherwise null.
- confidence HIGH = multiple corroborating data points; MEDIUM = one strong signal; LOW = limited context.
- Keep each field concise. what/why max 2 sentences. Evidence and actions as short imperative phrases.
- evidence: 2–5 items. recommended_actions: 2–5 items ordered by urgency."""


def run_reasoning(
    detection: DetectionRecord,
    context: DetectionContext,
    db: Session,
) -> Insight:
    """
    Call Azure OpenAI and return a structured Insight.
    Writes the insight to DB and fires the Teams notification before returning.
    """
    prompt = _build_prompt(detection, context)
    raw_json = _call_azure_openai(prompt)
    insight = _parse_insight(raw_json, detection.detection_id)

    write_insight(db, insight, context.relevant_docs)
    logger.info("Insight written for detection %s", detection.detection_id)

    for send_fn in (send_teams_alert, send_discord_alert):
        try:
            send_fn(detection, insight)
        except Exception as exc:
            logger.error("%s failed for detection %s: %s", send_fn.__name__, detection.detection_id, exc)

    return insight


# ---------------------------------------------------------------------------
# Sub-tasks
# ---------------------------------------------------------------------------


def _build_prompt(detection: DetectionRecord, context: DetectionContext) -> str:
    """Assemble the user message content for the LLM call."""
    lines: list[str] = []

    # --- Detection header ---
    lines.append("DETECTION")
    lines.append(f"  Type:     {detection.detection_type}")
    lines.append(f"  Severity: {detection.severity}")
    lines.append(f"  Asset:    {detection.asset_name} ({detection.asset_tag}) — Area: {detection.area}")
    lines.append(f"  Detected: {detection.detected_at}")
    lines.append("")

    # --- Sensor trend summary ---
    trend = context.sensor_trend
    if trend:
        values = [r.value for r in trend]
        unit = trend[0].unit
        lines.append("SENSOR TREND (last 24h)")
        lines.append(
            f"  Readings: {len(values)}  |  "
            f"Min: {min(values):.2f}  Max: {max(values):.2f}  "
            f"Avg: {sum(values)/len(values):.2f}  Unit: {unit}"
        )
        # For corrosion: show current temp vs design temp from detection_data
        if detection.detection_type == "CORROSION_THRESHOLD":
            dd = detection.detection_data
            lines.append(
                f"  Current temp: {dd.get('current_temp_celsius')}°C  "
                f"vs design: {dd.get('design_temp_celsius')}°C"
            )
            lines.append(
                f"  Adjusted corrosion rate: {dd.get('adjusted_rate_mm_per_year')} mm/year  "
                f"(base: {dd.get('base_corrosion_rate_mm_per_year')})"
            )
            lines.append(f"  Estimated remaining life: {dd.get('remaining_life_years')} years")
    else:
        lines.append("SENSOR TREND (last 24h)")
        lines.append("  No recent readings available.")
    lines.append("")

    # --- Parsed inspection values (corrosion only) ---
    piv = context.parsed_inspection_values
    if piv and any([piv.wall_thickness_mm, piv.coating_failure_pct,
                    piv.corrosion_rate_mm_per_year, piv.remaining_allowance_mm]):
        lines.append("INSPECTION VALUES")
        if piv.wall_thickness_mm is not None:
            lines.append(f"  Wall thickness:          {piv.wall_thickness_mm} mm")
        if piv.coating_failure_pct is not None:
            lines.append(f"  Coating failure:         {piv.coating_failure_pct}%")
        if piv.corrosion_rate_mm_per_year is not None:
            lines.append(f"  Corrosion rate:          {piv.corrosion_rate_mm_per_year} mm/year")
        if piv.remaining_allowance_mm is not None:
            lines.append(f"  Remaining allowance:     {piv.remaining_allowance_mm} mm")
        lines.append("")

    # --- Last inspection ---
    lines.append("LAST INSPECTION")
    if context.last_inspection_date:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        insp = context.last_inspection_date
        if insp.tzinfo is None:
            from datetime import timezone as tz
            insp = insp.replace(tzinfo=tz.utc)
        days_since = (now - insp).days
        lines.append(f"  {insp.strftime('%Y-%m-%d')} ({days_since} days ago)")
    else:
        lines.append("  No inspection on record.")
    lines.append("")

    # --- Last work order ---
    lines.append("LAST WORK ORDER")
    wo = context.last_work_order
    if wo:
        lines.append(
            f"  {wo.get('work_order_id')} | {wo.get('work_order_type')} | "
            f"{wo.get('status')} | Raised: {wo.get('raised_date')}"
        )
        if wo.get("work_description"):
            lines.append(f"  Description: {wo['work_description']}")
        if wo.get("findings"):
            lines.append(f"  Findings: {wo['findings']}")
    else:
        lines.append("  No work orders on record.")
    lines.append("")

    # --- Relevant documents ---
    if context.relevant_docs:
        lines.append("RELEVANT DOCUMENTS")
        for i, doc in enumerate(context.relevant_docs, 1):
            lines.append(f"  [{i}] {doc.title} ({doc.doc_type})")
            lines.append(f"      {doc.snippet}")
            lines.append("")

    return "\n".join(lines)


def _call_azure_openai(prompt: str) -> str:
    """POST to Azure OpenAI chat completion endpoint, return raw JSON string."""
    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )

    response = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=800,
    )

    return response.choices[0].message.content


def _parse_insight(raw_json: str, detection_id: str) -> Insight:
    """Parse and validate the LLM response into an Insight model."""
    data = json.loads(raw_json)
    data["detection_id"] = detection_id

    # Coerce confidence string to enum value
    raw_confidence = str(data.get("confidence", "MEDIUM")).upper()
    if raw_confidence not in ("LOW", "MEDIUM", "HIGH"):
        raw_confidence = "MEDIUM"
    data["confidence"] = Confidence(raw_confidence)

    return Insight.model_validate(data)
