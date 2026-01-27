from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Build, BuildComponent, Component, BuildStatus
from pydantic import BaseModel
from typing import List
from auth import get_current_user_id

router = APIRouter(prefix="/api/sales", tags=["sales"])

# Response models only (no Create models needed)
class BuildComponentResponse(BaseModel):    
    id: int
    component_name: str
    category: str
    cost_at_time: float
    msrp: float = None

    class Config:
        from_attributes = True

class BuildResponse(BaseModel):
    id: int
    name: str
    status: int
    components: List[BuildComponentResponse] = []
    
    class Config:
        from_attributes = True

@router.get("/building")

@router.get("/listing")
def get_builds(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    builds = db.query(Build).filter(Build.user_id == user_id).all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "status": b.status.value,
            "total_cost": b.total_cost,
            "selling_price": b.selling_price
        }
        for b in builds
    ]

@router.get("/selling")
