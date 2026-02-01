import requests
import json
from requests.auth import HTTPBasicAuth
from pathlib import Path

# Configuration
from config.settings import WC_CONSUMER_KEY, WC_CONSUMER_SECRET, WC_BASE_URL

BASE_URL = WC_BASE_URL
OUTPUT_FILE = Path("data/processed/wc_catalog.json")

def fetch_all_products():
    if not WC_CONSUMER_KEY or not WC_CONSUMER_SECRET:
        raise RuntimeError("WC_CONSUMER_KEY/WC_CONSUMER_SECRET are not set")

    page = 1
    per_page = 50
    all_products = []
    
    print(f"Starting sync from {BASE_URL}...")
    
    while True:
        print(f"Fetching page {page}...")
        try:
            response = requests.get(
                f"{BASE_URL}/products",
                auth=HTTPBasicAuth(WC_CONSUMER_KEY, WC_CONSUMER_SECRET),
                params={"per_page": per_page, "page": page},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error fetching page {page}: {response.status_code} - {response.text}")
                break
                
            products = response.json()
            if not products:
                break
                
            all_products.extend(products)
            print(f"Fetched {len(products)} products. Total so far: {len(all_products)}")
            
            page += 1
            
        except Exception as e:
            print(f"Exception fetching page {page}: {e}")
            break
            
    print(f"Finished fetching. Total raw products: {len(all_products)}")
    return all_products

def normalize_product(wc_product):
    """Convert WooCommerce product structure to our app's Product schema."""
    
    # Extract images
    images = [img['src'] for img in wc_product.get('images', [])]
    
    # Extract brand (attribute or default)
    brand = "De-co-de"
    for attr in wc_product.get('attributes', []):
        if attr['name'].lower() in ['brand', 'manufacturer', 'бренд', 'производитель']:
            if attr['options']:
                brand = attr['options'][0]
                break
                
    # Extract price
    price = wc_product.get('regular_price') or wc_product.get('price') or ""
    if price:
        price = f"{price} ₽"
        
    # Create normalized object
    return {
        "slug": wc_product.get('slug'),
        "name": wc_product.get('name'),
        "title": wc_product.get('name'), # Use name as title
        "brand": brand,
        "images": images,
        "main_image": images[0] if images else None,
        "source": "woocommerce", # critical field for filtering
        "description": wc_product.get('description', '').replace('<p>', '').replace('</p>', '\n').strip(),
        "article": wc_product.get('sku') or str(wc_product.get('id')),
        "parameters": {
            "Цена": price
        }
    }

def save_catalog(products):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    normalized = []
    for p in products:
        try:
            norm = normalize_product(p)
            normalized.append(norm)
        except Exception as e:
            print(f"Error normalizing product {p.get('id')}: {e}")
            
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {len(normalized)} products to {OUTPUT_FILE}")

if __name__ == "__main__":
    raw_products = fetch_all_products()
    save_catalog(raw_products)
