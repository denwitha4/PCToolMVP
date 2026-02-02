from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import (
    get_db,
    Build,
    BuildComponent,
    Product,
    InventoryLot,
    InventoryMovement,
    BuildStatus,
    MovementType,
    InventoryStatus,
)
from pydantic import BaseModel
from typing import Optional, List, Literal
from auth import get_current_user_id

router = APIRouter(prefix="/api/planner", tags=["planner"])


# Pydantic Models
class BuildCreate(BaseModel):
    name: str
    target_profit_amount: Optional[float] = None
    target_profit_percentage: Optional[float] = None


class BuildUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[int] = None
    selling_price: Optional[float] = None
    target_profit_amount: Optional[float] = None
    target_profit_percentage: Optional[float] = None


class ComponentAdd(BaseModel):
    product_id: int
    lot_id: Optional[int] = None
    quantity: int = 1
    cost_at_time: float
    is_external: bool = False


class ComponentUpdate(BaseModel):
    quantity: Optional[int] = None
    cost_at_time: Optional[float] = None
    lot_id: Optional[int] = None
    is_external: Optional[bool] = None


class ReservationRequest(BaseModel):
    lot_id: int
    quantity: int


# Planner Logic Functions
def calculate_component_metrics(component: BuildComponent, build_total_cost: float):
    """Calculate all metrics for a single component."""
    product = component.product
    lot = component.lot
    
    metrics = {
        "id": component.id,
        "product_id": component.product_id,
        "product_name": product.name if product else "Unknown",
        "category": product.category.value if product else "Unknown",
        "quantity": component.quantity,
        "unit_cost": component.cost_at_time,
        "total_cost": component.total_component_cost,
        "unit_msrp": product.msrp if product else 0,
        "total_msrp": component.total_msrp,
        "profit_absolute": component.component_profit,
        "profit_margin_percentage": component.component_margin_percentage,
        "cost_contribution_percentage": component.cost_contribution_to_build,
        "is_inventory_backed": component.is_inventory_backed,
        "is_external": component.is_external,
        "lot_id": component.lot_id,
    }
    
    # Inventory availability info
    if lot:
        metrics["inventory_available"] = lot.quantity_available
        metrics["inventory_reserved"] = lot.quantity_reserved
        metrics["has_sufficient_inventory"] = component.has_sufficient_inventory
        metrics["vendor"] = lot.vendor
        metrics["condition"] = lot.condition.value
    else:
        metrics["inventory_available"] = 0
        metrics["inventory_reserved"] = 0
        metrics["has_sufficient_inventory"] = False
        metrics["vendor"] = "External"
        metrics["condition"] = "N/A"
    
    return metrics


def calculate_build_metrics(build: Build):
    """Calculate all metrics for a build including target profit analysis."""
    total_cost = build.total_cost
    total_msrp = build.total_msrp
    projected_profit = build.projected_profit
    projected_margin_pct = build.projected_margin_percentage
    
    metrics = {
        "id": build.id,
        "name": build.name,
        "status": build.status.value,
        "selling_price": build.selling_price,
        "created_at": build.created_at.isoformat() if build.created_at else None,
        "updated_at": build.updated_at.isoformat() if build.updated_at else None,
        "total_cost": total_cost,
        "total_msrp": total_msrp,
        "projected_profit": projected_profit,
        "projected_margin_percentage": projected_margin_pct,
        "target_profit_amount": build.target_profit_amount,
        "target_profit_percentage": build.target_profit_percentage,
        "meets_target_profit": build.meets_target_profit,
        "max_allowable_cost": build.max_allowable_cost,
        "component_count": len(build.build_components),
    }
    
    # Target profit analysis
    if build.target_profit_amount is not None or build.target_profit_percentage is not None:
        max_cost = build.max_allowable_cost
        metrics["target_mode"] = "active"
        metrics["cost_variance"] = max_cost - total_cost if max_cost else None
        
        if metrics["meets_target_profit"]:
            metrics["target_status"] = "meets"
        elif max_cost and total_cost > max_cost:
            metrics["target_status"] = "over_budget"
            metrics["over_budget_amount"] = total_cost - max_cost
        else:
            metrics["target_status"] = "under_target"
    else:
        metrics["target_mode"] = "inactive"
        metrics["target_status"] = None
        metrics["cost_variance"] = None
    
    # Component-level breakdown
    components = []
    for bc in build.build_components:
        comp_metrics = calculate_component_metrics(bc, total_cost)
        components.append(comp_metrics)
    
    metrics["components"] = components
    
    # Identify problematic components if over budget
    if metrics.get("target_status") == "over_budget":
        metrics["high_cost_components"] = sorted(
            [c for c in components],
            key=lambda x: x["cost_contribution_percentage"],
            reverse=True
        )[:3]
    
    return metrics


