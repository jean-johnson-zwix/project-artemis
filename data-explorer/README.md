# data-explorer

Industrial asset monitoring web app for the Artemis platform. Provides real-time dashboards, sensor trend charts, anomaly detection, maintenance tracking, AI-generated detection insights, and RAG chat over SOPs and technical manuals.

---

## Features

- **Dashboard** — KPI cards, asset status grid, live anomaly feed, active work orders
- **Asset Browser** — Hierarchical tree of 96 assets with drill-down to sensor data
- **Asset Detail** — Recharts trend charts with alarm/trip threshold bands, health score, linked failures & work orders
- **Detections** — Full list of threshold breaches and anomalies, filterable by severity, type, asset, and date
- **Detection Detail** — AI-generated insight (what, why, evidence, recommended actions, confidence, remaining life), plus document citations with breadcrumb paths showing exactly which section of each document the AI used
- **Maintenance** — Kanban work order board (OPEN → IN_PROGRESS → COMPLETED)
- **Failures** — Event timeline with severity, root cause, production impact
- **Knowledge Chat** — Streaming RAG chat over SOPs and technical manuals, with document source citations

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 15 (App Router, TypeScript) |
| UI | Tailwind CSS v4 + shadcn/ui |
| Database | PostgreSQL 17 + pgvector (via Docker) |
| ORM | Prisma |
| Charts | Recharts |
| AI / RAG | Vercel AI SDK (`ai`, `@ai-sdk/openai`) |
| CSV ingestion | `csv-parse` (streaming, 3M+ rows) |
| URL state | `nuqs` |

---

## Prerequisites

- [Node.js](https://nodejs.org/) v20+
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- Data files pulled via Git LFS — see [root README](../README.md#data-files)
- An [OpenAI API key](https://platform.openai.com/api-keys) (only needed for the Knowledge Chat RAG feature)

---

## Setup

### 1. Install dependencies

From this directory:

```bash
cd data-explorer
npm install
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL="postgresql://hackazona:hackazona@localhost:5433/hackazona"
POSTGRES_USER=hackazona
POSTGRES_PASSWORD=hackazona
POSTGRES_DB=hackazona
OPENAI_API_KEY=sk-...   # only required for /knowledge RAG chat
```

> **Note:** Docker Compose maps Postgres to port **5433** to avoid conflicts with any local Postgres on 5432. If you'd prefer 5432, change the `ports` mapping in `docker-compose.yml` and update `DATABASE_URL` accordingly.

### 3. Start the database

```bash
docker compose up -d
```

Verify it's healthy:

```bash
docker ps | grep hackazona_db
```

### 4. Run migrations

```bash
npx prisma migrate deploy
```

### 5. Seed the database

Loads all CSVs from `../data/` — 96 assets, 175 sensors, 83 work orders, 11 documents, 6 failure events, and **3.07 million timeseries rows**. Streams in batches of 5,000 and takes roughly 1–3 minutes.

```bash
npx prisma db seed
```

### 6. Start the dev server

```bash
npm run dev -- --webpack
```

Open [http://localhost:3000](http://localhost:3000) — you'll be redirected to the dashboard.

---

## Enabling RAG Chat (optional)

The Knowledge Chat page uses OpenAI embeddings for semantic search. Once `OPENAI_API_KEY` is set in `.env`, generate embeddings once:

```bash
curl -X POST http://localhost:3000/api/embed
```

This calls `text-embedding-3-small`, stores `vector(1536)` values in the `documents` table, and creates an IVFFlat index. Only needs to run once.

---

## Project Structure

```
data-explorer/
├── docker-compose.yml
├── .env.example
├── prisma/
│   ├── schema.prisma        # 6 models + pgvector
│   └── seed.ts              # CSV ingestion (all phases)
└── src/
    ├── app/
    │   ├── dashboard/
    │   ├── assets/
    │   │   └── [assetId]/
    │   ├── anomalies/
    │   ├── maintenance/
    │   ├── failures/
    │   ├── knowledge/
    │   └── api/             # REST + streaming AI routes
    ├── components/
    │   ├── layout/          # Sidebar
    │   ├── dashboard/       # KpiCard, AssetStatusGrid, RecentAnomaliesTable
    │   ├── assets/          # AssetTree, SensorTrendChart
    │   ├── anomalies/       # AnomalyFeed
    │   ├── maintenance/     # WorkOrderCard
    │   └── knowledge/       # ChatWindow, SourceCitation
    └── lib/
        ├── prisma.ts        # Singleton PrismaClient
        ├── ai.ts            # OpenAI provider setup
        ├── anomaly.ts       # Threshold breach types
        ├── health.ts        # Asset health score (0–100)
        └── utils.ts
```

---

## Database Schema

```
assets (96)              ← self-referential parent_id hierarchy
  ↓
sensor_metadata (175)    ← asset_id FK
  ↓
timeseries (3.07M)       ← sensor_id + asset_id FKs
                            Indexes: (sensorId, timestamp), (assetId, timestamp)

assets ← failure_events (6)
assets ← work_orders (83)
assets ← documents (11)      embedding: vector(1536) for pgvector RAG
                             page_index_tree: jsonb — hierarchical section tree
                             indexed_at: timestamptz

detections               ← written by backend Layer 1
  ↓                         resolved_at, resolved_by, resolution_notes, discord_thread_id
insights                 ← written by backend Layer 3; FK → detections
                            relevant_docs: jsonb — document citations with tree_path

wiki_index               ← one row per indexed document; one_line_summary for LLM pre-filter
```

---

## Resetting the Database

```bash
docker compose down -v       # destroys the postgres volume
docker compose up -d
npx prisma migrate deploy
npx prisma db seed
```
