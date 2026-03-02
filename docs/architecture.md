# Architecture

## System Overview

```
                  ┌─────────────┐
                  │   Browser    │
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │  apps/web   │  Next.js 14
                  │  :3000      │  TypeScript
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │  apps/api   │  FastAPI
                  │  :8000      │  Python 3.12
                  └──┬───┬───┬──┘
                     │   │   │
          ┌──────────┘   │   └──────────┐
          │              │              │
   ┌──────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
   │  PostgreSQL │ │  Redis   │ │   MinIO     │
   │  :5432      │ │  :6379   │ │   :9000     │
   └─────────────┘ └────┬─────┘ └─────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
  ┌─────▼─────┐  ┌──────▼──────┐  ┌────▼──────┐
  │  ingest   │  │  annotate   │  │ scheduler │
  │  (TS)     │  │  (TS/LLM)  │  │  (TS)     │
  └───────────┘  └─────────────┘  └───────────┘
        │               │
  ┌─────▼─────┐  ┌──────▼──────┐
  │   recon   │  │  meshops   │
  │  (Py/GPU) │  │  (Py)      │
  └───────────┘  └─────────────┘
```

## Components

### Apps

| Component | Language | Purpose |
|-----------|----------|---------|
| `apps/api` | Python (FastAPI) | REST API, DB models, upgrade intelligence |
| `apps/web` | TypeScript (Next.js) | Dashboard UI, 3D viewer, upgrade browser |

### Services (Workers)

| Service | Language | Queue | Purpose |
|---------|----------|-------|---------|
| `services/ingest` | TypeScript | `ingest` | Media/article ingestion, MinIO storage |
| `services/annotate` | TypeScript | `annotate` | LLM-powered upgrade analysis |
| `services/scheduler` | TypeScript | (producer) | Pipeline orchestration, cron dispatch |
| `services/recon` | Python | `recon` | GPU 3D reconstruction (NeRF/Splat) |
| `services/meshops` | Python | `meshops` | Mesh alignment, delta heatmaps |

### Packages (Shared Libraries)

| Package | Language | Purpose |
|---------|----------|---------|
| `packages/common/python` | Python | Shared enums, Pydantic types |
| `packages/common/typescript` | TypeScript | Shared enums, interfaces |
| `packages/clients` | TypeScript | API client for services |

### Infrastructure

| Component | Purpose |
|-----------|---------|
| `infra/docker/` | Dockerfiles for API and Web |
| `infra/schemas/` | Canonical JSON Schemas |
| `infra/migrations/` | Database migrations (Alembic) |
| `infra/nginx/` | Reverse proxy config |

## Data Flow

```
Race Weekend
    │
    ▼
┌─────────┐   URLs/files   ┌─────────┐   raw media   ┌─────────┐
│Scheduler│──────────────▶│ Ingest  │──────────────▶│  MinIO  │
└─────────┘               └────┬────┘               └─────────┘
                               │
                        evidence rows
                               │
                          ┌────▼────┐
                          │Annotate │  LLM extraction
                          └────┬────┘
                               │
                     hypotheses + callouts
                               │
                          ┌────▼────┐
                          │  Recon  │  GPU processing
                          └────┬────┘
                               │
                          .ply + renders
                               │
                          ┌────▼────┐
                          │MeshOps  │  alignment + delta
                          └────┬────┘
                               │
                     compare artifacts
                               │
                          ┌────▼────┐
                          │  API    │──────▶ Web UI
                          └─────────┘
```

## Database Schema

Core tables: `teams`, `races`, `components`, `upgrades`, `performance_deltas`

Future tables: `evidence`, `assets`, `callouts`, `events`, `jobs`

Canonical JSON Schemas for all objects are in `infra/schemas/`.

## Queue Architecture

All worker services communicate via Redis queues (BullMQ for TypeScript, raw Redis for Python).

Pipeline stages are dispatched by the scheduler service:
`ingest -> annotate -> recon -> meshops -> publish`
