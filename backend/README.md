# backend — Artemis Detection Pipeline

FastAPI service that ingests sensor readings, runs multi-stage detection, gathers context, and calls Azure OpenAI to produce structured insights. Insights are written to the DB, sent to MS Teams (Adaptive Card), posted to Discord (per-alert threads), and optionally create a Salesforce Case. A companion Discord bot answers operator questions in those threads using the stored context.

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
| `AZURE_OPENAI_API_KEY` | Layer 2+ | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Layer 2+ | `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | Layer 3 | e.g. `gpt-4o-mini` |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Layer 2 | e.g. `text-embedding-3-small` |
| `AZURE_OPENAI_API_VERSION` | Layer 2+ | e.g. `2024-02-01` |
| `TEAMS_WEBHOOK_URL` | Layer 3 | Incoming Webhook URL from Teams channel |
| `DISCORD_BOT_TOKEN` | Layer 3 | Discord bot token (Developer Portal → Bot) |
| `DISCORD_CHANNEL_ID` | Layer 3 | Channel ID where alert threads are created |
| `DISCORD_WEBHOOK_URL` | Layer 3 (fallback) | Webhook URL used if bot token is absent |
| `FRONTEND_BASE_URL` | Layer 3 | Base URL for deep links (default: `http://localhost:3000`) |
| `SALESFORCE_INSTANCE_URL` | Layer 3 (optional) | e.g. `https://<instance>.my.salesforce.com` |
| `SALESFORCE_CLIENT_ID` | Layer 3 (optional) | Connected App consumer key |
| `SALESFORCE_CLIENT_SECRET` | Layer 3 (optional) | Connected App consumer secret |

Layer 1 only needs `DATABASE_URL`. Layer 2 and 3 need the Azure vars. Notifications need the Teams/Discord vars. Salesforce Case creation is optional — omit the vars to skip it.

---

## Running

### FastAPI server

```bash
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

### Discord bot (separate process)

The bot answers operator questions inside alert threads. Run alongside the FastAPI server:

```bash
source .venv/bin/activate
python bot.py
```

Requires `DISCORD_BOT_TOKEN`, `AZURE_OPENAI_*`, and `DATABASE_URL` to be set.
Enable **Message Content Intent** in the Discord Developer Portal → Bot → Privileged Gateway Intents.

### Streamlit Demo Dashboard

```bash
cd backend
streamlit run dashboard.py
```

By default it points at `http://localhost:8000` and uses `DATABASE_URL` from `.env`.
The dashboard has two tabs:

**Monitor**
- Shows only assets that support the demo simulation scenarios
- Lets you trigger a scenario from the header row (scenario + asset dropdowns, `Trigger` button)
- Derives each asset card status from the latest unresolved detection:
  - `ALERT` — HIGH or CRITICAL
  - `WATCH` — lower-severity active detection
  - `NORMAL` — no active detection
- Opens an asset detail view showing: AI summary, root cause, evidence, relevant doc citations, recommended actions, and a resolve form
- Resolve form captures `resolved_by` and `resolution_notes` and calls `POST /detections/{id}/resolve`

**Documents & Graph**
- Ingest a document through `POST /documents/ingest`
- Shows indexing status (polls `GET /documents/{doc_id}/status`)
- Displays the generated wiki summary and `page_index_tree` once ready

### Simulation Scenario Support

Not every asset supports every scenario. Current support:

| Scenario | Valid assets |
|---|---|
| Corrosion spike | `AREA-HP-SEP:V-101` (and any with a corrosion baseline) |
| Inspection overdue | Same as corrosion |
| Sensor anomaly | Asset owning sensor `V-101-PRESS` |
| Transmitter divergence | Asset owning sensor `PT-101-PV` |

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

### `POST /detections/{detection_id}/resolve`
Mark a detection as resolved. Fires resolution notifications to Teams and Discord.

```json
{ "resolved_by": "Jane", "resolution_notes": "Replaced diaphragm seal on PT-101-PV" }
```
```json
{ "detection_id": "...", "resolved_by": "Jane", "asset_id": "...", ... }
```

