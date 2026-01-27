from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
import datetime
import enum

Base = declarative_base()
DATABASE_URL = "sqlite:///db/pc_inventory.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

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
    EXTRAS = "Extras"

class Component(Base): ## Defines a specific component
    __tablename__ = "components"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "i7-12700k", "RTX 3070 Ti"
    category = Column(Enum(ComponentCategory), nullable=False)
    cost_per_unit = Column(Float, nullable=False)  # What you paid
    msrp = Column(Float, nullable=True)  # What you sell for (optional)
    user_id = Column(Integer, nullable=False)  # Owner of the component
    #in_build = Column(bool, nullable=False) # Whether or not it is in a build
    
    # Relationship to builds
    build_components = relationship("BuildComponent", back_populates="component")

class BuildStatus(int, enum.Enum):
    PLANNING = 1
    BUILDING = 2
    LISTING = 3
    SELLING = 4
    SOLD = 5

class Build(Base): ## Defines a build, to be ready for parts to be imported.
    __tablename__ = "builds"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "Gaming PC #1", "Office Build"
    status = Column(Enum(BuildStatus), default=BuildStatus.PLANNING)
    selling_price = Column(Float, nullable=True)
    user_id = Column(Integer, nullable=False)  # Owner of the build
    
    # Relationship to components
    build_components = relationship("BuildComponent", back_populates="build", cascade="all, delete-orphan")
    
    @property
    def total_cost(self):
        """Calculate total cost based on components used"""
        return sum(bc.cost_at_time for bc in self.build_components)
    
    @property
    def partsMSRP(self):
        """Gathers the part MSRP"""
        return sum(bc.msrp for bc in self.build_components)

class BuildComponent(Base):
    """Junction table linking builds to components"""
    __tablename__ = "build_components"
    
    id = Column(Integer, primary_key=True, index=True)
    build_id = Column(Integer, ForeignKey("builds.id"), nullable=False)
    component_id = Column(Integer, ForeignKey("components.id"), nullable=False)
    quantity = Column(Integer, default=1)  # How many of this component in the build
    cost_at_time = Column(Float, nullable=False)  # Lock in the cost when added to build
    user_id = Column(Integer, nullable=False)  # Owner of the build component
    
    # Relationships
    build = relationship("Build", back_populates="build_components")
    component = relationship("Component", back_populates="build_components")

# Database setup
DATABASE_URL = "sqlite:///db/pc_inventory.db"
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
