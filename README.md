# F1 3D Upgrade Dashboard

> A web-based dashboard that generates and displays 3D models of Formula 1 cars with real-time upgrade tracking, powered by FIA technical regulation data and public upgrade intelligence.

## Project Overview

This project builds a system that:

1. Parses FIA technical regulations into parametric constraints
2. Generates team-specific 3D car models within those constraints
3. Tracks and visualises car upgrades ahead of each race weekend
4. Serves an interactive dashboard where users can inspect cars, compare upgrades, and understand technical changes

The system prioritises **useful accuracy over false precision** — macro-level geometry is parametrically generated from regulations, while fine-grained upgrades are represented through a hybrid of geometric changes (where data permits) and rich annotations (always).

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **3D Rendering** | React Three Fiber + drei | Interactive car viewer, annotations, camera controls |
| **Frontend** | Next.js (App Router) + TypeScript | Dashboard UI, routing, SSR |
| **Parametric Modeling** | Python + CadQuery / build123d | Generate base car geometry from regulation parameters |
| **Mesh Processing** | trimesh + NumPy | Deform base meshes, export glTF/GLB |
| **Upgrade Tracking** | Python + spaCy / transformers | NLP pipeline to classify and extract upgrade info |
| **API** | FastAPI | Serve model files, upgrade data, and regulation metadata |
| **Database** | PostgreSQL + SQLAlchemy | Store regulation constraints, team profiles, upgrade history |
| **Storage** | S3-compatible (MinIO for local dev) | Host generated .glb model files |
| **Task Queue** | Celery + Redis | Async model generation jobs |

---

## Project Structure

```
f1-3d-dashboard/
├── README.md                    # This file — the single source of truth
├── docker-compose.yml           # Local dev environment
│
├── backend/                     # Python backend
│   ├── pyproject.toml
│   ├── alembic/                 # DB migrations
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── regulation.py    # Regulation constraints
│   │   │   ├── team.py          # Team design profiles
│   │   │   └── upgrade.py       # Upgrade records
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── cars.py      # GET /cars, GET /cars/{team_id}
│   │   │   │   ├── upgrades.py  # GET /upgrades, POST /upgrades
│   │   │   │   └── models.py    # GET /models/{team_id}/latest.glb
│   │   │   └── deps.py          # Shared dependencies
│   │   ├── services/
│   │   │   ├── regulation_parser.py   # PDF → structured constraints
│   │   │   ├── model_generator.py     # Constraints → 3D mesh
│   │   │   ├── mesh_deformer.py       # Base mesh → team variant
│   │   │   ├── upgrade_tracker.py     # Scrape + classify upgrades
│   │   │   └── glb_exporter.py        # Mesh → glTF/GLB
│   │   └── tasks/
│   │       └── generate_model.py      # Celery task for async generation
│   ├── data/
│   │   ├── regulations/         # Raw FIA regulation PDFs
│   │   ├── base_models/         # Base .glb car model(s)
│   │   └── team_profiles/       # JSON team design descriptors
│   └── tests/
│
├── frontend/                    # Next.js frontend
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # Landing / team selector
│   │   │   ├── car/[teamId]/page.tsx  # Single car viewer
│   │   │   └── compare/page.tsx       # Side-by-side comparison
│   │   ├── components/
│   │   │   ├── CarViewer.tsx           # R3F canvas + model loader
│   │   │   ├── UpgradeAnnotation.tsx   # 3D-positioned HTML overlay
│   │   │   ├── UpgradeTimeline.tsx     # Race-by-race upgrade history
│   │   │   ├── RegulationOverlay.tsx   # Toggle regulation envelopes
│   │   │   └── TeamSelector.tsx        # Grid of team cards
│   │   ├── hooks/
│   │   │   ├── useCarModel.ts          # Fetch + cache .glb
│   │   │   └── useUpgrades.ts          # Fetch upgrade data
│   │   ├── lib/
│   │   │   ├── api.ts                  # Backend API client
│   │   │   └── three-utils.ts          # Shared Three.js helpers
│   │   └── types/
│   │       └── index.ts               # Shared TypeScript types
│   └── public/
│       └── textures/                  # Livery textures, env maps
│
└── scripts/
    ├── seed_regulations.py      # One-off: parse regs into DB
    ├── seed_teams.py            # One-off: populate team profiles
    └── fetch_upgrades.py        # Cron: pull latest upgrade intel
```

