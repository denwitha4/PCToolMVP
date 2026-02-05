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
    vram = gpu['VRAM_GB']
    exclude_var = ["Super", "Ti", "XT", "XTX", "GRE", "D", "LE"]
    if gpu['Variant'] == 'Base': 
        variant = ''
    else: 
        variant = gpu['Variant']
        for i in variant.split(): exclude_var.remove(i)
    

    query = f"{model} {variant} {vram}GB"



    print(query)

    results = search_items(query, extra_exclusions=exclude_var)

    results = results or []
    lowest = sorted(results, key=lambda x: float(x["price"]))[:3] if results else []


    average_price = sum([float(item['price']) for item in results]) / len(results) if results else 0
    sold_link = results[0].get("sold_link") if results else None
    if sold_link:
        print(f"Sold Link: {sold_link}")
    return {"average_price": average_price, "lowest_listings": lowest, "sold_link": sold_link}