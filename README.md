# Form & Flow — F1 car archive

An interactive archive of dated Ferrari SF-26 and Mercedes W17 exterior reconstructions, with evidence review, component history, and studio renders.

The first published Pages snapshot contains **reviewed launch references**: Ferrari, 23 January 2026; Mercedes, 22 January 2026. Both were reviewed and published on 12 September 2026. These are not claims about the latest race specification. Later articles enter an evidence inbox; a reviewer decides what can be modeled. Exact team CAD, internal geometry, sponsor artwork, and a complete season history are not supplied. Fresh local installations still create unpublished drafts that require their own review.

## Run locally

For the public GitHub Pages build and the handover from `demo/static`, see
[the deployment guide](docs/github-pages.md). `npm run build:pages` creates a
standalone static viewer; Docker remains the local collection, rendering, and
review workflow. Only published releases enter a deployable snapshot.

Install Docker Desktop, then run from the repository root:

```sh
python3 scripts/configure.py
docker compose up -d --build
```

Open **http://127.0.0.1:3000/review** and sign in with `ADMIN_TOKEN` from your local `.env`. Credentials are generated locally and never sent to the frontend bundle. Do not commit `.env`.

The initial migration queues both reference drafts. Native ARM64/AMD64 Blender builds editable scenes, GLBs, four 1080p previews, and four 3840×2160 PNGs. CPU rendering can take tens of minutes per car, depending on your Mac and sample count. Inspect progress with:

```sh
docker compose exec -T api python -m app.cli jobs
docker compose logs -f worker scheduler
```

The public archive stays empty until you complete all four reference comparisons and publish a draft. Build completion is not visual acceptance. Start with front, side, rear, and perspective photographs from the dated source galleries, and record remaining uncertainty.

Stop with `docker compose down`. Database, releases, Redis state, and scheduler state persist in named volumes. Removing volumes deletes their contents; normal shutdown does not remove them.

### Existing installation

The migrations add release tables and preserve legacy record IDs. They also normalize old enum labels to the values used by the canonical API. The original ten-team demonstration records stay private and are never automatically promoted into the car archive.

Keep the existing database password in `.env`. On the old default Compose volume, `configure.py` recognizes the previous repository's `f1pass` credential; it never changes a stored password or overwrites an existing setting. Back up your existing database before upgrading:

```sh
mkdir -p data/backups
docker compose exec -T db pg_dump -U f1user -d f1dashboard -Fc > data/backups/before-upgrade.dump
```

An unversioned legacy database is checked against the original table layout before migration 001 is stamped. Unexpected layouts stop migration with an explanation. API startup does not run migrations.

## Weekly release workflow

1. **Collect.** The scheduler creates one collection job each Monday at 10:00 Europe/Berlin. Docker must be running. After downtime it catches up once for the most recent due week. Use the source inbox or `make collect` for a manual run.
2. **Review evidence.** Automatic HTML, RSS/Atom, and FIA PDF intake stores source URL, publisher, publication/retrieval dates, text, and PDF page references. Multiple team/component claims become separate drafts. Ambiguous assignments stay unresolved; no future race is guessed. Blocked publishers appear as collection errors and support manual URL/text import.
3. **Choose representation.** A confirmed report can remain “reported; shape unavailable.” A modeled claim requires confirmed evidence, an observation date/event, and reconstruction notes. Evidence confidence never becomes a dimension.
4. **Compose a configuration.** Start from a published parent, select approved claims, and enter explicit supported component parameters. Circuit-specific configurations and returns to earlier configurations are recorded explicitly. Reversions need evidence that each changed assembly was fitted again. A release without a supported shape change keeps the complete previous geometry.
5. **Build and inspect.** Builds create new directories; published files are never regenerated in place. A gate checks GLB structure, assembly names, materials/textures, orientation, bounds, tyre contact, all artifact hashes, source/spec consistency, and PNG dimensions.
6. **Publish.** Compare all four views against reference URLs and save review notes. Only an authenticated maintainer can publish. A final artifact validation precedes publication. Rollback moves the current-release pointer and retains all history.

A failed collection or render cannot replace the current published car. Interrupted jobs recover after a five-minute heartbeat lease expires, with three automatic attempts and an explicit manual retry thereafter. Job attempts are fenced so a superseded process cannot replace files.

Configure sources in [data/references/sources.json](data/references/sources.json). The public-publisher allowlist is in [sources.py](backend/app/services/sources.py). Add an index URL and link pattern, RSS/Atom feed, or direct document entry; rebuild API/scheduler images after changing configuration. No paywall bypass or paid extraction service is used.

## Inspect and compare

The archive provides a team selector, dated timeline, camera presets, component picking, evidence passages, uncertainty notes, and 4K downloads. Comparison defaults to two releases of the same team and offers synchronized cameras, side-by-side views, before/after switching, and changed-component highlighting.

Use **Compare teams** to inspect Ferrari and Mercedes from the same viewpoint. **Show neutral surfaces** removes livery distractions; the inlet, airbox and nose shortcuts focus both cameras on matching assemblies. Each car retains its own configuration date, sources and uncertainty notes. Constructor differences are not classified as racing upgrades.

