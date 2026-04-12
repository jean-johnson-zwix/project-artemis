# Layer 1 — Implementation Plan

Detection runs on every ingest. All incoming sensor data hits `POST /ingest/reading` first — detection logic runs there before writing to DB. No polling loop.

---

## File Structure

```
backend/
├── main.py                  # mounts all routers
├── db.py                    # SQLAlchemy engine + session
├── models.py                # Pydantic I/O models (shared contract)
├── routers/
│   └── ingest.py            # POST /ingest/reading
└── detection/
    ├── __init__.py
    ├── threshold.py          # threshold breach detection
    ├── statistical.py        # Z-score anomaly detection
    ├── corrosion.py          # corrosion remaining life
    └── divergence.py         # transmitter divergence
```

---

## Task 1 — DB Setup (`db.py`)

Connect to Postgres using SQLAlchemy. Read-only access to seeded tables (`sensor_metadata`, `timeseries`, `assets`, `work_orders`). Write access to new `detections` table.

The `Detection` model has been added to `data-explorer/prisma/schema.prisma`. Run the migration from that directory:

```bash
cd data-explorer
npx prisma migrate dev --name add_detections
```

`detection_data` is `Json` (JSONB in Postgres) — stores the per-type payload exactly as defined in the contract doc. No separate columns per detection type.

---

## Task 2 — Ingest Endpoint (`routers/ingest.py`)

This is the entry point. Everything flows through here.

```
POST /ingest/reading
Content-Type: application/json
```

**Request body:**
```python
class SensorReading(BaseModel):
    sensor_id: str           # e.g. "V-101-TEMP"
    asset_id: str            # e.g. "AREA-HP-SEP:V-101"
    timestamp: datetime
    value: float
    unit: str
    quality_flag: str        # GOOD | BAD | INTERPOLATED | OFFLINE | UNCERTAIN
```

**On each call:**
1. Validate and write the reading to `timeseries`
2. Load sensor metadata for this `sensor_id` (thresholds, type, normal range)
3. Load asset info (name, tag, area)
4. Run all applicable detectors (see below)
5. For any detections returned: write to `detections` table, POST to Layer 2 webhook
6. Return `200 OK` with list of any detections fired (empty list if none)

**Response:**
```python
class IngestResponse(BaseModel):
    written: bool
    detections_fired: list[str]   # list of detection_ids, empty if none
```

---

## Task 3 — Threshold Detection (`detection/threshold.py`)

Straightforward comparison. Runs on every ingest.

**Inputs:** current reading value, sensor metadata thresholds
**Data source:** `sensor_metadata` — `alarm_low`, `alarm_high`, `trip_low`, `trip_high`

**Known pairs from seed data:**
- `V-101-TEMP` — alarm: 34/103.5°C, trip: 28/117°C
- `V-101-PRESS` — alarm: 25.5/80.5 bar, trip: 21/91 bar
- `PT-101-PV` — alarm: 25.5/80.5 bar, trip: 21/91 bar
- `PT-102-PV` — alarm: 25.5/80.5 bar, trip: 21/91 bar
- (all 175 sensors have thresholds — generic logic covers all)

**Severity mapping:**
- Trip breach → `CRITICAL`
- Alarm breach → `HIGH`

**Output if triggered** (`detection_data` for `SENSOR_ANOMALY` type):
```python
{
    "sensor_id": "V-101-TEMP",
    "sensor_tag": "V-101/TEMP",
    "sensor_type": "TEMPERATURE",
    "anomaly_value": 118.2,
    "anomaly_unit": "degC",
    "anomaly_timestamp": "...",
    "rolling_mean": None,      # null for threshold — not Z-score
    "rolling_stddev": None,
    "z_score": None,
    "window_hours": None
}
```

No output if within bounds.

---

## Task 4 — Statistical Anomaly Detection (`detection/statistical.py`)

Z-score over a 24h rolling window. Runs on every ingest.

**Inputs:** current reading, last 24h of readings for this sensor
**Data source:** query `timeseries` for `sensor_id` WHERE `timestamp >= now() - interval '24 hours'`

**Logic:**
```python
mean = avg(last_24h_values)
stddev = stddev(last_24h_values)
z = (current_value - mean) / stddev
if abs(z) > 3.0:
    fire SENSOR_ANOMALY
```

Skip if fewer than 30 readings in window (not enough data). Skip if `quality_flag != GOOD`.

**Severity:** `abs(z) > 4` → `HIGH`, else → `MEDIUM`

**Output** (`detection_data`):
```python
{
    "sensor_id": "...",
    "sensor_tag": "...",
    "sensor_type": "...",
    "anomaly_value": 94.7,
    "anomaly_unit": "bar",
    "anomaly_timestamp": "...",
    "rolling_mean": 71.2,
    "rolling_stddev": 5.8,
    "z_score": 4.05,
    "window_hours": 24
}
```

