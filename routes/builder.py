from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Build, BuildComponent, Component
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/builder", tags=["builder"])

# Pydantic models
class BuildCreate(BaseModel):
    name: str
    status: str = "Planning"

class BuildComponentCreate(BaseModel):
    component_id: int
    quantity: int = 1
    cost_at_time: float

class BuildComponentResponse(BaseModel):
    id: int
    component_name: str
    category: str
    cost_at_time: float
    msrp: float = None

# GET all builds
@router.get("/builds")
def get_builds(db: Session = Depends(get_db)):
    builds = db.query(Build).all()
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

# POST create new build
@router.post("/builds")
def create_build(build: BuildCreate, db: Session = Depends(get_db)):
    new_build = Build(name=build.name, status=build.status)
    db.add(new_build)
    db.commit()
    db.refresh(new_build)
    return {
        "id": new_build.id,
        "name": new_build.name,
        "status": new_build.status.value
    }

# GET single build
@router.get("/builds/{build_id}")
def get_build(build_id: int, db: Session = Depends(get_db)):
    build = db.query(Build).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return {
        "id": build.id,
        "name": build.name,
        "status": build.status.value,
        "total_cost": build.total_cost,
        "selling_price": build.selling_price
    }

# GET build components
@router.get("/builds/{build_id}/components")
def get_build_components(build_id: int, db: Session = Depends(get_db)):
    build_components = db.query(BuildComponent).filter(BuildComponent.build_id == build_id).all()
    result = []
    for bc in build_components:
        result.append({
            "id": bc.id,
            "component_name": bc.component.name,
            "category": bc.component.category.value,
            "cost_at_time": bc.cost_at_time,
            "msrp": bc.component.msrp
        })
    return result

# POST add component to build
@router.post("/builds/{build_id}/components")
def add_component_to_build(build_id: int, component_data: BuildComponentCreate, db: Session = Depends(get_db)):
    # Check if build exists
    build = db.query(Build).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    # Check if component exists
    component = db.query(Component).filter(Component.id == component_data.component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    # Remove any existing component of the same category for this build
    existing_component = db.query(BuildComponent).join(Component).filter(
        BuildComponent.build_id == build_id,
        Component.category == component.category
    ).first()
    
    if existing_component:
        db.delete(existing_component)
        db.commit()
    
    new_bc = BuildComponent(
        build_id=build_id,
        component_id=component_data.component_id,
        quantity=component_data.quantity,
        cost_at_time=component_data.cost_at_time
    )
    db.add(new_bc)
    db.commit()
    db.refresh(new_bc)
    return {"message": "Component added to build"}

# DELETE build
@router.delete("/builds/{build_id}")
def delete_build(build_id: int, db: Session = Depends(get_db)):
    build = db.query(Build).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    db.delete(build)
    db.commit()
    return {"message": "Build deleted successfully"}

# PUT remove component from build (editing the build to not include the component)
@router.put("/builds/{build_id}/components/{build_component_id}")
def remove_component_from_build(build_id: int, build_component_id: int, db: Session = Depends(get_db)):
    # Check if build exists
    build = db.query(Build).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    # Find the build component
    bc = db.query(BuildComponent).filter(
        BuildComponent.id == build_component_id,
        BuildComponent.build_id == build_id
    ).first()
    if not bc:
        raise HTTPException(status_code=404, detail="Component not found in build")
    
    # Delete the build component (editing the build)
    db.delete(bc)
    db.commit()
    return {"message": "Component removed from build"}