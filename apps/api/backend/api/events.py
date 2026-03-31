from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID

from backend.database import get_db
from backend.models.models import Event
from backend.models.enums import EventStatus
from backend.schemas.schemas import EventCreate, EventRead, EventUpdate

router = APIRouter()


@router.get("/", response_model=List[EventRead])
def list_events(
    status: EventStatus | None = None,
    race_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Event).options(joinedload(Event.race))
    if status:
        q = q.filter(Event.status == status)
    if race_id:
        q = q.filter(Event.race_id == race_id)
    return q.order_by(Event.created_at.desc()).all()


@router.get("/{event_id}", response_model=EventRead)
def get_event(event_id: UUID, db: Session = Depends(get_db)):
    event = (
        db.query(Event)
        .options(joinedload(Event.race))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("/", response_model=EventRead, status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    event = Event(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return db.query(Event).options(joinedload(Event.race)).filter(Event.id == event.id).first()


@router.patch("/{event_id}", response_model=EventRead)
def update_event_status(event_id: UUID, payload: EventUpdate, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = payload.status
    db.commit()
    db.refresh(event)
    return db.query(Event).options(joinedload(Event.race)).filter(Event.id == event.id).first()
