import requests
import json
import sys
from requests.auth import HTTPBasicAuth
from pathlib import Path

# Add project root to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        # Retry logic
        retries = 3
        success = False
        while retries > 0:
            try:
                response = requests.get(
                    f"{BASE_URL}/products",
                    auth=HTTPBasicAuth(WC_CONSUMER_KEY, WC_CONSUMER_SECRET),
                    params={"per_page": per_page, "page": page},
                    timeout=60
                )
                
                if response.status_code != 200:
                    print(f"Error fetching page {page}: {response.status_code} - {response.text}")
                    # If 400/401/404 maybe don't retry? But 500/502/timeout yes.
                    # For now, let's just retry on error if it's not 4xx (except 429)
                    if response.status_code < 500 and response.status_code != 429:
                        break
                else:
                    success = True
                    break
                    
            except Exception as e:
                print(f"Exception fetching page {page} (attempt {4-retries}): {e}")
                import time
                time.sleep(5)
            
            retries -= 1
        
        if not success:
           print(f"Failed to fetch page {page} after retries.")
           # Don't break completely? Or maybe we should?
           # If we miss a page, we miss data. Better to break and fail loud.
           break

        products = response.json()
        if not products:
            break
            
        all_products.extend(products)
        print(f"Fetched {len(products)} products. Total so far: {len(all_products)}")
        
        page += 1
            
            
    print(f"Finished fetching. Total raw products: {len(all_products)}")
    return all_products

from src.api.services.woocommerce import normalize_wc_product as normalize_product

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
