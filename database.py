from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum

Base = declarative_base()

class ComponentCategory(str, enum.Enum):
    CPU = "CPU"
    GPU = "GPU"
    MOTHERBOARD = "Motherboard"
    RAM = "RAM"
    STORAGE = "Storage"
    PSU = "PSU"
    CASE = "Case"
    COOLING = "Cooling"
    PERIPHERAL = "Peripheral"

class Component(Base):
    __tablename__ = "components"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "i7-12700k", "RTX 3070 Ti"
    category = Column(Enum(ComponentCategory), nullable=False)
    quantity = Column(Integer, default=0)
    cost_per_unit = Column(Float, nullable=False)  # What you paid
    retail_price = Column(Float, nullable=True)  # What you sell for (optional)
    supplier = Column(String, nullable=True)
    location = Column(String, nullable=True)  # Where it's stored
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to builds
    build_components = relationship("BuildComponent", back_populates="component")

class BuildStatus(str, enum.Enum):
    PLANNING = "Planning"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    SOLD = "Sold"

class Build(Base):
    __tablename__ = "builds"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "Gaming PC #1", "Office Build"
    status = Column(Enum(BuildStatus), default=BuildStatus.PLANNING)
    customer_name = Column(String, nullable=True)
    selling_price = Column(Float, nullable=True)  # What you sold it for
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    sold_at = Column(DateTime, nullable=True)
    
    # Relationship to components
    build_components = relationship("BuildComponent", back_populates="build", cascade="all, delete-orphan")
    
    @property
    def total_cost(self):
        """Calculate total cost based on components used"""
        return sum(bc.cost_at_time * bc.quantity for bc in self.build_components)
    
    @property
    def profit(self):
        """Calculate profit if sold"""
        if self.selling_price:
            return self.selling_price - self.total_cost
        return None

class BuildComponent(Base):
    """Junction table linking builds to components"""
    __tablename__ = "build_components"
    
    id = Column(Integer, primary_key=True, index=True)
    build_id = Column(Integer, ForeignKey("builds.id"), nullable=False)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=False)
    quantity = Column(Integer, default=1)  # How many of this component in the build
    cost_at_time = Column(Float, nullable=False)  # Lock in the cost when added to build
    
    # Relationships
    build = relationship("Build", back_populates="build_components")
    component = relationship("Component", back_populates="build_components")

# Database setup
DATABASE_URL = "sqlite:///./pc_inventory.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Example usage:
if __name__ == "__main__":
    # Create tables
    init_db()
    
    # Example: Add a component
    db = SessionLocal()
    
    cpu = Component(
        name="i7-12700k",
        category=ComponentCategory.CPU,
        quantity=3,
        cost_per_unit=350.00,
        retail_price=450.00,
        supplier="NewEgg",
        location="Shelf A1"
    )
    
    gpu = Component(
        name="RTX 3070 Ti",
        category=ComponentCategory.GPU,
        quantity=2,
        cost_per_unit=550.00,
        retail_price=700.00,
        supplier="Amazon",
        location="Shelf A2"
    )
    
    db.add(cpu)
    db.add(gpu)
    db.commit()
    
    # Example: Create a build
    build = Build(
        name="Gaming PC #1",
        status=BuildStatus.IN_PROGRESS,
        customer_name="John Doe"
    )
    db.add(build)
    db.commit()
    
    # Add components to build
    build_cpu = BuildComponent(
        build_id=build.id,
        component_id=cpu.id,
        quantity=1,
        cost_at_time=cpu.cost_per_unit
    )
    build_gpu = BuildComponent(
        build_id=build.id,
        component_id=gpu.id,
        quantity=1,
        cost_at_time=gpu.cost_per_unit
    )
    
    db.add(build_cpu)
    db.add(build_gpu)
    db.commit()
    
    # Check total cost
    print(f"Build total cost: ${build.total_cost}")
    
    db.close()