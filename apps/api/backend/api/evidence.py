from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.database import get_db
from backend.models.models import Evidence
from backend.schemas.schemas import EvidenceCreate, EvidenceRead

router = APIRouter()


@router.get("/", response_model=List[EvidenceRead])
def list_evidence(
    upgrade_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Evidence)
    if upgrade_id:
        q = q.filter(Evidence.upgrade_id == upgrade_id)
    return q.order_by(Evidence.created_at.desc()).all()


@router.get("/{evidence_id}", response_model=EvidenceRead)
def get_evidence(evidence_id: UUID, db: Session = Depends(get_db)):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return ev


@router.post("/", response_model=EvidenceRead, status_code=201)
def create_evidence(payload: EvidenceCreate, db: Session = Depends(get_db)):
    ev = Evidence(**payload.model_dump())
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/{evidence_id}", status_code=204)
def delete_evidence(evidence_id: UUID, db: Session = Depends(get_db)):
    ev = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    db.delete(ev)
    db.commit()
