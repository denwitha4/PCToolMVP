from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import (
    get_db,
    Product,
    InventoryLot,
    InventoryMovement,
    ProductCategory,
    InventoryStatus,
    LotCondition,
    MovementType,
)
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from auth import get_current_user_id

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def _log_movement(db: Session, lot_id: int, movement_type: MovementType, quantity: int):
    """Log an inventory movement. Call after mutating lot quantities."""
    mov = InventoryMovement(
        inventory_lot_id=lot_id,
        movement_type=movement_type,
        quantity=quantity,
    )
    db.add(mov)


def _component_response(component: InventoryLot) -> Dict[str, Any]:
    """Serialize component with computed fields and product info."""
    return {
        "id": component.id,
        "user_id": component.user_id,
        "product_id": component.product_id,
        "product_name": component.product.name if component.product else None,
        "category": component.product.category.value if component.product else None,
        "internal_sku": component.internal_sku,
        "vendor": component.vendor,
        "vendor_sku": component.vendor_sku,
        "condition": component.condition.value if component.condition else None,
        "unit_cost": component.unit_cost,
        "sales_tax": component.sales_tax,
        "shipping_cost": component.shipping_cost,
        "fees": component.fees,
        "quantity_on_hand": component.quantity_on_hand,
        "quantity_reserved": component.quantity_reserved,
        "quantity_available": component.quantity_available,
        "total_landed_cost": round(component.total_landed_cost, 2),
        "total_inventory_value": round(component.total_inventory_value, 2),
        "inventory_status": component.inventory_status.value if component.inventory_status else None,
        "assigned_build_id": component.assigned_build_id,
        "serial_number": component.serial_number,
        "storage_location": component.storage_location,
        "notes": component.notes,
        "notes_preview": (component.notes[:80] + "…") if component.notes and len(component.notes) > 80 else component.notes,
        "created_at": component.created_at.isoformat() if component.created_at else None,
        "updated_at": component.updated_at.isoformat() if component.updated_at else None,
    }


# --- Pydantic schemas ---

class ProductCreate(BaseModel):
    name: str
    category: ProductCategory
    msrp: Optional[float] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[ProductCategory] = None
    msrp: Optional[float] = None


class ComponentCreate(BaseModel):
    product_id: int
    vendor: str
    unit_cost: float
    quantity_on_hand: int = 1
    condition: LotCondition = LotCondition.NEW
    sales_tax: float = 0.0
    shipping_cost: float = 0.0
    fees: float = 0.0
    vendor_sku: Optional[str] = None
    serial_number: Optional[str] = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None


class ComponentUpdate(BaseModel):
    vendor: Optional[str] = None
    unit_cost: Optional[float] = None
    quantity_on_hand: Optional[int] = None
    sales_tax: Optional[float] = None
    shipping_cost: Optional[float] = None
    fees: Optional[float] = None
    condition: Optional[LotCondition] = None
    vendor_sku: Optional[str] = None
    serial_number: Optional[str] = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None


class BulkEditUpdates(BaseModel):
    vendor: Optional[str] = None
    unit_cost: Optional[float] = None
    quantity_on_hand: Optional[int] = None
    sales_tax: Optional[float] = None
    shipping_cost: Optional[float] = None
    fees: Optional[float] = None
    notes: Optional[str] = None
    category: Optional[ProductCategory] = None


class BulkEditBody(BaseModel):
    component_ids: List[int]
    updates: BulkEditUpdates


class MergeBody(BaseModel):
    component_ids: List[int]


class ReserveItem(BaseModel):
    component_id: int
    quantity: int


class ReserveBody(BaseModel):
    items: List[ReserveItem]
    build_id: Optional[int] = None


class ReleaseBody(BaseModel):
    items: List[ReserveItem]


class SellBody(BaseModel):
    items: List[ReserveItem]


class SoftDeleteBody(BaseModel):
    component_ids: List[int]


# --- Products ---

