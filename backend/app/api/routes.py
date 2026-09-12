from fastapi import APIRouter, Depends
from app.auth import require_admin
from app.api.releases import public, admin, auth
from app.api import (
    teams,
    races,
    components,
    upgrades,
    performance,
    events,
    evidence,
    assets,
    seed,
    regulations,
)

router = APIRouter()
router.include_router(public, tags=["Car releases"])
router.include_router(auth, prefix="/review", tags=["Review session"])
router.include_router(admin, prefix="/review", tags=["Review"])
# Retained legacy data/tools are maintainer-only: old demonstration records must
# never be mistaken for evidence in a public, dated car release.
for name, module in (
    ("teams", teams),
    ("races", races),
    ("components", components),
    ("upgrades", upgrades),
    ("performance", performance),
    ("events", events),
    ("evidence", evidence),
    ("assets", assets),
    ("seed", seed),
    ("regulations", regulations),
):
    router.include_router(
        module.router,
        prefix="/" + name,
        tags=["Legacy " + name],
        dependencies=[Depends(require_admin)],
    )
