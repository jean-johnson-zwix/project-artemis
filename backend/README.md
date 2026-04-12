# backend — Layer 1 Detection Engine

FastAPI service that ingests sensor readings, runs anomaly/corrosion/divergence detection, writes results to the `detections` table, and forwards events to the Layer 2 webhook.

---

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the env file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string (same DB as `data-explorer`) |
| `LAYER2_WEBHOOK_URL` | Layer 2 service URL — leave blank to disable |

---

## Running

```bash
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

---

## API

### `POST /ingest/reading`

Ingest a single sensor reading. Detection runs synchronously on every call.

**Request body:**
```json
{
  "sensor_id": "V-101-TEMP",
  "asset_id": "AREA-HP-SEP:V-101",
  "timestamp": "2024-01-01T00:00:00Z",
  "value": 118.2,
  "unit": "degC",
  "quality_flag": "GOOD"
}
```

**Response:**
```json
{
  "written": true,
  "detections_fired": ["<uuid>", ...]
}
```

---

## Detection Types

| Type | Trigger | Cooldown |
|---|---|---|
| `SENSOR_ANOMALY` | Threshold breach or Z-score > 3σ (24h window) | 1 hour per sensor |
| `TRANSMITTER_DIVERGENCE` | PT-101-PV vs PT-102-PV diverge > 5% | 1 hour |
| `CORROSION_THRESHOLD` | Remaining wall life < 5 years (V-101) | 4 hours |

---

## Structure

```
backend/
├── main.py                  # FastAPI app
├── db.py                    # SQLAlchemy engine + session
├── models.py                # Pydantic I/O models
├── routers/
│   └── ingest.py            # POST /ingest/reading
└── detection/
    ├── threshold.py          # Threshold breach detection
    ├── statistical.py        # Z-score anomaly detection
    ├── corrosion.py          # Corrosion remaining life
    └── divergence.py         # Transmitter divergence
```
