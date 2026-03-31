from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.database import get_db
from backend.models.models import Team
from backend.schemas.schemas import TeamCreate, TeamRead

router = APIRouter()


@router.get("/", response_model=List[TeamRead])
def list_teams(db: Session = Depends(get_db)):
    return db.query(Team).all()


@router.get("/{team_id}", response_model=TeamRead)
def get_team(team_id: UUID, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.post("/", response_model=TeamRead, status_code=201)
def create_team(payload: TeamCreate, db: Session = Depends(get_db)):
    team = Team(**payload.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team
