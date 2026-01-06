from fastapi import APIRouter
from scraper import search_items  # Import when you need it
from pydantic import BaseModel
import csv

print("📦 eBay routes loaded")
router = APIRouter(prefix="/api/ebay", tags=["ebay"])

class GPUSearchRequest(BaseModel):
    id: int


def csv_id_search(id: int, component: str):
    with open(f'static/data/{component}.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row['id']) == id:
                return row
    return None

@router.post("/search-gpu")
async def search_gpu_prices(request: GPUSearchRequest):
    gpu = csv_id_search(request.id, 'gpus')

    if not gpu:
        return {"error": "GPU not found"}

    vendor = gpu['Vendor']
    series = gpu['Series']
    model = gpu['Model']
    exclude_var = ["Super", "Ti", "XT", "XTX", "GRE", "D", "LE"]
    if gpu['Variant'] == 'Base': 
        variant = ''
    else: 
        variant = gpu['Variant']
        for i in variant.split(): exclude_var.remove(i)
    vram = gpu['VRAM_GB']
    

    query = f"{vendor} {series} {model} {variant} {vram}GB"
    print (f"Searching eBay for: {query}")
    print(f"With Exclusions: {exclude_var}")
    #results = search_items(request.gpu_name, request.max_results)
    #return {"results": results}
    return {"message": "Functionality not implemented yet."}