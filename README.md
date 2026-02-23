# F1 Engineering Dashboard

The most technically insightful open-source F1 platform on the internet.  
Not drama. Not headlines. **Pure engineering.**

---

## Architecture

```
f1-engineering-dashboard/
│
├── backend/                FastAPI + PostgreSQL
│   ├── api/                REST endpoints (teams, races, upgrades, performance)
│   ├── ingestion/          Data ingestion pipelines (Sprint 2)
│   ├── upgrade_parser/     Upgrade classification system (Sprint 2)
│   ├── models/             SQLAlchemy ORM models
│   ├── rag/                RAG-based AI explanation layer (Sprint 3)
│   └── schemas/            Pydantic validation schemas
│
├── frontend/               Next.js 14 (App Router) + TypeScript
│   ├── app/                Pages — upgrades, teams, performance
│   ├── components/         Reusable UI components
│   ├── charts/             Data visualization (Sprint 4)
│   ├── three/              Three.js 3D viewer (Sprint 5)
│   └── styles/             Global CSS — dark engineering aesthetic
│
├── 3d_pipeline/            3D car visualization pipeline (Sprint 5–6)
│   ├── blender_assets/     Source .blend files
│   ├── exporters/          glTF/GLB export scripts
│   ├── nerf_experiments/   NeRF-based 3D generation R&D
│   └── processed_models/   Production-ready 3D models
│
├── data/                   Raw + processed datasets
│   ├── raw/
│   ├── processed/
│   └── upgrade_logs/
│
├── infra/                  Infrastructure
│   ├── docker/             Dockerfiles (backend, frontend)
│   ├── deploy/             Deployment configs
│   └── ci/                 CI/CD pipelines
│
└── docker-compose.yml      One-command local stack
```

---

## Quick Start

```bash
# Clone and start everything
git clone <repo-url> && cd f1-engineering-dashboard
docker compose up --build

# Seed the database with 2025 F1 data
curl -X POST http://localhost:8000/api/v1/seed/

# Open the dashboard
open http://localhost:3000
```

| Service  | URL                              |
|----------|----------------------------------|
| Frontend | http://localhost:3000             |
| Backend  | http://localhost:8000             |
| API Docs | http://localhost:8000/docs        |
| Database | postgresql://localhost:5432       |

---

## Database Schema

Five core tables powering the engineering intelligence layer:

- **teams** — Constructor identity, base, power unit
- **races** — 2025 calendar with circuit metadata
- **components** — Car zones (front wing, floor, diffuser, etc.)
- **upgrades** — Structured upgrade records with aero reasoning, mechanical reasoning, and performance hypothesis
- **performance_deltas** — Lap time evolution and upgrade efficiency scores

---

## API Endpoints

| Method | Endpoint                    | Description                        |
|--------|-----------------------------|------------------------------------|
| GET    | `/api/v1/teams/`           | List all teams                     |
| POST   | `/api/v1/teams/`           | Create team                        |
| GET    | `/api/v1/races/`           | List races (filter by season)      |
| POST   | `/api/v1/races/`           | Create race                        |
| GET    | `/api/v1/components/`      | List components (filter by zone)   |
| GET    | `/api/v1/upgrades/`        | List upgrades (filter by category, team, race) |
| GET    | `/api/v1/upgrades/{id}`    | Get upgrade detail with relations  |
| POST   | `/api/v1/upgrades/`        | Create upgrade                     |
| DELETE | `/api/v1/upgrades/{id}`    | Delete upgrade                     |
| GET    | `/api/v1/performance/`     | List performance deltas            |
| POST   | `/api/v1/performance/`     | Create performance delta           |
| POST   | `/api/v1/seed/`            | Seed database with sample data     |

---

## Engineering Principles

Every upgrade in this system must have:

1. **Aero reasoning** — airflow behavior, pressure zones, vortex structures
2. **Mechanical reasoning** — structural implications, load paths, compliance
3. **Performance hypothesis** — quantified expected lap time delta
4. **Visual before narrative** — show the data, then explain it
5. **Quantify whenever possible** — no vague storytelling

---

## Sprint Roadmap

| Sprint | Week | Focus                          | Status  |
|--------|------|--------------------------------|---------|
| 1      | 1    | Project Foundation             | Done    |
| 2      | 2    | Upgrade Intelligence System    | Next    |
| 3      | 3    | AI Engineering Explanation (RAG) |        |
| 4      | 4    | Performance Delta Modeling     |         |
| 5      | 5–6  | 3D Visualization Engine        |         |
| 6      | 5–6  | NeRF Experimental (Optional)   |         |
| 7      | 7    | Engineering Dashboard UI       |         |
| 8      | 8    | Production & Open Source Release |       |

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL 16
- **Frontend**: Next.js 14, React 18, TypeScript
- **3D**: Three.js, Blender, NeRF (experimental)
- **AI/RAG**: Vector DB + LLM pipeline (Sprint 3)
- **Infra**: Docker Compose, CI/CD

---

## License

MIT