def soft_reserve_inventory(
    db: Session,
    lot_id: int,
    quantity: int,
    build_id: int,
    user_id: int
):
    """
    Soft-reserve inventory for a build.
    - Reduces available inventory
    - Does NOT mark as sold
    - Reversible
    """
    lot = db.query(InventoryLot).filter(
        InventoryLot.id == lot_id,
        InventoryLot.user_id == user_id,
    ).first()
    
    if not lot:
        raise HTTPException(status_code=404, detail="Inventory lot not found")
    
    if lot.soft_delete:
        raise HTTPException(status_code=400, detail="Inventory lot is deleted")
    
    available = lot.quantity_available
    if quantity > available:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient inventory. Available: {available}, Requested: {quantity}"
        )
    
    lot.quantity_reserved += quantity
    lot.assigned_build_id = build_id
    
    if lot.quantity_reserved > 0:
        lot.inventory_status = InventoryStatus.RESERVED
    
    # Log reservation movement
    movement = InventoryMovement(
        inventory_lot_id=lot.id,
        movement_type=MovementType.RESERVE,
        quantity=quantity,
    )
    db.add(movement)
    
    return lot


def release_inventory_reservation(
    db: Session,
    lot_id: int,
    quantity: int,
    user_id: int
):
    """Release a soft reservation."""
    lot = db.query(InventoryLot).filter(
        InventoryLot.id == lot_id,
        InventoryLot.user_id == user_id,
    ).first()
    
    if not lot:
        return
    
    lot.quantity_reserved = max(0, lot.quantity_reserved - quantity)
    
    if lot.quantity_reserved == 0:
        lot.assigned_build_id = None
        lot.inventory_status = InventoryStatus.IN_STOCK
    
    # Log release movement
    movement = InventoryMovement(
        inventory_lot_id=lot.id,
        movement_type=MovementType.RELEASE,
        quantity=-quantity,
    )
    db.add(movement)


# API Endpoints

