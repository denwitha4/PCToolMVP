from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from database import get_db, Component, ComponentCategory
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

# Pydantic models for request validation
class ComponentCreate(BaseModel):
    name: str
    category: ComponentCategory
    cost_per_unit: float
    msrp: Optional[float] = None

class ComponentUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[ComponentCategory] = None
    cost_per_unit: Optional[float] = None
    msrp: Optional[float] = None

# GET all components
@router.get("/components")
def get_components(db: Session = Depends(get_db)):
    """Get all components from database"""
    components = db.query(Component).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "category": c.category.value,
            "cost": c.cost_per_unit,
            "msrp": c.msrp
        }
        for c in components
    ]

# POST create new component
@router.post("/components")
def create_component(component: ComponentCreate, db: Session = Depends(get_db)):
    """Create a new component"""
    new_component = Component(
        name=component.name,
        category=component.category,
        cost_per_unit=component.cost_per_unit,
        msrp=component.msrp
    )
    db.add(new_component)
    db.commit()
    db.refresh(new_component)
    
    return {
        "id": new_component.id,
        "name": new_component.name,
        "category": new_component.category.value,
        "cost": new_component.cost_per_unit,
        "msrp": new_component.msrp,
        "message": "Component created successfully"
    }

# PUT update component
@router.put("/components/{component_id}")
def update_component(
    component_id: int,
    component_update: ComponentUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing component"""
    component = db.query(Component).filter(Component.id == component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    if component_update.name is not None:
        component.name = component_update.name
    if component_update.category is not None:
        component.category = component_update.category
    if component_update.cost_per_unit is not None:
        component.cost_per_unit = component_update.cost_per_unit
    if component_update.msrp is not None:
        component.msrp = component_update.msrp
    
    db.commit()
    db.refresh(component)
    
    return {
        "id": component.id,
        "name": component.name,
        "category": component.category.value,
        "cost": component.cost_per_unit,
        "msrp": component.msrp,
        "message": "Component updated successfully"
    }

# DELETE component
@router.delete("/components/{component_id}")
def delete_component(component_id: int, db: Session = Depends(get_db)):
    """Delete a component"""
    component = db.query(Component).filter(Component.id == component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    # Check if component is used in any builds
    from database import BuildComponent
    used_in_builds = db.query(BuildComponent).filter(BuildComponent.component_id == component_id).first()
    if used_in_builds:
        raise HTTPException(status_code=400, detail="Cannot delete component that is used in builds")
    
    db.delete(component)
    db.commit()
    
    return {"message": "Component deleted successfully", "id": component_id}



# GET components in plaintext REMOVE THIS WHENEVER
@router.get("/components/text", response_class=PlainTextResponse)
def get_components_text(db: Session = Depends(get_db)):
    """Get all components in plaintext format"""
    components = db.query(Component).all()
    if not components:
        return "No components found."
    
    text = "Components:\n\n"
    for c in components:
        text += f"ID: {c.id}\n"
        text += f"Name: {c.name}\n"
        text += f"Category: {c.category.value}\n"
        text += f"Cost per Unit: ${c.cost_per_unit}\n"
        text += f"MSRP: ${c.msrp if c.msrp else 'N/A'}\n"
        text += "\n"
    
    return text