The authenticated review studio also offers **Compare other constructor**, including validated unpublished drafts. To improve an existing model of the same dated configuration, choose **Improve an existing reconstruction** in New release. This creates new component revisions and requires four-view review; it does not change the original observation date or replace published assets. A draft targeting an older modeling generator must be recreated before rebuilding. Annotation-only releases continue to reuse their parent's exact geometry and builder provenance.

A GLB failure shows only that release's still and a retry control. Switching teams clears the previous selection. No procedural car is substituted. Published assets have immutable URLs and cache headers; draft assets require authentication.

## Application layout

| Path | Responsibility |
|---|---|
| `frontend/` | Canonical Next.js / React Three Fiber archive and maintainer UI |
| `backend/app/` | Canonical FastAPI API, evidence extraction, versioning, Celery jobs |
| `backend/alembic/` | Additive PostgreSQL migrations and publication immutability guards |
| `modeling/` | Original editable Blender builder, component catalog, dated references |
| `data/references/` | Reviewed 2026 regulation registry and collection configuration |
| `infra/docker/` | Web, API, and native CPU Blender images |
| `docker-compose.yml` | PostgreSQL, Redis, migration, API, web, worker, scheduler |

The diverged `apps/` implementations and primitive GLB fallbacks have been retired. Legacy API records remain accessible to the maintainer under their existing endpoint names.

The scheduler has its own Celery queue, independent of lengthy Blender work. PostgreSQL is the job/status authority; Redis transports tasks. Each release stores component revision IDs, frozen evidence, mesh hashes, a build specification, the exact builder/catalog/regulation files, and its editable `.blend`.

## API

Public endpoints:

- `GET /api/v1/cars/catalog`
- `GET /api/v1/cars/{team}/versions?season=2026`
- `GET /api/v1/cars/{team}/versions/{version_id}`
- `GET|HEAD /api/v1/releases/{version_id}/{filename}`
- `GET|HEAD /api/v1/models/{team}/latest.glb` — redirects to the current published asset

Maintainer endpoints under `/api/v1/review` provide session login, dashboard, source import, candidate review, version creation, build, visual review, publication, rollback, collection, and retry. Browser sessions are signed, HttpOnly, SameSite=Strict, and time limited. Scripts may use `Authorization: Bearer <ADMIN_TOKEN>`.

`POST /api/v1/models/{team}/regenerate` requires authentication and returns HTTP 202 with a draft build job. It never overwrites a published model.

## Development and validation

```sh
python3.12 -m venv backend/.venv
backend/.venv/bin/pip install -e './backend[dev]'
npm --prefix frontend ci
make test
npm --prefix frontend run build

# Real geometry checks, including an isolated front-wing change:
docker compose run --rm --no-deps worker python -m app.geometry_check

# Browser tests against the running app:
E2E_BASE_URL=http://127.0.0.1:3000 npm --prefix frontend run test:e2e
```

Browser tests use explicitly synthetic public manifests and local test assets. They do not publish real drafts. Set `PLAYWRIGHT_CHROME_PATH` to your Chrome executable or install Chromium with `cd frontend && npx playwright install chromium`.

When running browser checks alongside CPU rendering on a Mac, use `E2E_NATIVE_GPU=1 npm --prefix frontend run test:e2e` to use installed Chrome with Metal graphics. The default headless mode uses software WebGL.

To repeat the native Mac GPU orbit benchmark against a completed draft:

```sh
node scripts/benchmark_viewer.cjs
```

It requires local Chrome and the review token in `.env`, previews a draft only in that browser, and writes a screenshot and measured frame count under `data/releases/benchmark/`. Set `E2E_BASE_URL` for another local port, `TEAM=ferrari` for the other car, or `PLAYWRIGHT_CHROME_PATH` for a different Chrome installation. It never publishes the draft.

The [architecture notes](docs/architecture.md) explain evidence, version history, and job ownership. Detailed results and the remaining visual acceptance are recorded in [docs/validation.md](docs/validation.md).

For host development, expose PostgreSQL/Redis in a private Compose override and configure host `DATABASE_URL` / `REDIS_URL`. Run `npm run dev:backend` and `npm run dev:frontend`. Production Compose exposes only the web port on localhost.

Optional Compose settings: `WEB_PORT`, `RENDER_SAMPLES` (128), `BUILD_TIMEOUT_SECONDS` (7200), and `COOKIE_SECURE` (false for localhost HTTP). CPU Blender rendering and browser graphics are separate. [Docker Desktop GPU support](https://docs.docker.com/desktop/features/gpu/) documents the Windows/WSL2 GPU path; the native Debian Blender package supports [ARM64](https://packages.debian.org/trixie/arm64/blender).

## Accuracy and asset provenance

The reviewed [2026 reference set](data/references/regulations-2026.json) records FIA Section C issue 20, dated 5 August 2026, with exact article and page references for a small set of fundamental dimensions. It is a partial reference registry, not an FIA compliance certification. Regulations constrain a reconstruction; photographs establish a team's visible shape.

The [modeling notes](modeling/README.md) document coordinates, assembly ownership, editable parameters, and remaining visual uncertainty. All generated geometry, carbon textures, and studio lights are original. External photographs are linked for reference and are not bundled into release assets. The project does not redistribute team CAD or paid assets.

Full-grid coverage, video export, automated geometric inference from prose, and public hosting remain outside this release.