@router.post("/builds")
def create_build(
    build: BuildCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new build plan."""
    new_build = Build(
        user_id=user_id,
        name=build.name,
        status=BuildStatus.PLANNING,
        target_profit_amount=build.target_profit_amount,
        target_profit_percentage=build.target_profit_percentage,
    )
    db.add(new_build)
    db.commit()
    db.refresh(new_build)
    
    return calculate_build_metrics(new_build)


@router.get("/builds")
def get_all_builds(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get all builds for the user with basic metrics."""
    builds = db.query(Build).filter(Build.user_id == user_id).all()
    return [calculate_build_metrics(b) for b in builds]


@router.get("/builds/{build_id}")
def get_build(
    build_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get detailed build plan with all metrics."""
    build = db.query(Build).filter(
        Build.id == build_id,
        Build.user_id == user_id,
    ).first()
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    return calculate_build_metrics(build)


@router.put("/builds/{build_id}")
def update_build(
    build_id: int,
    build_update: BuildUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Update build details including target profit settings."""
    build = db.query(Build).filter(
        Build.id == build_id,
        Build.user_id == user_id,
    ).first()
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    if build_update.name is not None:
        build.name = build_update.name
    if build_update.status is not None:
        build.status = BuildStatus(build_update.status)
    if build_update.selling_price is not None:
        build.selling_price = build_update.selling_price
    if build_update.target_profit_amount is not None:
        build.target_profit_amount = build_update.target_profit_amount
        build.target_profit_percentage = None
    if build_update.target_profit_percentage is not None:
        build.target_profit_percentage = build_update.target_profit_percentage
        build.target_profit_amount = None
    
    db.commit()
    db.refresh(build)
    
    return calculate_build_metrics(build)


@router.delete("/builds/{build_id}")
def delete_build(
    build_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a build and release all reservations."""
    build = db.query(Build).filter(
        Build.id == build_id,
        Build.user_id == user_id,
    ).first()
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    # Release all inventory reservations
    for component in build.build_components:
        if component.lot_id and not component.is_external:
            release_inventory_reservation(
                db, component.lot_id, component.quantity, user_id
            )
    
    db.delete(build)
    db.commit()
    
    return {"message": "Build deleted successfully"}


@router.get("/builds/{build_id}/components-list")
def get_build_components_list(
    build_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get components for a build (backward compatible format for frontend)."""
    build = db.query(Build).filter(
        Build.id == build_id,
        Build.user_id == user_id,
    ).first()
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    build_components = db.query(BuildComponent).filter(
        BuildComponent.build_id == build_id,
        BuildComponent.user_id == user_id,
    ).all()

    result = []
    for bc in build_components:
        result.append({
            "id": bc.id,
            "component_name": bc.product.name if bc.product else "",
            "category": bc.product.category.value if bc.product else "",
            "cost_at_time": bc.cost_at_time,
            "msrp": bc.product.msrp if bc.product else None,
            "product_id": bc.product_id,
            "lot_id": bc.lot_id,
            # Enhanced planner fields
            "quantity": bc.quantity,
            "is_external": bc.is_external,
            "is_inventory_backed": bc.is_inventory_backed,
            "total_cost": bc.total_component_cost,
            "total_msrp": bc.total_msrp,
            "profit_absolute": bc.component_profit,
            "profit_margin_percentage": bc.component_margin_percentage,
        })
    return result


@router.post("/builds/{build_id}/components")
def add_component_to_build(
    build_id: int,
    component: ComponentAdd,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Add a component to a build (inventory-backed or external)."""
    build = db.query(Build).filter(
        Build.id == build_id,
        Build.user_id == user_id,
    ).first()
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    # Verify product exists
    product = db.query(Product).filter(Product.id == component.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check if component of same category already exists
    existing = db.query(BuildComponent).join(Product).filter(
        BuildComponent.build_id == build_id,
        BuildComponent.user_id == user_id,
        Product.category == product.category,
    ).first()
    
    if existing:
        # Release existing reservation if applicable
        if existing.lot_id and not existing.is_external:
            release_inventory_reservation(
                db, existing.lot_id, existing.quantity, user_id
            )
        db.delete(existing)
        db.commit()
    
    # Handle inventory reservation if not external
    if component.lot_id and not component.is_external:
        soft_reserve_inventory(
            db, component.lot_id, component.quantity, build_id, user_id
        )
    
    # Create build component
    new_component = BuildComponent(
        build_id=build_id,
        product_id=component.product_id,
        lot_id=component.lot_id,
        quantity=component.quantity,
        cost_at_time=component.cost_at_time,
        is_external=component.is_external,
        quantity_from_inventory=0 if component.is_external else component.quantity,
        quantity_external=component.quantity if component.is_external else 0,
        user_id=user_id,
    )
    
    db.add(new_component)
    db.commit()
    db.refresh(new_component)
    
    # Return updated build metrics
    db.refresh(build)
    return calculate_build_metrics(build)


@router.put("/builds/{build_id}/components/{component_id}")
def update_component(
    build_id: int,
    component_id: int,
    component_update: ComponentUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Update a component in a build."""
    build = db.query(Build).filter(
        Build.id == build_id,
        Build.user_id == user_id,
    ).first()
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    component = db.query(BuildComponent).filter(
        BuildComponent.id == component_id,
        BuildComponent.build_id == build_id,
        BuildComponent.user_id == user_id,
    ).first()
    
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    # Handle quantity change with reservations
    if component_update.quantity is not None and component_update.quantity != component.quantity:
        if component.lot_id and not component.is_external:
            # Release old reservation
            release_inventory_reservation(
                db, component.lot_id, component.quantity, user_id
            )
            # Reserve new quantity
            soft_reserve_inventory(
                db, component.lot_id, component_update.quantity, build_id, user_id
            )
        component.quantity = component_update.quantity
    
    if component_update.cost_at_time is not None:
        component.cost_at_time = component_update.cost_at_time
    
    # Handle switching between inventory and external
    if component_update.is_external is not None and component_update.is_external != component.is_external:
        if component_update.is_external and component.lot_id:
            # Switching to external - release reservation
            release_inventory_reservation(
                db, component.lot_id, component.quantity, user_id
            )
        elif not component_update.is_external and component.lot_id:
            # Switching to inventory - reserve
            soft_reserve_inventory(
                db, component.lot_id, component.quantity, build_id, user_id
            )
        component.is_external = component_update.is_external
    
    # Handle lot change
    if component_update.lot_id is not None and component_update.lot_id != component.lot_id:
        # Release old lot if exists
        if component.lot_id and not component.is_external:
            release_inventory_reservation(
                db, component.lot_id, component.quantity, user_id
            )
        # Reserve new lot
        if component_update.lot_id and not component.is_external:
            soft_reserve_inventory(
                db, component_update.lot_id, component.quantity, build_id, user_id
            )
        component.lot_id = component_update.lot_id
    
    db.commit()
    db.refresh(build)
    
    return calculate_build_metrics(build)


@router.delete("/builds/{build_id}/components/{component_id}")
def remove_component(
    build_id: int,
    component_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Remove a component from a build."""
    build = db.query(Build).filter(
        Build.id == build_id,
        Build.user_id == user_id,
    ).first()
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    component = db.query(BuildComponent).filter(
        BuildComponent.id == component_id,
        BuildComponent.build_id == build_id,
        BuildComponent.user_id == user_id,
    ).first()
    
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    
    # Release reservation if applicable
    if component.lot_id and not component.is_external:
        release_inventory_reservation(
            db, component.lot_id, component.quantity, user_id
        )
    
    db.delete(component)
    db.commit()
    db.refresh(build)
    
    return calculate_build_metrics(build)


@router.get("/builds/{build_id}/target-profit-analysis")
def get_target_profit_analysis(
    build_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get detailed target profit analysis for a build."""
    build = db.query(Build).filter(
        Build.id == build_id,
        Build.user_id == user_id,
    ).first()
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    metrics = calculate_build_metrics(build)
    
    analysis = {
        "build_id": build.id,
        "build_name": build.name,
        "target_mode_active": metrics["target_mode"] == "active",
        "target_status": metrics["target_status"],
        "current_profit": metrics["projected_profit"],
        "current_margin_percentage": metrics["projected_margin_percentage"],
        "target_profit_amount": build.target_profit_amount,
        "target_profit_percentage": build.target_profit_percentage,
        "meets_target": metrics["meets_target_profit"],
        "max_allowable_cost": metrics["max_allowable_cost"],
        "current_total_cost": metrics["total_cost"],
        "cost_variance": metrics["cost_variance"],
        "total_msrp": metrics["total_msrp"],
    }
    
    if metrics.get("over_budget_amount"):
        analysis["over_budget_amount"] = metrics["over_budget_amount"]
        analysis["problematic_components"] = metrics.get("high_cost_components", [])
    
    return analysis


@router.get("/inventory-available")
def get_available_inventory(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get available inventory for planner component selection."""
    query = db.query(InventoryLot).join(Product).filter(
        InventoryLot.user_id == user_id,
        InventoryLot.soft_delete == False,
    )
    
    if category:
        from database import ProductCategory
        query = query.filter(Product.category == ProductCategory(category))
    
    lots = query.all()
    
    result = []
    for lot in lots:
        result.append({
            "lot_id": lot.id,
            "product_id": lot.product_id,
            "product_name": lot.product.name,
            "category": lot.product.category.value,
            "msrp": lot.product.msrp,
            "unit_cost": lot.total_landed_cost,
            "quantity_available": lot.quantity_available,
            "quantity_reserved": lot.quantity_reserved,
            "quantity_on_hand": lot.quantity_on_hand,
            "vendor": lot.vendor,
            "condition": lot.condition.value,
            "internal_sku": lot.internal_sku,
            "is_available": lot.quantity_available > 0,
        })
    
    return result


@router.post("/builds/{build_id}/reserve")
def create_reservation(
    build_id: int,
    reservation: ReservationRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Soft-reserve inventory for a build (manual reservation)."""
    build = db.query(Build).filter(
        Build.id == build_id,
        Build.user_id == user_id,
    ).first()
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    soft_reserve_inventory(
        db, reservation.lot_id, reservation.quantity, build_id, user_id
    )
    
    db.commit()
    
    return {"message": "Inventory reserved successfully"}


@router.delete("/builds/{build_id}/reserve/{lot_id}")
def release_reservation(
    build_id: int,
    lot_id: int,
    quantity: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Release a soft reservation."""
    build = db.query(Build).filter(
        Build.id == build_id,
        Build.user_id == user_id,
    ).first()
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    release_inventory_reservation(db, lot_id, quantity, user_id)
    db.commit()
    
    return {"message": "Reservation released successfully"}


@router.get("/builds/{build_id}/reservations")
def get_build_reservations(
    build_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Get all inventory reservations for a build."""
    build = db.query(Build).filter(
        Build.id == build_id,
        Build.user_id == user_id,
    ).first()
    
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    reservations = []
    for component in build.build_components:
        if component.lot_id and not component.is_external:
            lot = component.lot
            reservations.append({
                "component_id": component.id,
                "lot_id": lot.id,
                "product_name": component.product.name,
                "category": component.product.category.value,
                "quantity_reserved": component.quantity,
                "internal_sku": lot.internal_sku,
                "vendor": lot.vendor,
                "condition": lot.condition.value,
            })
    
    return reservations
