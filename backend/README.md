# backend — Detection Pipeline

FastAPI service that ingests sensor readings, runs detection, gathers context, and calls Azure OpenAI to produce structured insights. Insights are written to the DB and sent to MS Teams via Adaptive Card.

---

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

Fill in `.env`:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Postgres connection — same DB as `data-explorer` |
| `AZURE_OPENAI_API_KEY` | Yes - Layer 2+3 | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Yes - Layer 2+3 | `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | Yes - Layer 3 | e.g. `gpt-4o-mini` |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Yes - Layer 2 | e.g. `text-embedding-3-small` |
| `AZURE_OPENAI_API_VERSION` | Yes - Layer 2+3 | e.g. `2024-02-01` |
| `TEAMS_WEBHOOK_URL` | Yes - Layer 3 | Incoming Webhook URL from Teams channel |
| `FRONTEND_BASE_URL` | Layer 3 | Base URL for deep links in Teams card (default: `http://localhost:3000`) |

Layer 1 only needs `DATABASE_URL`. Layer 2 and 3 need the Azure vars. Teams alert needs `TEAMS_WEBHOOK_URL`.

---

## Running

```bash
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

---

## API

### `POST /ingest/reading`
Ingest a sensor reading. Detection runs synchronously; Layer 2+3 run as a background task.

```json
{
  "sensor_id": "V-101-TEMP",
  "asset_id": "AREA-HP-SEP:V-101",
  "timestamp": "2024-01-01T00:00:00Z",
  "value": 128.0,
  "unit": "degC",
  "quality_flag": "GOOD"
}
```
```json
{ "written": true, "detections_fired": ["<uuid>", ...] }
```

### `POST /detections`
Internal webhook endpoint. Called by Layer 1 to trigger Layer 2+3 processing.
Returns 200 immediately; processing happens in background.

### `GET /health`
```json
{ "status": "ok" }
```

---

## Detection Types (Layer 1)

| Type | Trigger | Severity | Cooldown |
|---|---|---|---|
| `SENSOR_ANOMALY` | Alarm/trip breach or \|z\| > 3σ over 24h | HIGH (alarm/z>4), CRITICAL (trip), MEDIUM (z≤4) | 1h |
| `TRANSMITTER_DIVERGENCE` | PT-101-PV vs PT-102-PV diverge > 5% | HIGH (>10%), MEDIUM (>5%) | 1h |
| `CORROSION_THRESHOLD` | Remaining wall life < 5 years on V-101 | CRITICAL (<2y), HIGH (<3y), MEDIUM (<5y) | 4h |

---

## Pipeline Flow

```
POST /ingest/reading
  └─ Layer 1: detect → write to detections table
      └─ BackgroundTask: _process_detection(DetectionRecord)
          ├─ Layer 2: gather_context()
          │     sensor trend (24h) + document search + work orders + inspection parsing
          └─ Layer 3: run_reasoning()
                Azure OpenAI (gpt-4o-mini) → Insight
                write to insights table
                POST Adaptive Card to Teams webhook
```

---

## Structure

```
backend/
├── main.py                  # FastAPI app
├── db.py                    # SQLAlchemy engine + write_detection + write_insight
├── models.py                # Pydantic models (shared contract across all layers)
├── notifications.py         # Teams Adaptive Card builder + webhook POST
├── routers/
│   ├── ingest.py            # POST /ingest/reading  (Layer 1 entry point)
│   └── detections.py        # POST /detections  (Layer 2+3 background trigger)
├── detection/               # Layer 1 — pure detection functions
│   ├── threshold.py
│   ├── statistical.py
│   ├── corrosion.py
│   └── divergence.py
└── layers/                  # Layer 2+3 orchestration
    ├── context.py           # Layer 2 — sensor trend, doc search, work orders
    └── reasoning.py         # Layer 3 — Azure OpenAI prompt + Insight parsing
```

---

## Testing

### Layer 1

```bash
python test_detections.py
```

Runs 8 tests covering threshold breach, Z-score anomaly, transmitter divergence, corrosion detection, and deduplication.

### Layer 2 + 3

```bash
python test_pipeline.py
```

| Test | Type | Azure key needed |
|---|---|---|
| Inspection value regex parsing | Unit | No |
| Prompt structure validation | Unit | No |
| Teams env var check | Config | No |
| Corrosion spike → insight in DB | E2E | Yes |
| Sensor anomaly → insight in DB | E2E | Yes |

E2E tests wait 12 seconds for the background task (Layer 2 + Azure OpenAI call) to complete before querying the DB.
