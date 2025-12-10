from fastapi import APIRouter
router = APIRouter(prefix="/builder", tags=["builder"])

@router.get("/builds")
def get_builds():
    pass