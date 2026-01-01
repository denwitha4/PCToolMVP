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
    return templates.TemplateResponse("landing/index.html", {"request": request})

@router.get("/home", response_class=HTMLResponse)
async def sales_page(request: Request, db: Session = Depends(get_db)):
    """Home page"""
    return templates.TemplateResponse("home/index.html", {"request": request, "active": "home"})

@router.get("/sales", response_class=HTMLResponse)
async def sales_page(request: Request, db: Session = Depends(get_db)):
    """Sales management page"""
    return templates.TemplateResponse("sales/index.html", {"request": request, "active": "sales"})

@router.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, db: Session = Depends(get_db)):
    """Inventory management page"""
    return templates.TemplateResponse("inventory/index.html", {"request": request, "active": "inventory"})

@router.get("/source", response_class=HTMLResponse)
async def inventory_page(request: Request, db: Session = Depends(get_db)):
    """Sourcing management page"""
    return templates.TemplateResponse("source/index.html", {"request": request, "active": "source"})

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, db: Session = Depends(get_db)):
    """Analytics page"""
    return templates.TemplateResponse("analytics/index.html", {"request": request, "active": "analytics"})

@router.get("/builder", response_class=HTMLResponse)
async def builder_page(request: Request):
    """PC Builder page"""
    return templates.TemplateResponse("builder/index.html", {"request": request, "active": "builder"})

@router.get("/builder/{build_id}", response_class=HTMLResponse)
async def builder_edit_page(request: Request, build_id: int, db: Session = Depends(get_db)):
    """Edit specific build page"""
    return templates.TemplateResponse("builder/edit.html", {"request": request, "build_id": build_id, "active": "builder"})