@router.post("/products")
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new product (catalog entry)."""
    product = Product(
        name=body.name,
        category=body.category,
        msrp=body.msrp,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category.value,
        "msrp": product.msrp,
        "created_at": product.created_at.isoformat() if product.created_at else None,
    }


@router.get("/products")
def list_products(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List products that the user has inventory for (has at least one non-deleted lot)."""
    product_ids = [
        r[0]
        for r in db.query(InventoryLot.product_id)
        .filter(InventoryLot.user_id == user_id, InventoryLot.soft_delete == False)
        .distinct()
        .all()
    ]
    products = (
        db.query(Product)
        .filter(Product.id.in_(product_ids))
        .order_by(Product.name)
        .all()
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category.value,
            "msrp": p.msrp,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in products
    ]


@router.get("/products/all")
def list_all_products(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List all products (for dropdown when adding a new lot with new product)."""
    products = db.query(Product).order_by(Product.name).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category.value,
            "msrp": p.msrp,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in products
    ]


@router.get("/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category.value,
        "msrp": product.msrp,
        "created_at": product.created_at.isoformat() if product.created_at else None,
    }


@router.put("/products/{product_id}")
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if body.name is not None:
        product.name = body.name
    if body.category is not None:
        product.category = body.category
    if body.msrp is not None:
        product.msrp = body.msrp
    db.commit()
    db.refresh(product)
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category.value,
        "msrp": product.msrp,
        "message": "Product updated successfully",
    }


# --- Lots ---

def _next_internal_sku(db: Session, user_id: int) -> str:
    """Generate unique internal SKU per user."""
    from sqlalchemy import func
    r = db.query(func.count(InventoryLot.id)).filter(InventoryLot.user_id == user_id).scalar()
    return f"SKU-{user_id}-{r + 1}"


@router.post("/components")
def create_component(
    body: ComponentCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Add an inventory component. Logs Add movement."""
    product = db.query(Product).filter(Product.id == body.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if body.quantity_on_hand < 1:
        raise HTTPException(status_code=400, detail="quantity_on_hand must be at least 1")
    internal_sku = _next_internal_sku(db, user_id)
    component = InventoryLot(
        user_id=user_id,
        product_id=body.product_id,
        internal_sku=internal_sku,
        vendor=body.vendor,
        vendor_sku=body.vendor_sku,
        condition=body.condition,
        unit_cost=body.unit_cost,
        sales_tax=body.sales_tax,
        shipping_cost=body.shipping_cost,
        fees=body.fees,
        quantity_on_hand=body.quantity_on_hand,
        quantity_reserved=0,
        inventory_status=InventoryStatus.IN_STOCK,
        serial_number=body.serial_number,
        storage_location=body.storage_location,
        notes=body.notes,
    )
    db.add(component)
    db.flush()
    _log_movement(db, component.id, MovementType.ADD, body.quantity_on_hand)
    db.commit()
    db.refresh(component)
    return _component_response(component)


@router.get("/components")
def list_components(
    product_id: Optional[int] = None,
    status: Optional[str] = None,
    build_id: Optional[int] = None,
    include_deleted: bool = False,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List components for current user with computed fields. Exclude soft-deleted by default."""
    q = (
        db.query(InventoryLot)
        .join(Product)
        .filter(InventoryLot.user_id == user_id)
    )
    if not include_deleted:
        q = q.filter(InventoryLot.soft_delete == False)
    if product_id is not None:
        q = q.filter(InventoryLot.product_id == product_id)
    if status is not None:
        q = q.filter(InventoryLot.inventory_status == InventoryStatus(status))
    if build_id is not None:
        q = q.filter(InventoryLot.assigned_build_id == build_id)
    components = q.order_by(InventoryLot.created_at.desc()).all()
    return [_component_response(component) for component in components]


@router.get("/components/{component_id}")
def get_component(
    component_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    component = (
        db.query(InventoryLot)
        .join(Product)
        .filter(InventoryLot.id == component_id, InventoryLot.user_id == user_id)
        .first()
    )
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return _component_response(component)


@router.put("/components/{component_id}")
def update_component(
    component_id: int,
    body: ComponentUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    component = db.query(InventoryLot).filter(
        InventoryLot.id == component_id,
        InventoryLot.user_id == user_id,
    ).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    if component.soft_delete:
        raise HTTPException(status_code=400, detail="Cannot edit soft-deleted component")
    old_qty = component.quantity_on_hand
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(component, k, v)
    if body.quantity_on_hand is not None and body.quantity_on_hand != old_qty:
        delta = body.quantity_on_hand - old_qty
        _log_movement(db, component.id, MovementType.ADJUST, delta)
    db.commit()
    db.refresh(component)
    return _component_response(component)


# --- Bulk edit ---

@router.put("/components/bulk-edit")
def bulk_edit_components(
    body: BulkEditBody,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Apply updates to multiple components. Category updates the linked product."""
    updates = body.updates.model_dump(exclude_unset=True)
    category = updates.pop("category", None)
    components = (
        db.query(InventoryLot)
        .filter(InventoryLot.id.in_(body.component_ids), InventoryLot.user_id == user_id)
        .all()
    )
    if len(components) != len(body.component_ids):
        raise HTTPException(status_code=404, detail="One or more components not found")
    for component in components:
        if component.soft_delete:
            continue
        old_qty = component.quantity_on_hand
        for k, v in updates.items():
            if hasattr(component, k):
                setattr(component, k, v)
        if "quantity_on_hand" in updates and updates["quantity_on_hand"] != old_qty:
            delta = updates["quantity_on_hand"] - old_qty
            _log_movement(db, component.id, MovementType.ADJUST, delta)
    if category is not None:
        product_ids = {component.product_id for component in components}
        for pid in product_ids:
            p = db.query(Product).filter(Product.id == pid).first()
            if p:
                p.category = ProductCategory(category)
    db.commit()
    return {"message": "Bulk edit applied", "count": len(components)}


# --- Bulk actions ---

@router.post("/components/merge")
def merge_components(
    body: MergeBody,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Merge multiple components into one. Allowed only if same product_id and same unit_cost."""
    if len(body.component_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 components to merge")
    components = (
        db.query(InventoryLot)
        .filter(InventoryLot.id.in_(body.component_ids), InventoryLot.user_id == user_id)
        .all()
    )
    if len(components) != len(body.component_ids):
        raise HTTPException(status_code=404, detail="One or more components not found")
    product_id = components[0].product_id
    unit_cost = components[0].unit_cost
    condition = components[0].condition
    for component in components[1:]:
        if component.product_id != product_id or component.unit_cost != unit_cost or component.condition != condition:
            raise HTTPException(
                status_code=400,
                detail="Merge allowed only when product_id, unit_cost, and condition match",
            )
        if component.soft_delete:
            raise HTTPException(status_code=400, detail="Cannot merge soft-deleted component")
    total_qty = sum(c.quantity_on_hand for c in components)
    total_tax = sum(c.sales_tax for c in components)
    total_shipping = sum(c.shipping_cost for c in components)
    total_fees = sum(c.fees for c in components)
    first = components[0]
    new_sku = _next_internal_sku(db, user_id)
    new_component = InventoryLot(
        user_id=user_id,
        product_id=product_id,
        internal_sku=new_sku,
        vendor=first.vendor,
        condition=first.condition,
        unit_cost=unit_cost,
        sales_tax=total_tax,
        shipping_cost=total_shipping,
        fees=total_fees,
        quantity_on_hand=total_qty,
        quantity_reserved=0,
        inventory_status=InventoryStatus.IN_STOCK,
        notes="Merged from components " + ",".join(str(c.id) for c in components),
    )
    db.add(new_component)
    db.flush()
    _log_movement(db, new_component.id, MovementType.ADD, total_qty)
    for component in components:
        old_qty = component.quantity_on_hand
        component.soft_delete = True
        component.quantity_on_hand = 0
        _log_movement(db, component.id, MovementType.ADJUST, -old_qty)
    db.commit()
    db.refresh(new_component)
    return _component_response(new_component)


@router.post("/components/reserve")
def reserve_components(
    body: ReserveBody,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Increase reserved quantity on components. Optionally assign build_id."""
    for item in body.items:
        component = db.query(InventoryLot).filter(
            InventoryLot.id == item.component_id,
            InventoryLot.user_id == user_id,
        ).first()
        if not component:
            raise HTTPException(status_code=404, detail=f"Component {item.component_id} not found")
        if component.soft_delete:
            raise HTTPException(status_code=400, detail=f"Component {item.component_id} is deleted")
        available = component.quantity_on_hand - component.quantity_reserved
        if item.quantity > available:
            raise HTTPException(
                status_code=400,
                detail=f"Component {item.component_id}: requested {item.quantity}, available {available}",
            )
        component.quantity_reserved += item.quantity
        if body.build_id is not None:
            component.assigned_build_id = body.build_id
        if component.quantity_reserved > 0:
            component.inventory_status = InventoryStatus.RESERVED
        _log_movement(db, component.id, MovementType.RESERVE, item.quantity)
    db.commit()
    return {"message": "Reserved successfully"}


@router.post("/components/release")
def release_components(
    body: ReleaseBody,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Decrease reserved quantity on components. Clear assigned_build_id when reserved hits 0."""
    for item in body.items:
        component = db.query(InventoryLot).filter(
            InventoryLot.id == item.component_id,
            InventoryLot.user_id == user_id,
        ).first()
        if not component:
            raise HTTPException(status_code=404, detail=f"Component {item.component_id} not found")
        if item.quantity > component.quantity_reserved:
            raise HTTPException(
                status_code=400,
                detail=f"Component {item.component_id}: cannot release more than reserved",
            )
        component.quantity_reserved -= item.quantity
        if component.quantity_reserved <= 0:
            component.assigned_build_id = None
            component.inventory_status = InventoryStatus.IN_STOCK
        _log_movement(db, component.id, MovementType.RELEASE, -item.quantity)
    db.commit()
    return {"message": "Released successfully"}


@router.post("/components/sell")
def sell_components(
    body: SellBody,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Reduce quantity_on_hand. Mark component sold when quantity_on_hand reaches 0."""
    for item in body.items:
        component = db.query(InventoryLot).filter(
            InventoryLot.id == item.component_id,
            InventoryLot.user_id == user_id,
        ).first()
        if not component:
            raise HTTPException(status_code=404, detail=f"Component {item.component_id} not found")
        if component.soft_delete:
            raise HTTPException(status_code=400, detail=f"Component {item.component_id} is deleted")
        available = component.quantity_on_hand - component.quantity_reserved
        if item.quantity > available:
            raise HTTPException(
                status_code=400,
                detail=f"Component {item.component_id}: cannot sell more than available",
            )
        component.quantity_on_hand -= item.quantity
        _log_movement(db, component.id, MovementType.SELL, -item.quantity)
        if component.quantity_on_hand <= 0:
            component.inventory_status = InventoryStatus.SOLD
    db.commit()
    return {"message": "Sold successfully"}


@router.post("/components/soft-delete")
def soft_delete_components(
    body: SoftDeleteBody,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Soft delete components. Do not hard delete."""
    components = (
        db.query(InventoryLot)
        .filter(InventoryLot.id.in_(body.component_ids), InventoryLot.user_id == user_id)
        .all()
    )
    for component in components:
        component.soft_delete = True
    db.commit()
    return {"message": "Soft deleted successfully", "count": len(components)}


@router.get("/components/{component_id}/movements")
def list_component_movements(
    component_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    component = db.query(InventoryLot).filter(
        InventoryLot.id == component_id,
        InventoryLot.user_id == user_id,
    ).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    movements = (
        db.query(InventoryMovement)
        .filter(InventoryMovement.inventory_lot_id == component_id)
        .order_by(InventoryMovement.timestamp.desc())
        .all()
    )
    return [
        {
            "id": m.id,
            "movement_type": m.movement_type.value,
            "quantity": m.quantity,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
        }
        for m in movements
    ]
