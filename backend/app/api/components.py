from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.models import Component
from app.schemas.schemas import ComponentCreate, ComponentRead
from app.models.enums import ComponentZone

router = APIRouter()


@router.get("/", response_model=List[ComponentRead])
def list_components(zone: ComponentZone | None = None, db: Session = Depends(get_db)):
    q = db.query(Component)
    if zone:
        q = q.filter(Component.zone == zone)
    return q.all()


@router.get("/{component_id}", response_model=ComponentRead)
def get_component(component_id: UUID, db: Session = Depends(get_db)):
    comp = db.query(Component).filter(Component.id == component_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")
    return comp


@router.post("/", response_model=ComponentRead, status_code=201)
def create_component(payload: ComponentCreate, db: Session = Depends(get_db)):
    comp = Component(**payload.model_dump())
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp
