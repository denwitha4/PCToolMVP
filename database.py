from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
    Enum,
    Boolean,
    Text,
    inspect,
)
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy import text
import datetime
import enum

Base = declarative_base()
DATABASE_URL = "sqlite:///db/pc_inventory.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables and run migration if needed."""
    Base.metadata.create_all(bind=engine)
    _migrate_components_to_products()
    _migrate_planner_fields()
    _migrate_bundle_fields()


def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Enums ---

class ProductCategory(str, enum.Enum):
    CPU = "CPU"
    GPU = "GPU"
    MOTHERBOARD = "Motherboard"
    RAM = "RAM"
    STORAGE = "Storage"
    PSU = "PSU"
    CASE = "Case"
    COOLING = "Cooling"
    EXTRAS = "Extras"


class InventoryStatus(str, enum.Enum):
    IN_STOCK = "in_stock"
    RESERVED = "reserved"
    SOLD = "sold"
    DAMAGED = "damaged"
    RETURNED = "returned"


class LotCondition(str, enum.Enum):
    NEW = "new"
    OPEN_BOX = "open_box"
    USED = "used"
    REFURBISHED = "refurbished"


class MovementType(str, enum.Enum):
    ADD = "Add"
    RESERVE = "Reserve"
    RELEASE = "Release"
    SELL = "Sell"
    ADJUST = "Adjust"


class BuildStatus(int, enum.Enum):
    PLANNING = 1
    BUILDING = 2
    LISTING = 3
    SELLING = 4
    SOLD = 5


# --- Models ---

class Product(Base):
    """Catalog: what the item is. No quantity or cost."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(Enum(ProductCategory), nullable=False)
    msrp = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    lots = relationship("InventoryLot", back_populates="product")
    build_components = relationship("BuildComponent", back_populates="product")


class InventoryLot(Base):
    """Stock: how, when, and at what cost the item was acquired."""
    __tablename__ = "inventory_lots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    internal_sku = Column(String, nullable=False, unique=True)
    vendor = Column(String, nullable=False)
    vendor_sku = Column(String, nullable=True)
    condition = Column(Enum(LotCondition), default=LotCondition.NEW)
    unit_cost = Column(Float, nullable=False)
    sales_tax = Column(Float, default=0.0)
    shipping_cost = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)
    quantity_on_hand = Column(Integer, default=0, nullable=False)
    quantity_reserved = Column(Integer, default=0, nullable=False)
    inventory_status = Column(Enum(InventoryStatus), default=InventoryStatus.IN_STOCK)
    assigned_build_id = Column(Integer, ForeignKey("builds.id"), nullable=True)
    serial_number = Column(String, nullable=True)
    storage_location = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    soft_delete = Column(Boolean, default=False)
    bundle_id = Column(Integer, ForeignKey("bundles.id"), nullable=True)
    allocation_weight = Column(Float, nullable=True)
    allocation_locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="lots")
    movements = relationship("InventoryMovement", back_populates="inventory_lot", order_by="InventoryMovement.timestamp")
    build = relationship("Build", back_populates="reserved_lots")
    build_components = relationship("BuildComponent", back_populates="lot")
    bundle = relationship("Bundle", back_populates="lots")

    @property
    def quantity_available(self):
        return self.quantity_on_hand - self.quantity_reserved

    @property
    def total_landed_cost(self):
        return self.unit_cost + self.sales_tax + self.shipping_cost + self.fees

    @property
    def total_inventory_value(self):
        return self.quantity_available * self.total_landed_cost


class InventoryMovement(Base):
    """Audit trail for all quantity-changing actions."""
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    inventory_lot_id = Column(Integer, ForeignKey("inventory_lots.id"), nullable=False)
    movement_type = Column(Enum(MovementType), nullable=False)
    quantity = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    inventory_lot = relationship("InventoryLot", back_populates="movements")


class Bundle(Base):
    """Bundle acquisition record: tracks multi-component purchases."""
    __tablename__ = "bundles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    vendor = Column(String, nullable=False)
    purchase_date = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    lots = relationship("InventoryLot", back_populates="bundle")


class Build(Base):
    __tablename__ = "builds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    status = Column(Enum(BuildStatus), default=BuildStatus.PLANNING)
    selling_price = Column(Float, nullable=True)
    user_id = Column(Integer, nullable=False)
    target_profit_amount = Column(Float, nullable=True)
    target_profit_percentage = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    build_components = relationship(
        "BuildComponent", back_populates="build", cascade="all, delete-orphan"
    )
    reserved_lots = relationship("InventoryLot", back_populates="build")

    @property
    def total_cost(self):
        return sum(bc.total_component_cost for bc in self.build_components)

    @property
    def total_msrp(self):
        total = 0
        for bc in self.build_components:
            if bc.product and bc.product.msrp:
                total += bc.product.msrp * bc.quantity
        return total

    @property
    def partsMSRP(self):
        return self.total_msrp

    @property
    def projected_profit(self):
        return self.total_msrp - self.total_cost

    @property
    def projected_margin_percentage(self):
        if self.total_msrp == 0:
            return 0
        return (self.projected_profit / self.total_msrp) * 100

    @property
    def meets_target_profit(self):
        if self.target_profit_amount is not None:
            return self.projected_profit >= self.target_profit_amount
        elif self.target_profit_percentage is not None:
            return self.projected_margin_percentage >= self.target_profit_percentage
        return None

    @property
    def max_allowable_cost(self):
        if self.target_profit_amount is not None:
            return self.total_msrp - self.target_profit_amount
        elif self.target_profit_percentage is not None:
            return self.total_msrp * (1 - self.target_profit_percentage / 100)
        return None


class BuildComponent(Base):
    """Links builds to products and optionally to the reserved lot."""
    __tablename__ = "build_components"

    id = Column(Integer, primary_key=True, index=True)
    build_id = Column(Integer, ForeignKey("builds.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("inventory_lots.id"), nullable=True)
    quantity = Column(Integer, default=1)
    cost_at_time = Column(Float, nullable=False)
    user_id = Column(Integer, nullable=False)
    is_external = Column(Boolean, default=False)
    quantity_from_inventory = Column(Integer, default=0)
    quantity_external = Column(Integer, default=0)
    external_cost = Column(Float, nullable=True)

    build = relationship("Build", back_populates="build_components")
    product = relationship("Product", back_populates="build_components")
    lot = relationship("InventoryLot", back_populates="build_components")

    @property
    def msrp(self):
        return self.product.msrp if self.product else None

    @property
    def total_msrp(self):
        if self.product and self.product.msrp:
            return self.product.msrp * self.quantity
        return 0

    @property
    def total_component_cost(self):
        return self.cost_at_time * self.quantity

    @property
    def component_profit(self):
        return self.total_msrp - self.total_component_cost

    @property
    def component_margin_percentage(self):
        if self.total_msrp == 0:
            return 0
        return (self.component_profit / self.total_msrp) * 100

    @property
    def cost_contribution_to_build(self):
        if self.build:
            total_cost = self.build.total_cost
            if total_cost == 0:
                return 0
            return (self.total_component_cost / total_cost) * 100
        return 0

    @property
    def is_inventory_backed(self):
        return self.lot_id is not None and not self.is_external

    @property
    def has_sufficient_inventory(self):
        if not self.lot_id:
            return False
        return self.lot.quantity_available >= self.quantity


def _migrate_components_to_products():
    """One-time migration: Component -> Product + InventoryLot, BuildComponent.component_id -> product_id/lot_id."""
    with engine.connect() as conn:
        if not inspect(engine).has_table("components"):
            return
        result = conn.execute(text("SELECT COUNT(*) FROM components"))
        if result.scalar() == 0:
            return

        # Ensure new tables and columns exist
        Base.metadata.create_all(bind=engine)

        # Add product_id, lot_id to build_components if missing
        insp = inspect(engine)
        bc_columns = [c["name"] for c in insp.get_columns("build_components")]
        if "product_id" not in bc_columns:
            conn.execute(text("ALTER TABLE build_components ADD COLUMN product_id INTEGER"))
        if "lot_id" not in bc_columns:
            conn.execute(text("ALTER TABLE build_components ADD COLUMN lot_id INTEGER"))
        conn.commit()

    db = SessionLocal()
    did_migrate = False
    try:
        # Use raw SQL to read old components (Component model no longer exists)
        rows = db.execute(
            text("SELECT id, user_id, name, category, cost_per_unit, msrp, quantity_instock FROM components")
        ).fetchall()

        component_id_to_product = {}
        component_id_to_lot = {}

        for row in rows:
            c_id, user_id, name, category, cost_per_unit, msrp, qty = row
            # Map category (old DB may store enum name e.g. MOTHERBOARD or value e.g. Motherboard)
            try:
                cat = ProductCategory(category)
            except ValueError:
                cat = getattr(ProductCategory, str(category), ProductCategory.EXTRAS)
            # Create Product
            product = Product(
                name=name,
                category=cat,
                msrp=msrp,
            )
            db.add(product)
            db.flush()

            # Create InventoryLot with unique internal_sku
            sku = f"LOT-{user_id}-{product.id}-{c_id}"
            lot = InventoryLot(
                user_id=user_id,
                product_id=product.id,
                internal_sku=sku,
                vendor="Migrated",
                unit_cost=cost_per_unit,
                quantity_on_hand=qty,
                quantity_reserved=0,
                inventory_status=InventoryStatus.IN_STOCK,
            )
            db.add(lot)
            db.flush()

            # Log Add movement
            mov = InventoryMovement(
                inventory_lot_id=lot.id,
                movement_type=MovementType.ADD,
                quantity=qty,
            )
            db.add(mov)

            component_id_to_product[c_id] = product.id
            component_id_to_lot[c_id] = lot.id

        db.commit()
        did_migrate = True

        # Update build_components
        bc_rows = db.execute(
            text("SELECT id, component_id FROM build_components WHERE component_id IS NOT NULL")
        ).fetchall()
        for bc_id, comp_id in bc_rows:
            if comp_id in component_id_to_product and comp_id in component_id_to_lot:
                db.execute(
                    text(
                        "UPDATE build_components SET product_id = :pid, lot_id = :lid WHERE id = :id"
                    ),
                    {
                        "pid": component_id_to_product[comp_id],
                        "lid": component_id_to_lot[comp_id],
                        "id": bc_id,
                    },
                )
        db.commit()

        # Drop components table
        db.execute(text("DROP TABLE IF EXISTS components"))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # Drop component_id column only after a successful migration (SQLite 3.35+)
    if did_migrate:
        with engine.connect() as conn:
            try:
                insp = inspect(engine)
                cols = [c["name"] for c in insp.get_columns("build_components")]
                if "component_id" in cols:
                    conn.execute(text("ALTER TABLE build_components DROP COLUMN component_id"))
                    conn.commit()
            except Exception:
                conn.rollback()


def _migrate_planner_fields():
    """Add planner-related fields to builds and build_components tables."""
    with engine.connect() as conn:
        insp = inspect(engine)
        
        # Add fields to builds table
        builds_columns = [c["name"] for c in insp.get_columns("builds")]
        
        if "target_profit_amount" not in builds_columns:
            conn.execute(text("ALTER TABLE builds ADD COLUMN target_profit_amount REAL"))
        if "target_profit_percentage" not in builds_columns:
            conn.execute(text("ALTER TABLE builds ADD COLUMN target_profit_percentage REAL"))
        if "created_at" not in builds_columns:
            conn.execute(text("ALTER TABLE builds ADD COLUMN created_at TIMESTAMP"))
        if "updated_at" not in builds_columns:
            conn.execute(text("ALTER TABLE builds ADD COLUMN updated_at TIMESTAMP"))
        
        # Add fields to build_components table
        bc_columns = [c["name"] for c in insp.get_columns("build_components")]
        
        if "is_external" not in bc_columns:
            conn.execute(text("ALTER TABLE build_components ADD COLUMN is_external BOOLEAN DEFAULT 0"))
        if "quantity_from_inventory" not in bc_columns:
            conn.execute(text("ALTER TABLE build_components ADD COLUMN quantity_from_inventory INTEGER DEFAULT 0"))
        if "quantity_external" not in bc_columns:
            conn.execute(text("ALTER TABLE build_components ADD COLUMN quantity_external INTEGER DEFAULT 0"))
        if "external_cost" not in bc_columns:
            conn.execute(text("ALTER TABLE build_components ADD COLUMN external_cost REAL"))
        
        conn.commit()


def _migrate_bundle_fields():
    """Add bundle-related fields to inventory_lots table."""
    with engine.connect() as conn:
        insp = inspect(engine)
        
        # Add fields to inventory_lots table
        lot_columns = [c["name"] for c in insp.get_columns("inventory_lots")]
        
        if "bundle_id" not in lot_columns:
            conn.execute(text("ALTER TABLE inventory_lots ADD COLUMN bundle_id INTEGER"))
        if "allocation_weight" not in lot_columns:
            conn.execute(text("ALTER TABLE inventory_lots ADD COLUMN allocation_weight REAL"))
        if "allocation_locked" not in lot_columns:
            conn.execute(text("ALTER TABLE inventory_lots ADD COLUMN allocation_locked BOOLEAN DEFAULT 0"))
        
        conn.commit()
