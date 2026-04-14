from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.models import PerformanceDelta
from app.schemas.schemas import PerformanceDeltaCreate, PerformanceDeltaRead

router = APIRouter()


@router.get("/", response_model=List[PerformanceDeltaRead])
def list_deltas(
    team_id: UUID | None = None,
    race_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(PerformanceDelta)
    if team_id:
        q = q.filter(PerformanceDelta.team_id == team_id)
    if race_id:
        q = q.filter(PerformanceDelta.race_id == race_id)
    return q.all()


@router.post("/", response_model=PerformanceDeltaRead, status_code=201)
def create_delta(payload: PerformanceDeltaCreate, db: Session = Depends(get_db)):
    delta = PerformanceDelta(**payload.model_dump())
    db.add(delta)
    db.commit()
    db.refresh(delta)
    return delta
