from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page"""
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, db: Session = Depends(get_db)):
    """Inventory management page"""
    return templates.TemplateResponse("inventory.html", {"request": request})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/builder", response_class=HTMLResponse)
async def builder_page(request: Request, db: Session = Depends(get_db)):
    """PC Builder page"""
    return templates.TemplateResponse("builder.html", {"request": request})