---

## Data Models

### Regulation Constraint

```python
class RegulationConstraint(Base):
    __tablename__ = "regulation_constraints"

    id: int                     # PK
    season: int                 # e.g. 2026
    component: str              # e.g. "front_wing", "floor", "rear_wing"
    parameter: str              # e.g. "max_width", "min_height", "max_chord"
    value: float                # Numeric value in mm or degrees
    unit: str                   # "mm", "deg", "ratio"
    article_ref: str            # FIA article reference, e.g. "Art. 3.9.2"
    notes: str | None           # Free text clarification
```

### Team Profile

```python
class TeamProfile(Base):
    __tablename__ = "team_profiles"

    id: int
    team_name: str              # e.g. "Red Bull Racing"
    team_code: str              # e.g. "RBR"
    season: int
    sidepod_concept: str        # "downwash", "undercut", "slim", "conventional"
    nose_style: str             # "narrow", "wide", "anteater"
    cooling_inlet: str          # "top", "side", "combined"
    suspension_front: str       # "pushrod", "pullrod"
    suspension_rear: str        # "pushrod", "pullrod"
    livery_config: dict         # JSON: primary/secondary colors, sponsor placements
    design_notes: str | None    # Free text on unique features
```

### Upgrade Record

```python
class UpgradeRecord(Base):
    __tablename__ = "upgrade_records"

    id: int
    team_id: int                # FK → team_profiles
    race_weekend: str           # e.g. "2026_R10_British_GP"
    component: str              # e.g. "front_wing", "sidepod", "floor"
    subcomponent: str | None    # e.g. "endplate", "turning_vane"
    description: str            # Human-readable summary
    source_url: str | None      # Where the intel came from
    source_type: str            # "official", "journalist", "photo_analysis"
    confidence: str             # "confirmed", "likely", "rumoured"
    geometric_impact: str       # "major" (new shape), "minor" (surface tweak), "none"
    annotation_position: dict   # JSON: {x, y, z} on the 3D model for overlay
    before_image_url: str | None
    after_image_url: str | None
    created_at: datetime
```

---

## Week-by-Week Development Plan

Each week targets a **small, demonstrable increment**. Every week ends with something you can see or test. Weeks are grouped into phases but designed so you can pause after any week and still have a coherent partial project.

---

### Phase 1: Foundation (Weeks 1–4)

**Goal:** A working viewer that loads a static 3D car model with orbit controls, served by a FastAPI backend with a seeded database.

---

#### Week 1 — Project Scaffolding + Static Viewer

**Objective:** Get a 3D car model rendering in the browser.

