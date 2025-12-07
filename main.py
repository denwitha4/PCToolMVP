from fastapi import FastAPI
from database import init_db
from webapp import router

# Initialize FastAPI
app = FastAPI(title="PC Inventory Tool")

# Initialize database tables
init_db()

# Include routes from webapp.py
app.include_router(router)
