# Hackazona — Industrial AI Platform

An industrial asset monitoring and AI platform for offshore oil & gas operations. Built with Next.js, Prisma, PostgreSQL (pgvector), and the Vercel AI SDK.

---

## Features

- **Dashboard** — KPI cards, asset status grid, live anomaly feed, active work orders
- **Asset Browser** — Hierarchical tree of 96 assets with drill-down to sensor data
- **Asset Detail** — Recharts trend charts with alarm/trip threshold bands, health score, linked failures & work orders
- **Anomalies** — Threshold breach detection feed (ALARM / TRIP levels)
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
- An [OpenAI API key](https://platform.openai.com/api-keys) (only needed for the Knowledge Chat RAG feature)

---

## Local Dev Setup

### 1. Clone the repo

```bash
git clone https://github.com/jean-johnson-zwix/aznn_hackazona_2026.git
cd aznn_hackazona_2026
```

### 2. Install dependencies

```bash
npm install
```

### 3. Configure environment variables

Copy the example env file and fill in your values:

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

> **Note:** The Docker Compose file maps Postgres to port **5433** (to avoid conflicts with any local Postgres on 5432). If port 5433 is free on your machine and you'd prefer 5432, change the `ports` mapping in `docker-compose.yml` and update `DATABASE_URL` accordingly.

### 4. Start the database

```bash
docker compose up -d
```

Wait ~10 seconds for the container to be healthy, then verify:

```bash
docker ps | grep hackazona_db
```

### 5. Run database migrations

```bash
npx prisma migrate deploy
```

### 6. Pull data files (Git LFS)

The CSV and document files are stored in Git LFS. After cloning, pull them down:

```bash
git lfs pull
```

This downloads the `data/` directory (~230 MB total). You need Git LFS installed — get it from [git-lfs.github.com](https://git-lfs.github.com) or via Homebrew:

```bash
brew install git-lfs
git lfs install
```

### 7. Seed the database

This loads all CSVs from the `data/` directory — 96 assets, 175 sensors, 83 work orders, 11 documents, 6 failure events, and **3.07 million timeseries rows**. The timeseries phase streams in batches of 5,000 and takes roughly 1–3 minutes.

```bash
npx prisma db seed
```

### 7. Start the dev server

```bash
npm run dev -- --webpack
```

Open [http://localhost:3000](http://localhost:3000) — you'll be redirected to the dashboard.

---

## Enabling RAG Chat (optional)

The Knowledge Chat page requires OpenAI embeddings. Once you have `OPENAI_API_KEY` set in `.env`:

1. Start the dev server
2. Make a one-off POST request to generate and store embeddings for all 11 documents:

```bash
curl -X POST http://localhost:3000/api/embed
```

This calls `text-embedding-3-small`, stores `vector(1536)` values in the `documents` table, and creates an IVFFlat index. It only needs to run once. After that, the `/knowledge` chat page will perform semantic search over the documents.

---

## Project Structure

```
hackazona/
├── docker-compose.yml
├── .env.example
├── prisma/
│   ├── schema.prisma        # 6 models + pgvector
│   └── seed.ts              # CSV ingestion (all phases)
├── data/                    # Source CSVs (assets, sensors, timeseries, etc.)
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

assets ← failure_events (6)  ← work_orders (83)
assets ← documents (11)         embedding: vector(1536) for pgvector RAG
```

---

## Resetting the Database

To wipe everything and re-seed from scratch:

```bash
docker compose down -v       # destroys the postgres volume
docker compose up -d
npx prisma migrate deploy
npx prisma db seed
```
