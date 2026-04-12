# Hackazona — Industrial AI Platform

An industrial asset monitoring and AI platform for offshore oil & gas operations.

---

## Monorepo Structure

```
hackazona/
├── data/                  # Source CSVs + documents (Git LFS, ~230 MB)
├── data-explorer/         # Next.js web app — see data-explorer/README.md
└── backend/               # FastAPI detection engine — see backend/README.md
```

## Packages

| Package | Description |
|---|---|
| [`data-explorer`](./data-explorer/README.md) | Next.js dashboard with sensor charts, anomaly detection, maintenance kanban, and RAG chat |
| [`backend`](./backend/README.md) | FastAPI Layer 1 detection engine — ingests sensor readings, runs anomaly/corrosion/divergence detection |

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

See **[data-explorer/README.md](./data-explorer/README.md)** for full setup instructions.
