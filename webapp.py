from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import get_db, Component
from sqlalchemy.orm import Session

router = APIRouter()
templates = Jinja2Templates(directory="templates") ## Tells FastAPI to look for html files in templates


## Get request for a page 
@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("index.html", {"request": request}) 

@router.get("/inventory", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("inventory.html", {"request": request}) 



@router.post("/button-click")
async def button_click(data: dict):
    """Handle button click events"""
    button_name = data.get("button", "Unknown")
    return {
        "status": "success",
        "message": f"Received click from {button_name}",
        "timestamp": "2024-12-06"
    }

@router.get("/components")
def get_components(db: Session = Depends(get_db)):
    """Get all components from database"""
    components = db.query(Component).all()
    return [{"id": c.id, "name": c.name, "category": c.category.value, "cost": c.cost_per_unit} for c in components]