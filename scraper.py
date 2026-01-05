# scraper.py - eBay Browse API scraper (for live listings with prices)
import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()

EBAY_APP_ID = os.getenv("EBAY_APP_ID")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID")

def get_oauth_token():
    """Get OAuth token for Browse API"""
    url = "https://api.ebay.com/identity/v1/oauth2/token"
    
    # Create basic auth header
    credentials = f"{EBAY_APP_ID}:{EBAY_CERT_ID}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }
    
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"❌ OAuth Error: {response.status_code}")
        print(response.text)
        return None

EXCLUDE_TERMS = [
    "fan", "motherboard", "mobile", "water", "block", "desktop", "artifact", 
    "fans", "intel", "pcb", "heatsink", "core", "only", "workstation", "bundle", 
    "broken", "replacement", "connector", "repair", "travel", "alienware", 
    "waterblock", "backplate", "bracket", "mount", "adapter", "cable", 
    "riser", "extension", "parts", "bad", "laptop", "dell", "TB", "Computer", "Gaming",
    "PC"
]

def search_items(keyword, max_results=10):
    """Search eBay for live listings with prices"""
    token = get_oauth_token()
    
    if not token:
        return []
    
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
    }

    # Build search query with exclusions
    search_query = keyword
    
    for term in EXCLUDE_TERMS:
        search_query += f" -{term}"
    
    print("🔎 Search Query:", search_query)
    params = {
        "q": search_query,
        "filter": "conditionIds:{1000|1500|2000|2500|3000|4000|5000|6000}",
        "limit": max_results
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"❌ Search Error: {response.status_code}")
        print(response.text)
        return []
    
    data = response.json()
    
    if 'itemSummaries' not in data:
        print("No items found")
        return []
    
    items = []
    for item in data['itemSummaries']:
        # Extract item info
        title = item.get('title', 'N/A')
        item_id = item.get('itemId', 'N/A')
        
        # Get price
        price = 'N/A'
        if 'price' in item:
            price_info = item['price']
            price = f"${price_info.get('value', 'N/A')} {price_info.get('currency', '')}"
        
        # Get shipping
        shipping = 'N/A'
        if 'shippingOptions' in item and len(item['shippingOptions']) > 0:
            shipping_info = item['shippingOptions'][0]
            if 'shippingCost' in shipping_info:
                shipping_cost = shipping_info['shippingCost']
                shipping = f"${shipping_cost.get('value', '0')} {shipping_cost.get('currency', '')}"
        
        # Get condition
        condition = item.get('condition', 'N/A')
        
        # Get seller
        seller = 'N/A'
        if 'seller' in item:
            seller = item['seller'].get('username', 'N/A')
        
        # Get image
        image_url = 'N/A'
        if 'image' in item:
            image_url = item['image'].get('imageUrl', 'N/A')
        
        # Get item URL
        item_url = item.get('itemWebUrl', 'N/A')
        
        items.append({
            'title': title,
            'item_id': item_id,
            'price': price,
            'shipping': shipping,
            'condition': condition,
            'seller': seller,
            'image_url': image_url,
            'url': item_url
        })
    
    return items

def main():
    if not EBAY_APP_ID or not EBAY_CERT_ID:
        print("❌ Missing credentials in .env file")
        print("Required: EBAY_APP_ID and EBAY_CERT_ID")
        return
    
    print(f"✅ App ID: {EBAY_APP_ID[:15]}...")
    print(f"✅ Cert ID: {EBAY_CERT_ID[:15]}...")
    
    search_term = input("\nSearch term: ").strip()
    if not search_term:
        print("❌ Search term required")
        return
    
    max_results = input("Max results (default 10): ").strip() or "10"
    max_results = int(max_results)
    
    print(f"\n🔍 Searching eBay for: {search_term}")
    print("-" * 60)
    
    items = search_items(search_term, max_results)
    
    if not items:
        print("❌ No results found")
        return
    
    print(f"\n✅ Found {len(items)} items:\n")
    
    for i, item in enumerate(items, 1):
        print(f"{i}. {item['title'][:70]}")
        print(f"   Price: {item['price']}")
        print(f"   Shipping: {item['shipping']}")
        print(f"   Condition: {item['condition']}")
        print(f"   Seller: {item['seller']}")
        print(f"   URL: {item['url']}")
        print()

if __name__ == "__main__":
    main()