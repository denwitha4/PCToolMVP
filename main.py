from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import init_db
import os

# Import route modules
from routes import pages, inventory, builder

# Initialize FastAPI
app = FastAPI(title="PC Inventory Tool")

# Mount static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize database tables
init_db()

# Include all routers
app.include_router(pages.router)
app.include_router(inventory.router)
app.include_router(builder.router)