---

## Task 5 — Transmitter Divergence (`detection/divergence.py`)

Compares PT-101-PV vs PT-102-PV on every ingest of either sensor.

**Trigger condition:** ingest `sensor_id` is `PT-101-PV` or `PT-102-PV`

**Logic:**
1. Get the latest reading for the *other* sensor from `timeseries`
2. If both readings are within 5 minutes of each other:
   ```python
   divergence_pct = abs(a - b) / ((a + b) / 2) * 100
   if divergence_pct > 5.0:
       fire TRANSMITTER_DIVERGENCE
   ```
3. If other sensor reading is >5 minutes stale, skip (can't compare)

**Severity:** `divergence_pct > 10` → `HIGH`, else → `MEDIUM`

**Output** (`detection_data`):
```python
{
    "sensor_a_id": "PT-101-PV",
    "sensor_a_tag": "PT-101/PV",
    "sensor_a_value": 74.3,
    "sensor_b_id": "PT-102-PV",
    "sensor_b_tag": "PT-102/PV",
    "sensor_b_value": 69.1,
    "divergence_pct": 7.5,
    "divergence_absolute": 5.2,
    "unit": "bar",
    "tolerance_pct": 5.0,
    "measurement_timestamp": "..."
}
```

---

## Task 6 — Corrosion Detection (`detection/corrosion.py`)

Runs on every ingest of a temperature sensor. Uses live temp + static values from inspection documents.

**Trigger condition:** `sensor_type == TEMPERATURE`

**Hardcoded baseline values** (from inspection report RPT-INSPECT-001 for V-101 — parsed once, stored as constants for now):
```python
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
```

**Formula:**
```python
temp_factor = 1 + 0.02 * max(0, current_temp - design_temp)  # 2% per degree over design
coating_factor = 1 + (coating_failure_pct / 100)              # 40% failure → 1.4x
adjusted_rate = base_rate * temp_factor * coating_factor
remaining_life = remaining_allowance / adjusted_rate

if remaining_life < 5.0:
    fire CORROSION_THRESHOLD
```

**Severity:** `remaining_life < 2` → `CRITICAL`, `< 3` → `HIGH`, `< 5` → `MEDIUM`

**Output** (`detection_data`):
```python
{
    "base_corrosion_rate_mm_per_year": 0.25,
    "temp_factor": 1.18,
    "coating_factor": 1.40,
    "adjusted_rate_mm_per_year": 0.413,
    "remaining_allowance_mm": 1.2,
    "remaining_life_years": 2.9,
    "design_temp_celsius": 120.0,
    "current_temp_celsius": 128.4,
    "temp_sensor_id": "TT-101-PV",
    "coating_failure_pct": 40.0,
    "wall_thickness_mm": 17.2
}
```

---

## Task 7 — Wire Up + Fire Webhook to Layer 2

In `routers/ingest.py`, after detections are collected:

```python
import httpx

LAYER2_WEBHOOK_URL = os.getenv("LAYER2_WEBHOOK_URL")  # add to .env

for detection in detections:
    # write to DB
    db.execute(insert_detection(detection))
    # call Layer 2
    httpx.post(LAYER2_WEBHOOK_URL, json=detection.model_dump())
```

Use `httpx` (async-friendly). Fire and don't await — Layer 1 returns immediately, Layer 2 processes in the background. If Layer 2 is down, log and continue — don't fail the ingest.

---

## Task 8 — Deduplication

Don't fire the same detection repeatedly on every reading. Before writing a detection, check:

```python
# Already fired this detection type for this asset in the last N hours?
existing = db.execute(
    "SELECT 1 FROM detections WHERE asset_id = :asset_id
     AND detection_type = :type
     AND detected_at > now() - interval '4 hours'"
)
if existing:
    skip  # already active
```

Cooldown periods:
- `SENSOR_ANOMALY` / `THRESHOLD` — 1 hour cooldown per sensor
- `CORROSION_THRESHOLD` — 4 hours cooldown per asset
- `TRANSMITTER_DIVERGENCE` — 1 hour cooldown
- `INSPECTION_OVERDUE` — 24 hours cooldown (handled separately, not on ingest)

---

## Notes

- `INSPECTION_OVERDUE` is **not** triggered by ingest — it's a separate background check. Run it once on startup and then on a simple schedule (e.g. daily). It doesn't need the ingest path.
- Hardcode the corrosion baseline for now — Layer 2 will later enrich this from the inspection document. Keep it as a dict constant so it's easy to replace.
- All detection functions are pure — they take values in, return a detection dict or `None`. No DB calls inside detection functions themselves (queries happen in the ingest router before calling them).
