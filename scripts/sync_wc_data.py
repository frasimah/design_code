
import requests
from requests.auth import HTTPBasicAuth
import json
import sys
import os
import time

# Add project root to path
sys.path.append(os.getcwd())
from config.settings import WC_CONSUMER_KEY, WC_CONSUMER_SECRET, WC_BASE_URL, DATA_DIR

def sync_woocommerce_data():
    print("🚀 Starting WooCommerce Data Sync (Text Only)...")
    
    auth = HTTPBasicAuth(WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
    
    # 1. Fetch Brands (Taxonomies)
    print("📦 Fetching Brands...")
    brands_map = {}
    try:
        wp_base = WC_BASE_URL.split("/wp-json/")[0].rstrip("/")
        wp_url = f"{wp_base}/wp-json/wp/v2/pwb-brand"
        
        page = 1
        while True:
            resp = requests.get(wp_url, auth=auth, params={"per_page": 100, "page": page}, timeout=20)
            if resp.status_code != 200: break
            data = resp.json()
            if not data: break
            
            for b in data:
                brands_map[b['id']] = b['name']
            
            if page >= int(resp.headers.get('X-WP-TotalPages', 1)): break
            page += 1
            print(f"   got brand page {page-1}...")
            
    except Exception as e:
        print(f"⚠️ Failed to fetch brands: {e}")

    print(f"✅ Loaded {len(brands_map)} brands.")

    # 2. Fetch Products
    print("📦 Fetching Products...")
    all_products = []
    page = 1
    
    while True:
        try:
            resp = requests.get(
                f"{WC_BASE_URL}/products",
                auth=auth,
                params={"per_page": 50, "page": page, "status": "publish"},
                timeout=30
            )
            
            if resp.status_code != 200:
                print(f"❌ Error fetching page {page}: {resp.status_code}")
                break
                
            data = resp.json()
            if not data:
                break
            
            for p in data:
                # Enrich with brand name immediately to save time later
                p_brands = p.get('brands', []) 
                # Depends on plugin, sometimes 'brands' is already populated with {id, name}
                # If not, use brands_map if needed. usually plugin adds it.
                
                # Strip unnecessary fields to save space? Nah, keep it compatible.
                all_products.append(p)
                
            print(f"   Page {page}: {len(data)} items (Total: {len(all_products)})")
            
            if page >= int(resp.headers.get('X-WP-TotalPages', 1)):
                break
            page += 1
            
        except Exception as e:
            print(f"❌ Exception on page {page}: {e}")
            time.sleep(2) # retry?
            break

    # 3. Save to file
    output_file = DATA_DIR / "wc_full_cache.json"
    
    final_data = {
        "updated_at": time.time(),
        "brands_map": brands_map,
        "products": all_products
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ Sync Complete! Saved {len(all_products)} products to {output_file}")
    
if __name__ == "__main__":
    sync_woocommerce_data()
