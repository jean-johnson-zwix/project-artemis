# Plan: Industrial AI Platform — Hackazona

## Stack
- **Next.js** (App Router, TypeScript) + **Prisma** + **Tailwind/shadcn**
- **PostgreSQL** via `pgvector/pgvector:pg16` Docker image (needed for embeddings)
- **Vercel AI SDK** (`ai`, `@ai-sdk/openai`) for streaming RAG chat
- **Recharts** for time-series visualization
- **csv-parse** for streaming seed of 3M+ rows
- **nuqs** for shareable URL-based filter state

---

## Data → Prisma Schema

6 models, clean relationships:

```
assets (96)          ← self-referential parent_id hierarchy
  ↓
sensor_metadata (175) ← asset_id FK
  ↓
timeseries (3.07M)   ← sensor_id + asset_id FKs
                        Composite indexes: (sensorId, timestamp), (assetId, timestamp)

assets ← failure_events (7)  ← work_orders (84)
assets ← documents (11)         embedding: vector(1536) for pgvector RAG
```

Key decisions:
- `Timeseries.id` is `BigInt` autoincrement (no UUID overhead at 3M rows)
- `Document.embedding` uses `Unsupported("vector(1536)")` + IVFFlat index via raw SQL
- All CSV enums mapped exactly (AssetStatus, Criticality, SensorType, QualityFlag, Severity, etc.)

---

## Prisma Schema

```prisma
generator client {
  provider        = "prisma-client-js"
  previewFeatures = ["postgresqlExtensions"]
}

datasource db {
  provider   = "postgresql"
  url        = env("DATABASE_URL")
  extensions = [pgvector(map: "vector")]
}

model Asset {
  id           String      @id @map("asset_id")
  tag          String
  name         String
  type         String
  subtype      String?
  parentId     String?     @map("parent_id")
  parent       Asset?      @relation("AssetHierarchy", fields: [parentId], references: [id])
  children     Asset[]     @relation("AssetHierarchy")
  area         String?
  location     String?
  manufacturer String?
  model        String?
  installDate  DateTime?   @map("install_date")
  status       AssetStatus
  criticality  Criticality

  sensors        SensorMetadata[]
  timeseriesRows Timeseries[]
  failureEvents  FailureEvent[]
  workOrders     WorkOrder[]
  documents      Document[]

  @@index([parentId])
  @@index([area])
  @@index([status])
  @@map("assets")
}

enum AssetStatus {
  OPERATING
  MAINTENANCE
  STANDBY
}

enum Criticality {
  HIGH
  MEDIUM
  LOW
}

model SensorMetadata {
  id         String     @id @map("sensor_id")
  assetId    String     @map("asset_id")
  asset      Asset      @relation(fields: [assetId], references: [id])
  tag        String
  name       String
  sensorType SensorType @map("sensor_type")
  unit       String
  normalMin  Float?     @map("normal_min")
  normalMax  Float?     @map("normal_max")
  alarmLow   Float?     @map("alarm_low")
  alarmHigh  Float?     @map("alarm_high")
  tripLow    Float?     @map("trip_low")
  tripHigh   Float?     @map("trip_high")
  area       String?
  location   String?

  timeseries Timeseries[]

  @@index([assetId])
  @@index([sensorType])
  @@map("sensor_metadata")
}

enum SensorType {
  PRESSURE
  TEMPERATURE
  FLOW
  LEVEL
  VIBRATION
  CURRENT
  FREQUENCY
  LOAD
  CONCENTRATION
}

model Timeseries {
  id          BigInt         @id @default(autoincrement())
  timestamp   DateTime
  sensorId    String         @map("sensor_id")
  sensor      SensorMetadata @relation(fields: [sensorId], references: [id])
  assetId     String         @map("asset_id")
  asset       Asset          @relation(fields: [assetId], references: [id])
  sensorType  SensorType     @map("sensor_type")
  value       Float
  unit        String
  qualityFlag QualityFlag    @map("quality_flag")

  @@index([sensorId, timestamp])
  @@index([assetId, timestamp])
  @@index([timestamp])
  @@map("timeseries")
}

enum QualityFlag {
  GOOD
  BAD
  INTERPOLATED
  OFFLINE
  UNCERTAIN
}

model FailureEvent {
  id               String    @id @map("failure_event_id")
  scenarioId       String?   @map("scenario_id")
  assetId          String    @map("asset_id")
  asset            Asset     @relation(fields: [assetId], references: [id])
  tag              String
  area             String
  eventTimestamp   DateTime  @map("event_timestamp")
  detectedBy       String?   @map("detected_by")
  severity         Severity
  safetyImpact     String?   @map("safety_impact")
  failureMode      String    @map("failure_mode")
  rootCause        String    @map("root_cause")
  failureMechanism String?   @map("failure_mechanism")
  immediateAction  String?   @map("immediate_action")
  correctiveAction String?   @map("corrective_action")
  productionLossBbl Float?   @map("production_loss_bbl")
  downtimeHours    Float?    @map("downtime_hours")

  workOrders WorkOrder[]

  @@index([assetId])
  @@index([eventTimestamp])
  @@index([severity])
  @@map("failure_events")
}

enum Severity {
  LOW
  MEDIUM
  HIGH
  CRITICAL
}

model WorkOrder {
  id                String          @id @map("work_order_id")
  failureEventId    String?         @map("failure_event_id")
  failureEvent      FailureEvent?   @relation(fields: [failureEventId], references: [id])
  assetId           String          @map("asset_id")
  asset             Asset           @relation(fields: [assetId], references: [id])
  tag               String
  area              String
  workOrderType     WorkOrderType   @map("work_order_type")
  priority          Priority
  status            WorkOrderStatus
  raisedDate        DateTime        @map("raised_date")
  scheduledDate     DateTime?       @map("scheduled_date")
  completedDate     DateTime?       @map("completed_date")
  reportedBy        String?         @map("reported_by")
  assignedTo        String?         @map("assigned_to")
  supervisor        String?
  workDescription   String          @map("work_description")
  findings          String?
  actionsTaken      String?         @map("actions_taken")
  partsReplaced     String?         @map("parts_replaced")
  laborHours        Float?          @map("labor_hours")
  downtimeHours     Float?          @map("downtime_hours")
  productionLossBbl Float?          @map("production_loss_bbl")
  scenarioId        String?         @map("scenario_id")

  @@index([assetId])
  @@index([status])
  @@index([raisedDate])
  @@map("work_orders")
}

enum WorkOrderType {
  CORRECTIVE
  PREVENTIVE
  EMERGENCY
  INSPECTION
  MODIFICATION
}

enum Priority {
  LOW
  MEDIUM
  HIGH
  CRITICAL
  EMERGENCY
}

enum WorkOrderStatus {
  OPEN
  IN_PROGRESS
  COMPLETED
  CANCELLED
  DEFERRED
}

model Document {
  id         String    @id @map("doc_id")
  assetId    String?   @map("asset_id")
  asset      Asset?    @relation(fields: [assetId], references: [id])
  docType    String    @map("doc_type")
  title      String
  revision   String?
  author     String?
  approvedBy String?   @map("approved_by")
  issueDate  DateTime? @map("issue_date")
  content    String
  embedding  Unsupported("vector(1536)")?

  @@index([assetId])
  @@index([docType])
  // IVFFlat index created via raw SQL after embeddings populated:
  // CREATE INDEX documents_embedding_idx ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
  @@map("documents")
}
```

---

## Docker — Persistent Postgres

```yaml
# docker-compose.yml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: hackazona_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-hackazona}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-hackazona}
      POSTGRES_DB: ${POSTGRES_DB:-hackazona}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-hackazona}"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  pgdata:
    name: hackazona_pgdata
```

```bash
# .env
DATABASE_URL="postgresql://hackazona:hackazona@localhost:5432/hackazona"
POSTGRES_USER=hackazona
POSTGRES_PASSWORD=hackazona
POSTGRES_DB=hackazona
OPENAI_API_KEY=sk-...
```

Start: `docker compose up -d && npx prisma migrate dev --name init`

---

## Seed Strategy

Register in `package.json`: `"prisma": { "seed": "tsx prisma/seed.ts" }`

1. **Phase 1** — `assets`, `sensor_metadata`, `failure_events`, `documents` via `createMany` (fast, <200 rows each)
2. **Phase 2** — `work_orders` (after failure_events for FK)
3. **Phase 3** — `timeseries` streamed with `csv-parse` in batches of 5,000 rows (~600 INSERTs, ~30–60s). `skipDuplicates: true` makes reruns safe.
4. **Phase 4** — separate `embed` script: generate `text-embedding-3-small` vectors, update via raw SQL, create IVFFlat index

