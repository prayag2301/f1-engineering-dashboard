from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.database import get_db
from backend.models.models import Race
from backend.schemas.schemas import RaceCreate, RaceRead

router = APIRouter()


@router.get("/", response_model=List[RaceRead])
def list_races(season: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Race)
    if season:
        q = q.filter(Race.season == season)
    return q.order_by(Race.round_number).all()


@router.get("/{race_id}", response_model=RaceRead)
def get_race(race_id: UUID, db: Session = Depends(get_db)):
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")
    return race


@router.post("/", response_model=RaceRead, status_code=201)
def create_race(payload: RaceCreate, db: Session = Depends(get_db)):
    race = Race(**payload.model_dump())
    db.add(race)
    db.commit()
    db.refresh(race)
    return race
