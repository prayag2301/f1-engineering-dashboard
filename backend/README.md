# F1 Engineering Dashboard — API

FastAPI backend serving the REST API.

## Local Development

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

API docs at [http://localhost:8000/docs](http://localhost:8000/docs).

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://f1user:f1pass@db:5432/f1dashboard` |
| `DEBUG` | Enable debug mode | `true` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |

## Endpoints

- `GET /health` — Health check
- `GET /api/v1/teams/` — List teams
- `GET /api/v1/races/` — List races
- `GET /api/v1/upgrades/` — List upgrades (filterable)
- `POST /api/v1/upgrades/intelligence/preview` — AI classification
- `POST /api/v1/upgrades/ingest` — Batch ingestion
- `POST /api/v1/seed/` — Seed database

## Tests

```bash
cd apps/api
python -m pytest
```
