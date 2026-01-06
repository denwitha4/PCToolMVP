from fastapi import APIRouter
from scraper import search_items  # Import when you need it
from pydantic import BaseModel

print("📦 eBay routes loaded")
router = APIRouter(prefix="/api/ebay", tags=["ebay"])

class GPUSearchRequest(BaseModel):
    gpu_name: str
    max_results: int = 10

@router.post("/search-gpu-prices")
async def search_gpu_prices(request: GPUSearchRequest):
    results = search_items(request.gpu_name, request.max_results)
    return {"results": results}