"""
Manual integration tests for Layer 1 detection engine.
Run with: python test_detections.py
Server must be running: uvicorn main:app --reload --port 8000
"""

import json
from datetime import datetime, timedelta, timezone

import requests

BASE = "http://localhost:8000"


def ingest(sensor_id, asset_id, timestamp, value, unit, quality_flag="GOOD"):
    r = requests.post(f"{BASE}/ingest/reading", json={
        "sensor_id": sensor_id,
        "asset_id": asset_id,
        "timestamp": timestamp,
        "value": value,
        "unit": unit,
        "quality_flag": quality_flag,
    })
    r.raise_for_status()
    return r.json()


def check(label, result, expect_type=None, expect_severity=None, expect_empty=False):
    fired = result.get("detections_fired", [])
    status = "PASS" if result.get("written") else "FAIL (not written)"

    if expect_empty:
        status = "PASS" if len(fired) == 0 else f"FAIL — expected no detections, got {fired}"
    elif expect_type:
        # fetch detection details to verify type/severity
        pass

    print(f"[{status}] {label}")
    print(f"  detections_fired: {fired}")
    return fired


def fetch_detection(detection_id):
    import psycopg2, os
    from dotenv import load_dotenv
    load_dotenv()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(
        "SELECT detection_type, severity, detection_data FROM detections WHERE detection_id = %s",
        (detection_id,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {"detection_type": row[0], "severity": row[1], "detection_data": row[2]}
    return None


def assert_detection(label, fired_ids, expect_type, expect_severity):
    """Checks that at least one fired detection matches the expected type and severity."""
    if not fired_ids:
        print(f"[FAIL] {label} — no detections fired")
        return

    matches = []
    for did in fired_ids:
        d = fetch_detection(did)
        if d and d["detection_type"] == expect_type:
            matches.append(d)

    if not matches:
        print(f"[FAIL] {label} — no detection of type {expect_type} found among {fired_ids}")
        return

    d = matches[0]
    sev_ok = d["severity"] == expect_severity
    status = "PASS" if sev_ok else "FAIL"
    print(f"[{status}] {label}")
    print(f"  type:     {d['detection_type']} (expected {expect_type}) ✓")
    print(f"  severity: {d['severity']} (expected {expect_severity}) {'✓' if sev_ok else '✗'}")
    print(f"  data:     {json.dumps(d['detection_data'], indent=4)}")


def clear_detections():
    import psycopg2, os
    from dotenv import load_dotenv
    load_dotenv()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("DELETE FROM detections")
    conn.commit()
    conn.close()
    print("--- Cleared detections table ---\n")


# ─── Tests ────────────────────────────────────────────────────────────────────

print("\n=== Layer 1 Detection Tests ===\n")
clear_detections()

# 1. Healthy — no threshold/z-score detection (corrosion may still fire at any temp given current baseline)
print("── Test 1: Healthy reading (no threshold/z-score detection) ──")
r = ingest("V-101-TEMP", "AREA-HP-SEP:V-101", "2024-06-01T12:00:00Z", 75.0, "degC")
fired = check("Healthy reading", r)
no_anomaly = all(
    fetch_detection(d)["detection_type"] != "SENSOR_ANOMALY"
    for d in fired
)
print(f"  [{'PASS' if no_anomaly else 'FAIL'}] No SENSOR_ANOMALY fired")
print()

# 2. Threshold ALARM (HIGH)
print("── Test 2: Threshold ALARM breach (HIGH) ──")
r = ingest("V-101-TEMP", "AREA-HP-SEP:V-101", "2024-06-01T13:00:00Z", 110.0, "degC")
fired = check("Threshold ALARM", r)
assert_detection("Threshold ALARM", fired, "SENSOR_ANOMALY", "HIGH")
print()

clear_detections()

# 3. Threshold TRIP (CRITICAL)
print("── Test 3: Threshold TRIP breach (CRITICAL) ──")
r = ingest("V-101-TEMP", "AREA-HP-SEP:V-101", "2024-06-01T14:00:00Z", 120.0, "degC")
fired = check("Threshold TRIP", r)
assert_detection("Threshold TRIP", fired, "SENSOR_ANOMALY", "CRITICAL")
print()

clear_detections()

# 4. Statistical Z-score — seed then outlier
print("── Test 4: Statistical Z-score anomaly ──")
now = datetime.now(timezone.utc)
print("  Seeding 30 normal readings (recent timestamps, values 54-56)...")
for i in range(0, 30):
    v = 55.0 + (i % 3) - 1  # cycles 54, 55, 56
    ts = (now - timedelta(hours=23) + timedelta(minutes=i * 45)).isoformat()
    ingest("V-101-PRESS", "AREA-HP-SEP:V-101", ts, v, "bar")
print("  Sending outlier (within threshold bounds but z > 4)...")
r = ingest("V-101-PRESS", "AREA-HP-SEP:V-101", now.isoformat(), 75.0, "bar")
fired = check("Z-score outlier", r)
assert_detection("Z-score outlier", fired, "SENSOR_ANOMALY", "HIGH")
print()

clear_detections()

# 5. Transmitter divergence — use recent timestamps so staleness check passes
print("── Test 5: Transmitter divergence ──")
t1 = datetime.now(timezone.utc).isoformat()
t2 = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()
r1 = ingest("PT-101-PV", "AREA-HP-SEP:PT-101", t1, 74.3, "bar")
check("PT-101-PV ingest", r1)
r2 = ingest("PT-102-PV", "AREA-HP-SEP:PT-102", t2, 65.0, "bar")
fired = check("PT-102-PV divergent ingest", r2)
assert_detection("Transmitter divergence", fired, "TRANSMITTER_DIVERGENCE", "HIGH")
print()

clear_detections()

# 6. Corrosion — below design temp — remaining life still < 5y from baseline, expect MEDIUM
print("── Test 6: Corrosion — below design temp (MEDIUM, temp_factor=1.0) ──")
r = ingest("V-101-TEMP", "AREA-HP-SEP:V-101", "2024-06-01T16:00:00Z", 100.0, "degC")
fired = check("Corrosion below design temp", r)
assert_detection("Corrosion below design temp", fired, "CORROSION_THRESHOLD", "MEDIUM")
print()

clear_detections()

# 7. Corrosion — above design temp — higher rate → shorter remaining life → HIGH
print("── Test 7: Corrosion — above design temp (HIGH) ──")
r = ingest("V-101-TEMP", "AREA-HP-SEP:V-101", "2024-06-01T17:00:00Z", 128.0, "degC")
fired = check("Corrosion above design temp", r)
assert_detection("Corrosion above design temp", fired, "CORROSION_THRESHOLD", "HIGH")
print()

clear_detections()

# 8. Deduplication — fire then re-fire within cooldown
print("── Test 8: Deduplication (same detection within cooldown) ──")
r1 = ingest("V-101-TEMP", "AREA-HP-SEP:V-101", "2024-06-01T18:00:00Z", 120.0, "degC")
fired1 = check("First TRIP (should fire)", r1)
r2 = ingest("V-101-TEMP", "AREA-HP-SEP:V-101", "2024-06-01T18:01:00Z", 120.0, "degC")
fired2 = check("Second TRIP within cooldown (should NOT fire)", r2, expect_empty=True)
print()

print("=== Done ===\n")
