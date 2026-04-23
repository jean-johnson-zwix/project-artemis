# Artemis — Industrial AI Platform

AI-powered asset monitoring and incident response platform for offshore oil & gas operations. Artemis continuously monitors sensor data, detects anomalies and corrosion threats, reasons over inspection documents and maintenance history, and delivers structured insights to operators via Teams, Discord, and a web dashboard.

---

## Monorepo Structure

```
artemis/
├── data/           # Source CSVs + documents (Git LFS, ~230 MB)
├── data-explorer/  # Next.js web app — see data-explorer/README.md
└── backend/        # FastAPI detection + reasoning engine — see backend/README.md
```

## Packages

| Package | Description |
|---|---|
| [`data-explorer`](./data-explorer/README.md) | Next.js dashboard with sensor charts, anomaly detection, maintenance kanban, AI-generated detection insights, and document citations |
| [`backend`](./backend/README.md) | FastAPI detection engine — ingests sensor readings, runs anomaly/corrosion/divergence detection, gathers context (PageIndex RAG), reasons with Azure OpenAI, notifies Teams and Discord |

---

## How It Works

```
Sensor reading
    │
    ▼
Layer 1 — Detection
    Threshold breach / Z-score anomaly / Transmitter divergence / Corrosion life
    │
    ▼ (background task)
Layer 2 — Context
    Sensor trend · PageIndex document retrieval · Work orders · Past resolutions
    │
    ▼
Layer 3 — Reasoning
    Azure OpenAI (gpt-4o-mini) → structured Insight
    │
    ├──▶ MS Teams Adaptive Card
    └──▶ Discord thread (per alert)
              │
              ▼
         Discord bot answers operator questions using stored context
```

When an alert is resolved:
- Asset status is restored to `OPERATING`
- Resolution notes are persisted
- Teams and Discord both receive a green "Resolved" notification

---

## Key Features

- **Multi-stage detection** — threshold, statistical (Z-score), transmitter divergence, and corrosion lifetime estimation
- **PageIndex RAG** — LLM-navigates a hierarchical document tree to extract the most relevant section from inspection reports and SOPs, not just the nearest embedding. Benchmarked against flat vector search (same embedding model): **100% Recall@3 vs 33%, MRR 0.889 vs 0.333, 38% less cross-document noise**
- **Structured AI insights** — what, why, evidence, confidence, remaining life, recommended actions; all grounded in real context
- **Document citations** — each insight cites the exact document sections used, with breadcrumb path shown in the UI
- **Historical resolution context** — past resolutions for the same asset and detection type are fed into the reasoning prompt
- **Teams + Discord notifications** — alert on detection, resolution notification on resolve
- **Discord Q&A bot** — operators ask questions in the alert thread; bot answers from stored detection context
- **Asset status lifecycle** — `OPERATING → MAINTENANCE/STANDBY` on detection, restored on resolution
- **Simulation scenarios** — corrosion spike, sensor anomaly, transmitter divergence, inspection overdue

---

## Benchmarks

### Layer 1 — Statistical Gating

Ran against 3M+ sensor readings across 175 sensors:

| Metric | Result |
|---|---|
| Readings handled by Layer 1 (no LLM) | **95.7%** |
| Estimated Azure OpenAI cost reduction | **~96%** |

### Layer 2 — Agentic RAG vs Naive Vector Search

6 hand-labeled queries across all detection types, same embedding model (`all-MiniLM-L6-v2`), 11-document corpus:

| Metric | Agentic RAG | Naive RAG |
|---|---|---|
| Recall@3 (correct doc in top 3) | **100%** | 33% |
| MRR (mean reciprocal rank) | **0.889** | 0.333 |
| Cross-document noise | **42%** | 80% |
| Section keyword precision@1 | **83%** | 50% |

The routing advantage compounds at production scale — the flat index has ~40× more confounding chunks while the agentic Stage 2 search space stays constant at 2 candidate documents.

Run the benchmarks locally:

```bash
cd backend
python ../benchmark_layer1.py   # Layer 1 detection rate across 3M readings
python ../benchmark_rag.py      # RAG retrieval quality comparison
```

---

## Data Files

Source data is stored in Git LFS. After cloning, pull it down:

```bash
# Install Git LFS if needed
brew install git-lfs
git lfs install

# Pull the data files
git lfs pull
```

This downloads the `data/` directory (~230 MB) containing:

```
data/
├── assets.csv              # 96 assets
├── sensor_metadata.csv     # 175 sensors
├── timeseries.csv          # 3.07M rows
├── failure_events.csv      # 6 events
├── maintenance_history.csv # 83 work orders
├── documents.csv           # 11 SOPs / manuals
└── documents/              # PDF and SVG source files
```

---

## Getting Started

### Docker (recommended)

Runs the full stack — Postgres, migrations + seed, Next.js frontend, and FastAPI backend — with a single command.

```bash
# 1. Clone and pull data (Git LFS)
git lfs install && git lfs pull

# 2. Create and fill in your env file
cp .env.example .env

# 3. Start everything (seed takes 1–3 min on first run)
make docker-up
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API / docs | http://localhost:8000/docs |
| Streamlit dashboard | http://localhost:8501 |
| PostgreSQL | localhost:5433 |

The Discord bot starts automatically. If `DISCORD_BOT_TOKEN` is not set it exits cleanly — no restart loop, no noise in the logs.

To wipe the database and start fresh:

```bash
make docker-reset   # docker compose down -v
make docker-up
```

---

### Local dev (without Docker)

Requires Node.js 20+, Python 3.12+, and the Docker Postgres container running.

```bash
# 1. Pull data
git lfs install && git lfs pull

# 2. Create .env and symlink it into each service directory
make setup          # copies .env.example → .env, then symlinks backend/.env and data-explorer/.env

# 3. Edit .env with your API keys, then start Postgres only
docker compose up postgres -d

# 4. Run migrations + seed (once)
make migrate
make seed

# 5. Start services in separate terminals
make dev-frontend   # http://localhost:3000
make dev-backend    # http://localhost:8000
```

---

### Environment variables

All variables live in a **single `.env` at the repo root** — no per-service env files needed.

| Variable | Required for |
|---|---|
| `DATABASE_URL` | All services (local dev) |
| `OPENAI_API_KEY` | Frontend Knowledge Chat |
| `AZURE_OPENAI_API_KEY` / `ENDPOINT` / `DEPLOYMENT` | Backend Layer 2 + 3 |
| `TEAMS_WEBHOOK_URL` | Teams notifications |
| `DISCORD_BOT_TOKEN` / `DISCORD_CHANNEL_ID` | Discord alerts + bot |

See [`.env.example`](./.env.example) for the full list with descriptions.

---

### Database migrations

Prisma (in `data-explorer/`) is the single migration source of truth. The backend uses the same schema with no separate migration tooling.

```bash
make migrate        # deploy pending migrations
make migrate-dev    # create a new migration (prompts for a name)
make seed           # seed the database (safe to re-run)
```

For per-service details see [data-explorer/README.md](./data-explorer/README.md) and [backend/README.md](./backend/README.md).

Integrations included: Discord, Teams and Salesforce. 
