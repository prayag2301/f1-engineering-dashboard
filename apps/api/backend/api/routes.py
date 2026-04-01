from fastapi import APIRouter
from backend.api.teams import router as teams_router
from backend.api.races import router as races_router
from backend.api.components import router as components_router
from backend.api.upgrades import router as upgrades_router
from backend.api.performance import router as performance_router
from backend.api.events import router as events_router
from backend.api.evidence import router as evidence_router
from backend.api.assets import router as assets_router
from backend.api.seed import router as seed_router
from backend.api.regulations import router as regulations_router
from backend.api.models import router as models_router

router = APIRouter()

router.include_router(teams_router, prefix="/teams", tags=["Teams"])
router.include_router(teams_router, prefix="/cars", tags=["Cars"])
router.include_router(races_router, prefix="/races", tags=["Races"])
router.include_router(components_router, prefix="/components", tags=["Components"])
router.include_router(upgrades_router, prefix="/upgrades", tags=["Upgrades"])
router.include_router(performance_router, prefix="/performance", tags=["Performance"])
router.include_router(events_router, prefix="/events", tags=["Events"])
router.include_router(evidence_router, prefix="/evidence", tags=["Evidence"])
router.include_router(assets_router, prefix="/assets", tags=["Assets"])
router.include_router(seed_router, prefix="/seed", tags=["Seed Data"])
router.include_router(regulations_router, prefix="/regulations", tags=["Regulations"])
