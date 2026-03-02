# Migration Log — Monorepo Restructure

## Baseline State (pre-restructure)

**Branch:** `main` at commit `fb451b9` ("Initial project import with Sprint 2 upgrade intelligence")

### Current Structure
```
f1-engineering-dashboard/
  backend/           # FastAPI (Python 3.12)
    main.py          # Entrypoint: uvicorn backend.main:app
    config.py        # Pydantic settings
    database.py      # SQLAlchemy engine + session
    models/          # Team, Race, Component, Upgrade, PerformanceDelta
    schemas/         # Pydantic request/response schemas
    api/             # REST routes (teams, races, components, upgrades, performance, seed)
    upgrade_parser/  # Rule-based upgrade classification
    ingestion/       # Batch ingest pipeline
    rag/             # Empty placeholder
    tests/           # 33 tests (intelligence + ingestion)
  frontend/          # Next.js 14 (TypeScript)
    app/             # App Router pages (home, analyze, teams, performance)
    components/      # UpgradeCard, FocusModal, CategoryFilter, TeamFilter
    lib/api.ts       # API client
    styles/          # Dark theme CSS
  infra/
    docker/          # Dockerfile.backend, Dockerfile.frontend
    ci/              # Empty
    deploy/          # Empty
  3d_pipeline/       # Empty placeholders (blender, exporters, nerf, models)
  data/              # raw/, processed/, upgrade_logs/ (all empty)
  docker-compose.yml # postgres, backend, frontend
  pytest.ini
```

### Dependencies
- **Python:** FastAPI 0.109.0, SQLAlchemy 2.0.25, Pydantic 2.5.3, Alembic 1.13.1, psycopg2-binary, httpx, uvicorn
- **Node:** Next.js 14.2.15, React 18.2.0, TypeScript 5.3.0

### Endpoints
- `GET /health` — health check
- `GET /docs` — OpenAPI docs
- `GET /api/v1/teams/`, `POST /api/v1/teams/`
- `GET /api/v1/races/`, `POST /api/v1/races/`
- `GET /api/v1/components/`, `POST /api/v1/components/`
- `GET /api/v1/upgrades/`, `POST /api/v1/upgrades/`, `DELETE /api/v1/upgrades/{id}`
- `POST /api/v1/upgrades/intelligence/preview`
- `POST /api/v1/upgrades/ingest`
- `GET /api/v1/performance/`, `POST /api/v1/performance/`
- `POST /api/v1/seed/`

### Test Baseline
- pytest: 33 tests across `backend/tests/test_intelligence.py` and `backend/tests/test_ingestion.py`
- No frontend tests yet
