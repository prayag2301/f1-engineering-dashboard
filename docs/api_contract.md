# API Contract

Base URL: `http://localhost:8000/api/v1`

## Endpoints

### Health
- `GET /health` — Returns `200 OK`

### Teams
- `GET /teams/` — List all teams → `TeamRead[]`
- `GET /teams/{id}` — Get team → `TeamRead`
- `POST /teams/` → `TeamRead` (201)

### Races
- `GET /races/?season=2025` — List races (filterable by season) → `RaceRead[]`
- `GET /races/{id}` — Get race → `RaceRead`
- `POST /races/` → `RaceRead` (201)

### Components
- `GET /components/?zone=Front Wing` — List components → `ComponentRead[]`
- `GET /components/{id}` — Get component → `ComponentRead`
- `POST /components/` → `ComponentRead` (201)

### Upgrades
- `GET /upgrades/?category=Aero&team_id=uuid&race_id=uuid&limit=50&offset=0` → `UpgradeRead[]`
- `GET /upgrades/{id}` → `UpgradeRead`
- `POST /upgrades/` → `UpgradeRead` (201, auto-enriches via intelligence)
- `DELETE /upgrades/{id}` → 204

### Upgrade Intelligence
- `POST /upgrades/intelligence/preview` — Classify upgrade text → `UpgradeIntelligencePreviewResponse`

### Batch Ingestion
- `POST /upgrades/ingest` — Batch import with dedup → `UpgradeBatchIngestResult`

### Performance
- `GET /performance/?team_id=uuid&race_id=uuid` → `PerformanceDeltaRead[]`
- `POST /performance/` → `PerformanceDeltaRead` (201)

### Seed
- `POST /seed/` — Idempotent DB seeding (201)

## Schema References

All response shapes conform to JSON Schemas in `infra/schemas/`:

| Schema | File |
|--------|------|
| Team | `infra/schemas/team.schema.json` |
| Race | `infra/schemas/race.schema.json` |
| Component | `infra/schemas/component.schema.json` |
| Upgrade | `infra/schemas/upgrade.schema.json` |
| PerformanceDelta | `infra/schemas/performance-delta.schema.json` |
| Evidence | `infra/schemas/evidence.schema.json` |
| Asset | `infra/schemas/asset.schema.json` |
| Callout | `infra/schemas/callout.schema.json` |
| Event | `infra/schemas/event.schema.json` |

## OpenAPI Docs

Interactive docs at: `http://localhost:8000/docs`
