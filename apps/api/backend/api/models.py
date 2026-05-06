"""
models.py — REST endpoints for parametric model generation and serving.

GET  /api/v1/models/{component}/{season}.glb
    Returns the .glb for the given component + season.
    Generates it on first request; cached thereafter.

POST /api/v1/models/{component}/{season}/generate
    Force-regenerates the model in the background.
    Returns immediately; poll the GET endpoint after ~1s.
"""

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

try:
    from app.database import get_db
    from app.services.model_generator import SUPPORTED_COMPONENTS, generate_model
except ModuleNotFoundError:
    from backend.database import get_db
    from backend.services.model_generator import SUPPORTED_COMPONENTS, generate_model

router = APIRouter()

_MODELS_DIR = Path(__file__).resolve().parents[2] / "generated_models"


def _glb_path(component: str, season: int) -> Path:
    return _MODELS_DIR / f"{component}_{season}.glb"


@router.get("/{component}/{season}.glb", response_class=FileResponse)
def get_model(component: str, season: int, db: Session = Depends(get_db)):
    """
    Serve the .glb for *component* at *season* spec.
    Generates it synchronously on first request; subsequent requests hit the cache.
    """
    if component not in SUPPORTED_COMPONENTS:
        raise HTTPException(
            status_code=404,
            detail=(
                f"'{component}' is not supported in Week 5. "
                f"Supported: {sorted(SUPPORTED_COMPONENTS)}"
            ),
        )

    path = _glb_path(component, season)

    if not path.exists():
        try:
            path = generate_model(component=component, season=season, db=db)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Generation failed: {exc}")

    return FileResponse(
        path=str(path),
        media_type="model/gltf-binary",
        filename=f"{component}_{season}.glb",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.post("/{component}/{season}/generate")
def regenerate_model(
    component: str,
    season: int,
    background_tasks: BackgroundTasks,
):
    """Force-regenerate the model, replacing any cached version."""
    if component not in SUPPORTED_COMPONENTS:
        raise HTTPException(
            status_code=404,
            detail=f"'{component}' is not supported.",
        )

    background_tasks.add_task(generate_model, component=component, season=season)
    return {
        "message": f"Regenerating {component} model for season {season}",
        "status": "queued",
        "result_url": f"/api/v1/models/{component}/{season}.glb",
    }
