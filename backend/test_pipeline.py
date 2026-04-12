"""
Integration tests for Layer 2 (context gathering) and Layer 3 (reasoning + Teams alert).
Run with: python test_pipeline.py
Server must be running: uvicorn main:app --reload --port 8000

Tests are split into two sections:
  Unit  — call Layer 2/3 functions directly, no HTTP, instant
  E2E   — POST /ingest/reading, wait for background task, verify DB
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

BASE = "http://localhost:8000"
WAIT_SECONDS = 12   # time to let the background task (L2 + L3) finish


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def db_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def clear_tables():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM insights")
    cur.execute("DELETE FROM detections")
    conn.commit()
    conn.close()
    print("--- Cleared detections + insights tables ---\n")


def fetch_insight(detection_id: str) -> dict | None:
    conn = db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT what, why, evidence, confidence, remaining_life_years, recommended_actions "
        "FROM insights WHERE detection_id = %s",
        (detection_id,),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "what": row[0],
            "why": row[1],
            "evidence": row[2],
            "confidence": row[3],
            "remaining_life_years": row[4],
            "recommended_actions": row[5],
        }
    return None


def fetch_all_insights() -> list[dict]:
    conn = db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT detection_id, what, confidence, remaining_life_years "
        "FROM insights ORDER BY created_at DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {"detection_id": r[0], "what": r[1], "confidence": r[2], "remaining_life_years": r[3]}
        for r in rows
    ]


def ingest(sensor_id, asset_id, value, unit, quality_flag="GOOD"):
    ts = datetime.now(timezone.utc).isoformat()
    r = requests.post(f"{BASE}/ingest/reading", json={
        "sensor_id": sensor_id,
        "asset_id": asset_id,
        "timestamp": ts,
        "value": value,
        "unit": unit,
        "quality_flag": quality_flag,
    })
    r.raise_for_status()
    return r.json()


def header(text: str):
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


def ok(label: str, detail: str = ""):
    suffix = f"  {detail}" if detail else ""
    print(f"  [PASS] {label}{suffix}")


def fail(label: str, detail: str = ""):
    suffix = f"  {detail}" if detail else ""
    print(f"  [FAIL] {label}{suffix}")


# ---------------------------------------------------------------------------
# Unit tests — Layer 2 functions (no HTTP, no Azure key needed)
# ---------------------------------------------------------------------------

def test_inspection_parsing():
    header("Unit — Layer 2: _parse_inspection_values")

    from layers.context import _parse_inspection_values

    # Actual text from RPT-INSPECT-001 seeded in documents table
    sample = """
    Minimum recorded: 17.2mm (location: 3m from South head, 6 o'clock position)
    Calculated corrosion rate: 0.25 mm/year (based on 4-year interval)
    Remaining corrosion allowance at min point: 1.2mm
    Phenolic epoxy coating on lower 1/3 of vessel: approximately 40% holiday rate.
    """

    result = _parse_inspection_values(sample)

    if result is None:
        fail("parse returned None — no values extracted")
        return

    checks = [
        ("wall_thickness_mm", result.wall_thickness_mm, 17.2),
        ("corrosion_rate_mm_per_year", result.corrosion_rate_mm_per_year, 0.25),
        ("remaining_allowance_mm", result.remaining_allowance_mm, 1.2),
        ("coating_failure_pct", result.coating_failure_pct, 40.0),
    ]

    for field, actual, expected in checks:
        if actual == expected:
            ok(f"{field} = {actual}")
        else:
            fail(f"{field}", f"expected {expected}, got {actual}")


def test_prompt_building():
    header("Unit — Layer 3: _build_prompt")

    from layers.reasoning import _build_prompt
    from models import (
        DetectionContext,
        DetectionRecord,
        ParsedInspectionValues,
        RelevantDoc,
        SensorReading,
    )
    from uuid import uuid4

    detection = DetectionRecord(
        detection_id=str(uuid4()),
        detected_at=datetime.now(timezone.utc),
        detection_type="CORROSION_THRESHOLD",
        severity="HIGH",
        asset_id="AREA-HP-SEP:V-101",
        asset_tag="V-101",
        asset_name="HP Production Separator",
        area="HP Separation",
        detection_data={
            "current_temp_celsius": 128.0,
            "design_temp_celsius": 120.0,
            "adjusted_rate_mm_per_year": 0.413,
            "base_corrosion_rate_mm_per_year": 0.25,
            "remaining_life_years": 2.9,
        },
    )

    now = datetime.now(timezone.utc)
    trend = [
        SensorReading(
            sensor_id="V-101-TEMP",
            asset_id="AREA-HP-SEP:V-101",
            timestamp=now - timedelta(hours=i),
            value=125.0 + i * 0.3,
            unit="degC",
            quality_flag="GOOD",
        )
        for i in range(10)
    ]

    context = DetectionContext(
        detection_id=detection.detection_id,
        sensor_trend=trend,
        relevant_docs=[
            RelevantDoc(
                doc_id="RPT-INSPECT-001",
                title="V-101 Internal Inspection AT2020",
                doc_type="INSPECTION_REPORT",
                snippet="Minimum recorded: 17.2mm. Corrosion rate: 0.25 mm/year.",
            )
        ],
        last_inspection_date=datetime(2020, 9, 28, tzinfo=timezone.utc),
        last_work_order={
            "work_order_id": "WO-1234",
            "work_order_type": "INSPECTION",
            "status": "COMPLETED",
            "raised_date": "2020-09-01",
            "work_description": "Annual turnaround inspection of V-101",
            "findings": "Corrosion noted at 6 o'clock position",
        },
        parsed_inspection_values=ParsedInspectionValues(
            wall_thickness_mm=17.2,
            coating_failure_pct=40.0,
            corrosion_rate_mm_per_year=0.25,
            remaining_allowance_mm=1.2,
        ),
    )

    prompt = _build_prompt(detection, context)

    required_sections = [
        "DETECTION",
        "SENSOR TREND",
        "INSPECTION VALUES",
        "LAST INSPECTION",
        "LAST WORK ORDER",
        "RELEVANT DOCUMENTS",
    ]

    required_values = [
        "CORROSION_THRESHOLD",
        "128.0",        # current temp
        "17.2",         # wall thickness
        "0.25",         # corrosion rate
        "40.0",         # coating
        "1.2",          # remaining allowance
        "RPT-INSPECT",  # doc reference
    ]

    all_ok = True
    for section in required_sections:
        if section in prompt:
            ok(f"Section present: {section}")
        else:
            fail(f"Section missing: {section}")
            all_ok = False

    for val in required_values:
        if val in prompt:
            ok(f"Value present: {val}")
        else:
            fail(f"Value missing in prompt: {val}")
            all_ok = False

    if all_ok:
        print(f"\n  Prompt length: {len(prompt)} chars")


# ---------------------------------------------------------------------------
# E2E tests — full pipeline via HTTP
# ---------------------------------------------------------------------------

def test_e2e_corrosion_pipeline():
    header("E2E — Corrosion spike → Layer 2 → Layer 3 → insight in DB")

    clear_tables()

    print(f"  Ingesting temperature reading above design temp (128°C)...")
    result = ingest("V-101-TEMP", "AREA-HP-SEP:V-101", 128.0, "degC")
    fired = result.get("detections_fired", [])

    if not fired:
        fail("No detection fired — check Layer 1 corrosion baseline config")
        return

    detection_id = fired[0]
    print(f"  Detection fired: {detection_id}")
    print(f"  Waiting {WAIT_SECONDS}s for Layer 2 + 3 background task...")
    time.sleep(WAIT_SECONDS)

    insight = fetch_insight(detection_id)

    if insight is None:
        fail("No insight found in DB after waiting")
        return

    ok("Insight written to DB")

    checks = [
        ("what",               insight["what"],               str, lambda v: len(v) > 10),
        ("why",                insight["why"],                str, lambda v: len(v) > 10),
        ("evidence",           insight["evidence"],           list, lambda v: len(v) >= 2),
        ("confidence",         insight["confidence"],         str, lambda v: v in ("LOW", "MEDIUM", "HIGH")),
        ("recommended_actions",insight["recommended_actions"],list, lambda v: len(v) >= 1),
        ("remaining_life_years",insight["remaining_life_years"], (float, int, type(None)), lambda v: v is None or v > 0),
    ]

    for field, value, expected_type, validator in checks:
        if isinstance(value, expected_type) and validator(value):
            display = json.dumps(value)[:80] if isinstance(value, (list, dict)) else repr(value)[:80]
            ok(f"{field}", display)
        else:
            fail(f"{field}", f"got {type(value).__name__}: {repr(value)[:80]}")


def test_e2e_sensor_anomaly_pipeline():
    header("E2E — Sensor anomaly → Layer 2 → Layer 3 → insight in DB")

    clear_tables()

    now = datetime.now(timezone.utc)
    print("  Seeding 30 normal pressure readings...")
    for i in range(30):
        ts = (now - timedelta(hours=23) + timedelta(minutes=i * 45)).isoformat()
        requests.post(f"{BASE}/ingest/reading", json={
            "sensor_id": "V-101-PRESS",
            "asset_id": "AREA-HP-SEP:V-101",
            "timestamp": ts,
            "value": 55.0 + (i % 3) - 1,
            "unit": "bar",
            "quality_flag": "GOOD",
        })

    print("  Ingesting outlier reading (z > 4)...")
    result = ingest("V-101-PRESS", "AREA-HP-SEP:V-101", 90.0, "bar")
    fired = result.get("detections_fired", [])

    if not fired:
        fail("No detection fired — outlier may not have exceeded z > 3")
        return

    detection_id = fired[0]
    print(f"  Detection fired: {detection_id}")
    print(f"  Waiting {WAIT_SECONDS}s for background task...")
    time.sleep(WAIT_SECONDS)

    insight = fetch_insight(detection_id)

    if insight is None:
        fail("No insight found in DB")
        return

    ok("Insight written to DB")
    ok("what", repr(insight["what"])[:80])
    ok("confidence", insight["confidence"])
    ok("actions count", str(len(insight["recommended_actions"])))

    if insight["remaining_life_years"] is None:
        ok("remaining_life_years is null (correct — not a corrosion detection)")
    else:
        fail("remaining_life_years should be null for SENSOR_ANOMALY", str(insight["remaining_life_years"]))


def test_e2e_teams_check():
    header("E2E — Teams webhook env var sanity check")

    webhook = os.getenv("TEAMS_WEBHOOK_URL", "")
    if webhook and webhook.startswith("http"):
        ok("TEAMS_WEBHOOK_URL is set", webhook[:60] + "...")
    else:
        fail("TEAMS_WEBHOOK_URL is not set — Teams notifications will be skipped")

    frontend = os.getenv("FRONTEND_BASE_URL", "")
    if frontend:
        ok("FRONTEND_BASE_URL is set", frontend)
    else:
        fail("FRONTEND_BASE_URL not set — deep links in Teams card will use localhost:3000")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== Layer 2 + 3 Pipeline Tests ===")

    # Unit tests — fast, no Azure key needed
    test_inspection_parsing()
    test_prompt_building()

    # Environment check
    test_e2e_teams_check()

    # E2E tests — require server + Azure key + DB
    azure_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    if not azure_key:
        print("\n  [SKIP] E2E tests skipped — AZURE_OPENAI_API_KEY not set in .env")
    else:
        test_e2e_corrosion_pipeline()
        test_e2e_sensor_anomaly_pipeline()

    print("\n=== Done ===\n")
