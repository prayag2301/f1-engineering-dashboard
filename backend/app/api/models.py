"""
Models API — Phase 2, Weeks 5+8.

Serves team-specific parametric F1 car GLB files.

Endpoints:
  GET /api/v1/models/{team_id}/latest.glb
      Returns a binary GLB file.  Generates on first request, then serves
      from the on-disk cache at data/models/{team_id}_{season}.glb.

  POST /api/v1/models/{team_id}/regenerate
      Invalidates the cache and regenerates the GLB for that team.
      Useful after a regulation or livery change.

  GET /api/v1/models/
      Lists all cached models with metadata.
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

# Resolve cache dir relative to the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CACHE_DIR = _PROJECT_ROOT / "data" / "models"

router = APIRouter()


def _cache_path(team_id: str, season: int) -> Path:
    return _CACHE_DIR / f"{team_id}_{season}.glb"


def _generate(team_id: str, season: int) -> bytes:
    """Generate GLB with team deformations applied."""
    # Late imports to keep startup fast and avoid hard dependency if trimesh
    # isn't installed yet (will raise a clear ImportError rather than a silent crash).
    try:
        from app.services.model_generator import generate_car_glb
        from app.services.mesh_deformer import build_deform_params
    except ModuleNotFoundError:
        from app.app.services.model_generator import generate_car_glb
        from app.app.services.mesh_deformer import build_deform_params

    deform_params = build_deform_params(team_id)
    return generate_car_glb(team_id=team_id, season=season, deform_params=deform_params)


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/")
def list_models(season: int = Query(default=2026)) -> list[dict]:
    """Return metadata for all cached GLB models."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for p in sorted(_CACHE_DIR.glob(f"*_{season}.glb")):
        team_id = p.stem.replace(f"_{season}", "")
        stat = p.stat()
        result.append({
            "team_id": team_id,
            "season": season,
            "size_bytes": stat.st_size,
            "cached_at": stat.st_mtime,
            "url": f"/api/v1/models/{team_id}/latest.glb?season={season}",
        })
    return result


@router.get("/{team_id}/latest.glb")
def get_car_model(
    team_id: str,
    season: int = Query(default=2026),
    force: bool = Query(default=False, description="Force regeneration even if cached"),
) -> Response:
    """
    Return a GLB binary for the requested team car.

    The model is generated once and cached. Pass ?force=true to regenerate.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(team_id, season)

    if force or not path.exists():
        try:
            glb_bytes = _generate(team_id=team_id, season=season)
        except ImportError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Model generation unavailable: trimesh not installed. {e}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Model generation failed: {e}",
            )
        path.write_bytes(glb_bytes)
    else:
        glb_bytes = path.read_bytes()

    return Response(
        content=glb_bytes,
        media_type="model/gltf-binary",
        headers={
            "Content-Disposition": f'inline; filename="{team_id}_{season}.glb"',
            "Cache-Control": "public, max-age=3600",
            "X-Team-Id": team_id,
            "X-Season": str(season),
        },
    )


@router.post("/{team_id}/regenerate")
def regenerate_model(team_id: str, season: int = Query(default=2026)) -> dict:
    """Invalidate cache and regenerate the GLB for a team."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(team_id, season)

    t0 = time.perf_counter()
    try:
        glb_bytes = _generate(team_id=team_id, season=season)
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"trimesh not installed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    path.write_bytes(glb_bytes)
    elapsed = time.perf_counter() - t0

    return {
        "team_id": team_id,
        "season": season,
        "size_bytes": len(glb_bytes),
        "generated_in_ms": round(elapsed * 1000, 1),
        "url": f"/api/v1/models/{team_id}/latest.glb?season={season}",
    }
