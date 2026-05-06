from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from backend.database import get_db
from backend.models.models import Asset
from backend.models.enums import AssetType
from backend.schemas.schemas import AssetCreate, AssetRead

router = APIRouter()


@router.get("/", response_model=List[AssetRead])
def list_assets(
    upgrade_id: UUID | None = None,
    asset_type: AssetType | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Asset)
    if upgrade_id:
        q = q.filter(Asset.upgrade_id == upgrade_id)
    if asset_type:
        q = q.filter(Asset.asset_type == asset_type)
    return q.order_by(Asset.created_at.desc()).all()


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: UUID, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/", response_model=AssetRead, status_code=201)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(by_alias=True)
    asset = Asset(
        upgrade_id=data["upgrade_id"],
        asset_type=data["asset_type"],
        path=data["path"],
        metadata_=data.get("metadata"),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: UUID, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.commit()
