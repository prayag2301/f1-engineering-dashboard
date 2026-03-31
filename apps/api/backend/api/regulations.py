from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.database import get_db
from backend.models.models import RegulationConstraint
from backend.schemas.schemas import RegulationConstraintCreate, RegulationConstraintRead

router = APIRouter()


@router.get("/", response_model=List[RegulationConstraintRead])
def list_regulations(
    season: Optional[int] = Query(None, description="Filter by season year, e.g. 2026"),
    component: Optional[str] = Query(None, description="Filter by component, e.g. front_wing"),
    db: Session = Depends(get_db),
):
    """Return regulation constraints, optionally filtered by season and/or component."""
    q = db.query(RegulationConstraint)
    if season is not None:
        q = q.filter(RegulationConstraint.season == season)
    if component is not None:
        q = q.filter(RegulationConstraint.component == component)
    return q.order_by(RegulationConstraint.component, RegulationConstraint.parameter).all()


@router.get("/{regulation_id}", response_model=RegulationConstraintRead)
def get_regulation(regulation_id: str, db: Session = Depends(get_db)):
    obj = db.query(RegulationConstraint).filter(RegulationConstraint.id == regulation_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Regulation constraint not found")
    return obj


@router.post("/", response_model=RegulationConstraintRead, status_code=201)
def create_regulation(payload: RegulationConstraintCreate, db: Session = Depends(get_db)):
    obj = RegulationConstraint(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
