# F1 Engineering Dashboard

The most technically insightful open-source F1 platform on the internet.
Not drama. Not headlines. **Pure engineering.**

---

## Quick Start

```bash
# Clone and bootstrap everything
git clone <repo-url> && cd f1-engineering-dashboard
./scripts/bootstrap_local.sh

# Open the dashboard
open http://localhost:3000
```

| Service    | URL                          |
|------------|------------------------------|
| Web        | http://localhost:3000         |
| API        | http://localhost:8000         |
| API Docs   | http://localhost:8000/docs    |
| MinIO      | http://localhost:9001         |
| PostgreSQL | localhost:5432               |
| Redis      | localhost:6379               |

---

## Repository Structure

```
f1-engineering-dashboard/
├── apps/
│   ├── api/              FastAPI REST API (Python 3.12)
│   └── web/              Next.js 14 dashboard (TypeScript)
│
├── services/
│   ├── ingest/           Media + article ingestion (TypeScript/BullMQ)
│   ├── annotate/         LLM upgrade analysis (TypeScript/BullMQ)
│   ├── scheduler/        Pipeline orchestration (TypeScript/BullMQ)
│   ├── recon/            3D reconstruction — NeRF/Splat (Python/GPU)
│   └── meshops/          Mesh alignment + delta heatmaps (Python)
│
├── packages/
│   ├── common/           Shared types (Python + TypeScript)
│   └── clients/          Shared API client (TypeScript)
│
├── infra/
│   ├── docker/           Dockerfiles
│   ├── schemas/          Canonical JSON Schemas
│   ├── migrations/       Database migrations
│   └── nginx/            Reverse proxy config
│
├── scripts/              bootstrap_local.sh, backfill_weekend.sh
├── docs/                 Architecture, API contract, playbooks
├── data/                 Raw, processed, samples
│
├── docker-compose.yml    Full local stack
├── Makefile              Common commands
└── package.json          npm workspace root
```

---

## Commands

```bash
# Bootstrap (starts everything + seeds DB)
make bootstrap

# Run tests
make test

# Lint + typecheck
make lint
make typecheck

# Build web for production
make build

# Start worker services
make workers

# Backfill a race weekend
make backfill SEASON=2026 RACE=R05

# Validate JSON schemas
make validate-schemas

# Tear down everything
make clean
```

---

## Engineering Principles

Every upgrade in this system must have:

1. **Aero reasoning** — airflow behavior, pressure zones, vortex structures
2. **Mechanical reasoning** — structural implications, load paths, compliance
3. **Performance hypothesis** — quantified expected lap time delta
4. **Visual before narrative** — show the data, then explain it
5. **Quantify whenever possible** — no vague storytelling

---

## Documentation

- [Architecture](docs/architecture.md) — system diagram + components
- [API Contract](docs/api_contract.md) — endpoints + schema links
- [Ingestion Rules](docs/ingestion_rules.md) — licensing + evidence scoring
- [Reconstruction Playbook](docs/reconstruction_playbook.md) — 3D pipeline guidance

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL 16 |
| Web | Next.js 14, React 18, TypeScript |
| Workers | BullMQ (TS), Redis queues (Python) |
| 3D | Three.js, Nerfstudio, Gaussian Splatting |
| AI | LLM pipeline (Claude), rule-based classification |
| Storage | MinIO (S3-compatible), PostgreSQL |
| Infra | Docker Compose, Redis 7 |

---

## License

MIT