### `POST /documents/ingest`
Ingest a document and schedule background page index tree generation.

```json
{
  "doc_id": "RPT-INSPECT-002",
  "doc_type": "INSPECTION_REPORT",
  "title": "V-101 Inspection Report 2025",
  "content": "..."
}
```
```json
{ "doc_id": "RPT-INSPECT-002", "status": "indexing" }
```

### `GET /documents/{doc_id}/status`
Poll indexing progress.
```json
{ "doc_id": "RPT-INSPECT-002", "status": "ready" }
```

### `POST /simulate/event`
Inject a synthetic scenario to trigger the full pipeline end-to-end.

```json
{ "scenario": "corrosion_spike", "asset_id": "AREA-HP-SEP:V-101", "overrides": {} }
```

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

Deduplication only applies to **unresolved** detections — a resolved alert correctly allows a new one to fire.

---

## Asset Status Lifecycle

| Event | New status |
|---|---|
| CRITICAL or HIGH detection | `MAINTENANCE` |
| MEDIUM or LOW detection | `STANDBY` |
| Detection resolved (no other active) | `OPERATING` |

---

## Pipeline Flow

```
POST /ingest/reading
  └─ Layer 1: detect → write to detections table → update asset status
      └─ BackgroundTask: _process_detection(DetectionRecord)
          ├─ Layer 2: gather_context()
          │     ├─ Sensor trend (last 24h)
          │     ├─ Wiki index → LLM → candidate docs
          │     ├─ PageIndex tree navigation (parallel, ThreadPoolExecutor)
          │     ├─ Work orders + last inspection date
          │     ├─ Inspection report parsing (corrosion only)
          │     └─ Past resolutions (same asset + type, last 5)
          └─ Layer 3: run_reasoning()
                Azure OpenAI (gpt-4o-mini) → Insight
                write to insights table (with relevant_docs)
                POST Adaptive Card to Teams
                POST embed to Discord → create thread → save thread_id

POST /detections/{id}/resolve
  └─ Mark resolved in DB → restore asset status if no active detections remain
      ├─ send_teams_resolved() — green Adaptive Card with resolution notes
      └─ send_discord_resolved() — green embed in alert thread

Discord bot (bot.py, separate process)
  └─ on_message in Thread
      ├─ get_detection_context_for_thread(thread_id)
      └─ Azure OpenAI → grounded 2–4 sentence answer → reply
```

---

## Structure

```
backend/
├── main.py                  # FastAPI app, startup seeding
├── db.py                    # SQLAlchemy engine, write_detection, write_insight,
│                            #   resolve_detection, save_discord_thread_id,
│                            #   get_detection_context_for_thread, update_asset_status
├── models.py                # Pydantic models (shared contract across all layers)
├── notifications.py         # Teams + Discord Adaptive Card / embed builders
├── bot.py                   # Discord bot — interactive Q&A in alert threads
├── simulator.py             # Simulation scenario logic
├── dashboard.py             # Streamlit demo dashboard
├── routers/
│   ├── ingest.py            # POST /ingest/reading  (Layer 1 entry point)
│   ├── detections.py        # POST /detections, POST /detections/{id}/resolve
│   └── documents.py         # POST /documents/ingest, GET /documents/{id}/status
├── detection/               # Layer 1 — pure detection functions
│   ├── threshold.py
│   ├── statistical.py
│   ├── corrosion.py
│   └── divergence.py
└── layers/                  # Layer 2+3 orchestration
    ├── pipeline.py          # Background task orchestration + deduplication
    ├── context.py           # Layer 2 — sensor trend, doc search, work orders, past resolutions
    ├── indexing.py          # PageIndex tree builder + wiki index refresh
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

### Notifications

```bash
python test_teams.py          # Tests Teams webhook
python test_teams.py --discord  # Tests Discord (requires DISCORD_* env vars)
python test_teams.py --full   # Tests full pipeline including LLM
```
