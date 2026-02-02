from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Build, BuildComponent, Product, BuildStatus
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