Tasks:
- Initialise the monorepo structure (backend/ + frontend/)
- Set up Next.js with TypeScript, install `@react-three/fiber` and `@react-three/drei`
- Find or download an open-source F1 car .glb model (search Sketchfab, TurboSquid free section, or Clara.io — you need one decent base model)
- Build `CarViewer.tsx`: load the .glb with `useGLTF`, add `OrbitControls`, set up lighting (HDRI environment map via drei's `Environment`)
- Result: a page at `/` that shows a rotating F1 car you can orbit around

**Deliverable:** Browser shows interactive 3D car model.

**Claude Code prompt hint:** `"Set up a Next.js app with React Three Fiber that loads a .glb model with orbit controls, environment lighting, and a dark background. Reference the frontend/ structure in README.md."`

---

#### Week 2 — Backend Scaffolding + Database

**Objective:** FastAPI backend running with PostgreSQL and the core data models.

Tasks:
- Set up `backend/` with FastAPI, SQLAlchemy 2.0 (async), Alembic
- Create `docker-compose.yml` with PostgreSQL and Redis services
- Implement the three data models above (RegulationConstraint, TeamProfile, UpgradeRecord)
- Run initial Alembic migration
- Create `seed_teams.py` — populate the 10 current F1 teams with placeholder design profiles
- Create basic health check endpoint: `GET /api/health`
- Create `GET /api/cars` returning team list with their profiles

**Deliverable:** `curl localhost:8000/api/cars` returns JSON with 10 teams.

**Claude Code prompt hint:** `"Set up the FastAPI backend with SQLAlchemy async models for RegulationConstraint, TeamProfile, and UpgradeRecord as defined in README.md. Include Alembic config and a seed script for the 10 F1 teams."`

---

#### Week 3 — Connect Frontend to Backend

**Objective:** Frontend fetches team data from the API and lets users pick a team.

Tasks:
- Build `TeamSelector.tsx` — grid of 10 team cards with name, logo placeholder, and team color
- Create `useCarModel.ts` hook that fetches from the backend
- Set up API client in `lib/api.ts` (use fetch or axios, keep it simple)
- Wire up routing: clicking a team card navigates to `/car/[teamId]`
- The car viewer page fetches team data and displays team name + the same static .glb (team-specific models come later)
- Add basic loading states and error handling

**Deliverable:** User picks a team → sees the 3D car with team name displayed.

**Claude Code prompt hint:** `"Build the TeamSelector component and car/[teamId] route. Fetch team data from the FastAPI backend. Wire up navigation. Use the component structure from README.md."`

---

#### Week 4 — Regulation Parser (v1)

**Objective:** Extract dimensional constraints from the FIA technical regulations PDF.

Tasks:
- Download the current FIA F1 Technical Regulations PDF, place in `data/regulations/`
- Build `regulation_parser.py` using PyMuPDF (fitz) for PDF text extraction
- Focus on extracting **numerical constraints only** for these components first: front wing, rear wing, floor/diffuser, overall car dimensions (length, width, height)
- Output structured JSON matching the RegulationConstraint schema
- Create `seed_regulations.py` to parse the PDF and insert constraints into the DB
- Add `GET /api/regulations?component=front_wing` endpoint
- Write tests for the parser against known values from the regulations

**Deliverable:** Database contains parsed regulation constraints. API serves them.

**Claude Code prompt hint:** `"Build regulation_parser.py that extracts dimensional constraints (widths, heights, angles) from the FIA technical regulations PDF using PyMuPDF. Target front wing, rear wing, floor, and overall dimensions. Output JSON matching RegulationConstraint in README.md."`

---

### Phase 2: Parametric Models (Weeks 5–8)

**Goal:** Generate team-differentiated 3D models from the regulation parameters and serve them to the frontend.

---

#### Week 5 — Base Parametric Skeleton

**Objective:** Generate a simplified F1 car wireframe/mesh from regulation constraints.

Tasks:
- Install CadQuery or build123d in the backend environment
- Build `model_generator.py` — start with just the **front wing**: take regulation max/min dimensions and generate a basic wing shape (rectangular base, endplates, flap elements)
- Export as STL/OBJ, then convert to GLB using trimesh
- This will look blocky and simple — that's fine. The point is the parametric pipeline works.
- Add a CLI command: `python -m app.services.model_generator --component front_wing --season 2026`
- Visual check: load the generated .glb in the frontend viewer

**Deliverable:** Programmatically generated front wing geometry viewable in browser.

**Claude Code prompt hint:** `"Implement model_generator.py that takes front wing RegulationConstraints from the DB and generates a 3D mesh using CadQuery. Export to GLB via trimesh. Start simple — a shaped wing within the regulation bounding box."`

---

#### Week 6 — Full Car Parametric Shell

**Objective:** Extend the parametric generator to produce a complete (simplified) car body.

Tasks:
- Add parametric generation for: monocoque/survival cell (basic fuselage), rear wing, sidepods (as deformable volumes), floor plate, nose cone, engine cover
- Assemble components into a single scene graph
- Each component is a separate mesh within the GLB (important for later annotation targeting)
- The car should be recognisably "F1-shaped" even if simplified
- Generate one car and load it in the viewer, confirm all components are present

**Deliverable:** Complete simplified F1 car generated from code, viewable in browser.

**Claude Code prompt hint:** `"Extend model_generator.py to generate all major car components (monocoque, nose, sidepods, floor, engine cover, both wings). Assemble into a single GLB with named mesh nodes per component."`

---

#### Week 7 — Team Differentiation via Mesh Deformation

**Objective:** Use TeamProfile data to morph the base car into 10 distinct variants.

Tasks:
- Build `mesh_deformer.py` — takes a base mesh + TeamProfile and applies deformations
- Map profile fields to geometric operations: `sidepod_concept: "downwash"` → scale/shape the sidepod mesh differently than `"undercut"`; `nose_style: "narrow"` → taper the nose cone
- Use trimesh's vertex manipulation or simple FFD (Free-Form Deformation) lattice
- Generate all 10 team variants, store in S3/MinIO
- Update `GET /api/models/{team_id}/latest.glb` to serve team-specific models
- Update frontend to load team-specific .glb files

**Deliverable:** Each team has a visually distinct car model loaded from the backend.

**Claude Code prompt hint:** `"Build mesh_deformer.py that reads TeamProfile fields (sidepod_concept, nose_style, etc.) and applies geometric deformations to the base car mesh. Generate 10 variants, one per team. Serve via the models API endpoint."`

---

#### Week 8 — Livery System

**Objective:** Apply team-specific colors and basic livery to the models.

Tasks:
- Create UV-mapped texture templates for the base car (or use vertex coloring if UV mapping is too complex at this stage)
- Build a livery generator in Python: takes `livery_config` from TeamProfile, produces a texture image
- Apply textures to the GLB files using trimesh or gltflib
- Update the export pipeline to include material/texture data in the GLB
- Frontend: ensure materials render correctly with Three.js (PBR materials, metalness, roughness)
- Add environment reflection for the metallic/glossy car look

**Deliverable:** 10 team cars with correct team colors and basic livery.

**Claude Code prompt hint:** `"Add a livery system: generate team-colored textures from livery_config in TeamProfile, apply them to the GLB meshes. Ensure PBR material properties (metalness, roughness) are set for a realistic car look in Three.js."`

---

### Phase 3: Upgrade Tracking (Weeks 9–12)

**Goal:** Build the NLP pipeline that ingests upgrade reports and surfaces them as annotations on the 3D models.

---

#### Week 9 — Upgrade Data Ingestion Pipeline

**Objective:** Scrape and structure upgrade reports from public sources.

Tasks:
- Build `upgrade_tracker.py` with functions to fetch from RSS feeds and known F1 technical sites (handle this respectfully — rate limit, cache, respect robots.txt)
- Use spaCy or a small transformer model to extract: team name, component mentioned, race weekend, description of the change
- Map extracted components to the enum used in UpgradeRecord (front_wing, sidepod, floor, etc.)
- Store results in the database with `confidence: "rumoured"` by default
- Create `fetch_upgrades.py` CLI script (will later become a cron job)
- Add `GET /api/upgrades?team_id=X&race_weekend=Y` endpoint

**Deliverable:** Database populated with structured upgrade records from real sources.

**Claude Code prompt hint:** `"Build upgrade_tracker.py: fetch F1 technical upgrade reports from RSS/web sources, use spaCy NER to extract team, component, and description. Store as UpgradeRecord in the DB. Add the upgrades API endpoint."`

---

#### Week 10 — 3D Annotation System

**Objective:** Display upgrade annotations as interactive overlays on the 3D model.

Tasks:
- Build `UpgradeAnnotation.tsx` using drei's `Html` component — a floating card positioned at a 3D coordinate on the car
- Each annotation shows: component name, short description, confidence badge, source link
- Annotations should fade/scale based on camera distance (closer = more detail)
- Build `UpgradeTimeline.tsx` — a sidebar showing upgrades chronologically per race weekend
- Clicking a timeline entry focuses the camera on the relevant component and opens its annotation
- Wire up: frontend fetches upgrades from API, renders them as positioned annotations

**Deliverable:** User can see and interact with upgrade markers on the 3D car.

**Claude Code prompt hint:** `"Build UpgradeAnnotation.tsx using drei's Html for 3D-positioned overlays. Build UpgradeTimeline.tsx as a sidebar. Clicking a timeline entry animates the camera to the component and opens the annotation. Fetch data from the upgrades API."`

---

#### Week 11 — Annotation Positioning + Component Highlighting

**Objective:** Polish the annotation UX — auto-position labels and highlight affected parts.

Tasks:
- Build a component-to-position mapping: for each component enum value, define a default 3D anchor point on the car model (can be refined per-team later)
- Add component highlighting: when an upgrade annotation is active, highlight the relevant mesh in the GLB (change emissive color or outline via drei's `Outlines`)
- Add a "show all upgrades" toggle that highlights all upgraded components at once with a color-coded system (new = green, updated = yellow, rumoured = orange)
- Handle annotation occlusion — annotations behind the car should hide or reduce opacity
- Add keyboard navigation between annotations (arrow keys)

**Deliverable:** Polished annotation experience with highlighting and smooth camera transitions.

**Claude Code prompt hint:** `"Add component highlighting when annotations are active — use emissive color changes or drei Outlines on the relevant mesh node. Build a component-to-position map for default annotation anchors. Add show-all-upgrades toggle with color coding by confidence level."`

---

#### Week 12 — Comparison View

**Objective:** Side-by-side car comparison for analyzing differences between teams or upgrade states.

Tasks:
- Build `/compare` page with two `CarViewer` instances side by side
- Sync camera controls: orbiting one car orbits the other identically (shared camera state)
- Allow comparing: Team A vs Team B, or Team A pre-upgrade vs post-upgrade
- Highlight the geometric and annotation differences between the two states
- Add a "diff overlay" mode: show only the regions that differ between two models (for geometric changes)

**Deliverable:** Working comparison view with synced cameras and diff highlighting.

**Claude Code prompt hint:** `"Build the /compare page with two synced CarViewer instances. Share camera state between them so they orbit together. Support team-vs-team and pre/post upgrade comparisons. Add a diff overlay highlighting changed regions."`

---

### Phase 4: Polish + Production (Weeks 13–16)

**Goal:** Make it production-ready, performant, and visually impressive.

---

#### Week 13 — Model Quality Pass

**Objective:** Improve the visual fidelity of generated models.

Tasks:
- Refine parametric shapes — add fillets, smooth transitions, more realistic curvatures using spline-based surfaces instead of box primitives
- Add fine details: halo, mirrors, wheels/tyres (can use static high-quality wheel meshes), DRS flap separation on rear wing
- Improve the mesh deformation system — make team differences more pronounced and accurate
- LOD (Level of Detail): generate 3 quality levels per car (high for close-up, medium for default, low for comparison view with two cars)
- Profile and optimize GLB file sizes (target < 5MB per car)

**Deliverable:** Noticeably better-looking cars with smooth surfaces and recognisable details.

---

#### Week 14 — Performance + Caching

**Objective:** Make everything fast.

Tasks:
- Add model caching: generate once, serve from CDN/S3 until an upgrade triggers regeneration
- Implement progressive loading: show low-LOD model immediately, swap to high-LOD once loaded
- Add Celery task for async model regeneration when upgrades are added
- Frontend: add Suspense boundaries, loading skeletons, preload models for adjacent teams
- Database query optimization, add appropriate indexes
- Measure and target: < 2s initial load, < 500ms team switch

**Deliverable:** Smooth, fast user experience with no loading jank.

---

#### Week 15 — Race Weekend Mode

**Objective:** The signature feature — a pre-race-weekend view showing all latest intel.

Tasks:
- Build a "Race Weekend" dashboard page: select upcoming race → see all 10 teams with upgrade summaries
- Auto-fetch latest upgrade intel 48h before each race weekend (Friday practice focus)
- "What's New" view: highlight only the teams bringing upgrades to this specific weekend
- Add notification/badge system for new upgrade intelligence
- Allow manual upgrade entry for confirmed info you spot yourself (admin interface)

**Deliverable:** A purpose-built pre-race-weekend intelligence dashboard.

---

#### Week 16 — Deployment + Documentation

**Objective:** Ship it.

Tasks:
- Dockerize the full stack (backend + frontend + DB + Redis)
- Set up CI/CD (GitHub Actions): lint, test, build, deploy
- Deploy backend to Railway/Fly.io/Render, frontend to Vercel
- Set up the upgrade fetch cron job in production
- Write user-facing documentation
- Create a demo video / walkthrough
- Final polish: responsive design, error boundaries, 404 pages, favicon, OG images

**Deliverable:** Live, deployed application with documentation.

---

## Key Technical Decisions

**Why parametric + deformation rather than pure generative AI (e.g. 3D diffusion models)?**
Current text-to-3D models (Point-E, Shap-E, etc.) cannot produce engineering-constrained geometry. They might generate something that looks vaguely like an F1 car but won't respect regulation dimensions or produce clean meshes suitable for annotation. The parametric approach is more work upfront but gives you controllable, correct, and annotatable output.

**Why annotations over full geometric reconstruction of upgrades?**
The data resolution doesn't support it. A journalist writing "Mercedes has revised the floor edge strakes" doesn't give you enough to model the new geometry. But it gives you plenty to create a useful annotation with the component highlighted, the description shown, and a photo linked. The annotation approach is both more honest and more useful.

**Why a single base model with deformations rather than 10 separate models?**
Maintainability. When regulations change (new season), you update the parametric generator once and regenerate all 10 variants. With separate hand-made models you'd need to update each one individually.

**Why FastAPI over Django/Flask?**
Async support (important for file serving and long-running model generation), automatic OpenAPI docs (useful during frontend development), and native Pydantic integration (matches the data model approach).

---

## Environment Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose
- PostgreSQL 16 (via Docker)
- Redis (via Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed_teams.py
python scripts/seed_regulations.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Full Stack (Docker)

```bash
docker-compose up -d
```

---

## Claude Code Usage Guide

This README is designed to be your primary reference when working with Claude Code. For best results:

1. **Always point Claude Code to this README** at the start of a session: `"Read README.md and understand the project structure before proceeding."`

2. **Reference specific weeks** when asking for implementation: `"Implement Week 5 tasks — build the parametric front wing generator as described in README.md."`

3. **Reference specific files** by their path in the project structure: `"Build backend/app/services/regulation_parser.py as specified in README.md Week 4."`

4. **Use the Claude Code prompt hints** included in each week — they are written to give Claude Code the right context and constraints.

5. **Iterate within weeks** — if a week's output needs refinement, ask Claude Code to improve the specific file rather than regenerating everything: `"The front wing mesh from model_generator.py is too blocky. Add filleted edges and smooth the upper surface curvature while staying within regulation constraints."`

---

## License

TBD

---

## Acknowledgments

- FIA for publishing technical regulations
- Open-source F1 3D model communities
- F1Technical.net and other technical journalism outlets