---

## AI Features

| Feature | Description |
|---|---|
| **RAG Chat** | Semantic search over SOPs/manuals, streamed responses with source citations |
| **Anomaly Detection** | Threshold breach detection (alarm/trip) + Z-score statistical anomalies (24h rolling window) |
| **Maintenance Assistant** | Q&A augmented with work orders + failure history per asset |
| **Health Score** | Deterministic 0–100 score: sensor distance from normal range, recent alarms, days since maintenance |
| **NL Asset Query** | (Stretch) `generateObject` parses natural language into Prisma filters |

---

## Additional Packages

```json
{
  "recharts": "^2",        // time-series charts with threshold band overlays
  "date-fns": "^3",        // timestamp formatting
  "csv-parse": "^5",       // streaming CSV parser (handles 3M rows without OOM)
  "tsx": "^4",             // run seed.ts directly
  "@ai-sdk/openai": "^1",  // Vercel AI SDK OpenAI provider
  "ai": "^4",              // streamText, generateObject, useChat
  "nuqs": "^2",            // URL search param state (shareable filter/time-range links)
  "dotenv": "^16"          // load .env in seed script
}
```

---

## Pages

| Route | Purpose |
|---|---|
| `/dashboard` | KPIs (active assets, maintenance, open alarms, production loss), asset status grid, anomaly feed, active work orders |
| `/assets` | Hierarchical asset browser (collapsible tree by parent_id) |
| `/assets/[assetId]` | Sensor trend charts with alarm/trip bands, health score, linked failures + work orders, "Ask AI" button |
| `/anomalies` | Threshold breach feed, toggle statistical anomalies |
| `/maintenance` | Kanban work order board (OPEN → IN_PROGRESS → COMPLETED), filter by area/priority/type |
| `/failures` | Failure event timeline with severity, root cause, production impact |
| `/knowledge` | Full-page RAG chat with document source citations, suggested question chips |

---

## Project Structure

```
hackazona/
├── docker-compose.yml
├── .env / .env.example
├── prisma/
│   ├── schema.prisma
│   └── seed.ts
├── data/                     # existing CSVs
└── src/
    ├── app/
    │   ├── dashboard/page.tsx
    │   ├── assets/page.tsx
    │   ├── assets/[assetId]/page.tsx
    │   ├── anomalies/page.tsx
    │   ├── maintenance/page.tsx
    │   ├── failures/page.tsx
    │   ├── knowledge/page.tsx
    │   └── api/
    │       ├── assets/route.ts
    │       ├── sensors/[sensorId]/timeseries/route.ts
    │       ├── anomalies/route.ts
    │       ├── maintenance/route.ts
    │       ├── failures/route.ts
    │       ├── knowledge/chat/route.ts   # AI SDK streaming RAG
    │       └── embed/route.ts            # one-off embedding generation
    ├── components/
    │   ├── ui/               # shadcn generated
    │   ├── layout/           # Sidebar, TopBar
    │   ├── dashboard/        # KpiCard, AssetStatusGrid, RecentAnomaliesTable
    │   ├── assets/           # AssetTree, SensorTrendChart
    │   ├── anomalies/        # AnomalyFeed, ThresholdBadge
    │   ├── maintenance/      # WorkOrderCard
    │   └── knowledge/        # ChatWindow, SourceCitation
    ├── lib/
    │   ├── prisma.ts         # singleton PrismaClient
    │   ├── ai.ts             # AI provider setup
    │   ├── embeddings.ts     # generate + store pgvector embeddings
    │   ├── anomaly.ts        # threshold breach + Z-score detection
    │   └── utils.ts
    └── types/index.ts
```

---

## Implementation Order

1. Scaffold Next.js + shadcn (`create-next-app` + `shadcn init`)
2. Docker + Prisma schema + `prisma migrate dev`
3. Seed script (phases 1–3, skip embeddings initially) — `npx prisma db seed`
4. Layout shell + route stubs for all pages
5. Dashboard KPIs + asset status grid
6. Asset detail + Recharts sensor trend charts with threshold bands
7. Anomalies page + detection logic in `lib/anomaly.ts`
8. Maintenance + Failures pages
9. Knowledge chat (embeddings + streaming RAG route + ChatWindow)
10. Health score badges across asset cards
