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
