# F1 Engineering Dashboard — Free Hosting Deploy Plan

**Status:** sketch / not yet executed.
**Goal:** run the *full* application (frontend + FastAPI backend + Postgres + 3D
model serving) on free tiers, deployed from this GitHub repo.

This file is gitignored on purpose — it's a personal working note.

---

## Target stack (all free)

| Layer | Service | Free tier limit | Why this one |
|---|---|---|---|
| Frontend (Next.js) | **Vercel** | unlimited static + 100 GB bandwidth/mo | Native Next.js, zero-config, GitHub auto-deploy |
| Backend (FastAPI) | **Render** Web Service | 750 hr/mo, sleeps after 15 min idle | Reads Dockerfile, env vars in UI, free Postgres add-on |
| Database | **Neon** Postgres | 0.5 GB storage, 191 compute hr/mo | Branchable Postgres, generous idle scaling, simple connection string |
| Static assets / GLB cache | served by FastAPI from local disk + Render persistent disk (1 GB free) | — | Avoids S3 setup; if it grows, move to **Cloudflare R2** (10 GB free) |
| CI | **GitHub Actions** | 2,000 min/mo private, unlimited public | Build + test on PR |

**Public-repo note:** if `prayag2301/f1-engineering-dashboard` stays public,
GitHub Actions minutes are unlimited. Nothing else changes.

---

## High-level topology

```
GitHub (this repo)
  ├── push to main
  │     ├── Vercel hook → builds frontend/ → deploys to https://f1-engineering-dashboard.vercel.app
  │     └── Render hook → builds backend/  → deploys to https://f1-api.onrender.com
  │
  └── Neon Postgres (separate service, connected via DATABASE_URL)
```

Frontend talks to backend over HTTPS only (no internal Docker network on
free tier). CORS must be opened on the FastAPI side for the Vercel domain.

---

## Step-by-step

### 1. Database — Neon (5 min)
1. Sign up at neon.tech with GitHub.
2. Create project `f1-engineering`. Region: closest to Render region you'll
   pick in step 2 (e.g. `eu-central-1` for Frankfurt).
3. Copy the pooled connection string. It looks like:
   `postgres://user:pwd@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`
4. Run alembic migrations against it from your laptop:
   ```bash
   cd backend
   DATABASE_URL="postgres://..." alembic upgrade head
   ```
5. Optional: seed reference data (`scripts/seed_*.py`) the same way.

### 2. Backend — Render (15 min)
1. Sign up at render.com with GitHub. Authorise the repo.
2. **New → Web Service → connect repo → root directory:** `backend`.
3. Settings:
   - **Runtime:** Docker (uses your existing `backend/` Dockerfile if present)
     or **Python**:
     - Build command: `pip install -e ".[dev]"`
     - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free.
   - **Region:** match Neon.
4. Environment variables:
   - `DATABASE_URL` → Neon connection string
   - `CORS_ORIGINS` → `https://f1-engineering-dashboard.vercel.app` (and
     preview wildcard, see step 4)
   - any API keys (OpenAI etc. for upgrade intelligence) — paid, not in this
     plan
5. First deploy takes ~5 min. URL will be `https://f1-api.onrender.com` (or similar).
6. Caveat: free instance **sleeps after 15 min idle**, first request after
   sleep takes 30–50 s. Acceptable for a demo, not for production.

### 3. Frontend — Vercel (5 min)
1. Sign up at vercel.com with GitHub. Import the repo.
2. **Root directory:** `frontend`.
3. **Framework preset:** Next.js (auto-detected).
4. Environment variables:
   - `NEXT_PUBLIC_API_URL` = `https://f1-api.onrender.com/api/v1`
   - `BACKEND_URL` = same (used by `next.config.js` rewrites)
5. Deploy. Production URL: `https://f1-engineering-dashboard.vercel.app`.
6. Every push to `main` redeploys automatically. PRs get preview URLs.

### 4. CORS / preview URLs
Vercel previews are at `https://f1-engineering-dashboard-<hash>-<user>.vercel.app`.
Update FastAPI CORS to allow a regex:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://f1-engineering-dashboard.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. 3D model storage
The parametric GLB endpoint generates on-demand and caches to disk. On Render
free tier the filesystem is ephemeral (wiped on deploy / sleep). Two options:

- **Accept regeneration:** first request per team after sleep is slow but
  cached for the instance's lifetime. Fine for a demo.
- **Persistent disk:** Render free tier gives 1 GB persistent disk. Mount at
  `/var/cache/f1-models`, point the cache there. Set `MODEL_CACHE_DIR=/var/cache/f1-models`.

### 6. Domain (optional, free)
- Vercel: free `*.vercel.app`. Custom domain needs DNS but is free on Vercel.
- Render: free `*.onrender.com`.

---

## Cost summary

All zero. Hard limits before paying:
- Render free hours: **750 hr/mo** (one always-on service uses 720 hr — you'll
  hit the cap, but the service sleeps when idle so real usage is much lower).
- Neon compute: 191 hr/mo of *active* time (Neon scales to zero when idle).
- Vercel bandwidth: 100 GB/mo (you'll never hit this).

If the backend sleep latency becomes annoying, **Render Starter** at $7/mo
removes it. Cheapest single upgrade.

---

## Open questions / TODO before doing this

- [ ] Confirm `backend/Dockerfile` exists and works standalone (not just inside
      the docker-compose network).
- [ ] Move any seed/setup that assumes local Postgres into a one-shot script
      runnable against Neon.
- [ ] Decide whether the LLM-backed `/analyze` endpoint ships in the free
      version or is gated behind an env flag (it costs money to run).
- [ ] Add `CORS_ORIGINS` handling to `backend/app/main.py` if not present.
- [ ] Add `.env.production.example` for the frontend with `NEXT_PUBLIC_API_URL`.

---

## Alternative path (if Render free tier feels too constrained)

- **Backend → Fly.io**: 3 × shared-cpu-1x 256 MB free VMs, no sleep, but
  requires `fly.toml` and a credit card on file.
- **Backend → Railway**: $5/mo trial credit, no sleep, simplest UX, but
  not strictly free after the credit runs out.
- **DB → Supabase**: 500 MB Postgres free, also gives you auth + storage if
  you ever need them. Same connection-string ergonomics as Neon.
