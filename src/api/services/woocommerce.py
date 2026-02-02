import requests
from requests.auth import HTTPBasicAuth
from typing import List, Optional, Tuple
import time
import json
import hashlib
from pathlib import Path
import os

from config.settings import WC_CONSUMER_KEY, WC_CONSUMER_SECRET, WC_BASE_URL, DATA_DIR

BASE_URL = WC_BASE_URL

# Disk-based cache configuration
CACHE_DIR = DATA_DIR / "cache" / "woocommerce"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = 3600  # 1 hour default

def _get_cache_path(key: str) -> Path:
    hashed_key = hashlib.md5(key.encode()).hexdigest()
    return CACHE_DIR / f"{hashed_key}.json"

def _get_from_cache(key: str, ttl: int = CACHE_TTL) -> Optional[dict]:
    path = _get_cache_path(key)
    if not path.exists():
        return None
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Check expiry
        if time.time() - data["timestamp"] > ttl:
            return None
            
        return data["value"]
    except Exception as e:
        print(f"Cache read error for {key}: {e}")
        return None

def _save_to_cache(key: str, value: any):
    path = _get_cache_path(key)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.time(),
                "value": value
            }, f, ensure_ascii=False)
    except Exception as e:
        print(f"Cache write error for {key}: {e}")

def _get_auth() -> Optional[HTTPBasicAuth]:
    if not WC_CONSUMER_KEY or not WC_CONSUMER_SECRET:
        return None
    return HTTPBasicAuth(WC_CONSUMER_KEY, WC_CONSUMER_SECRET)

def normalize_wc_product(wc_product: dict) -> dict:
    """Convert WooCommerce product structure to our app's Product schema."""
    
    # Extract images
    images = [img['src'] for img in wc_product.get('images', [])]
    
    # Extract brand (check taxonomy 'brands' first, then attributes)
    brand = "De-co-de"
    wc_brands = wc_product.get('brands', [])
    if wc_brands and isinstance(wc_brands, list):
        brand = wc_brands[0].get('name', "De-co-de")
    else:
        for attr in wc_product.get('attributes', []):
            if attr['name'].lower() in ['brand', 'manufacturer', 'бренд', 'производитель']:
                if attr['options']:
                    brand = attr['options'][0]
                    break
                
    # Extract price
    price = wc_product.get('regular_price') or wc_product.get('price') or ""
    if price:
        price = f"{price} EUR"
        
    # Extract category (first one)
    category = ""
    if wc_product.get('categories'):
        category = wc_product['categories'][0].get('name', '')

    # Extract all attributes
    attributes = {}
    
    # Standard dimensions
    dimensions = wc_product.get('dimensions', {})
    dim_str = []
    if dimensions.get('length'):
        dim_str.append(f"L: {dimensions['length']}")
    if dimensions.get('width'):
        dim_str.append(f"W: {dimensions['width']}")
    if dimensions.get('height'):
        dim_str.append(f"H: {dimensions['height']}")
    if dim_str:
        attributes['Размеры (WC)'] = " x ".join(dim_str)
        
    # Weight
    weight = wc_product.get('weight')
    if weight:
        attributes['Вес'] = f"{weight} kg"

    for attr in wc_product.get('attributes', []):
        name = attr.get('name')
        options = attr.get('options', [])
        if name and options:
             attributes[name] = ", ".join(options)

    return {
        "slug": wc_product.get('slug'),
        "name": wc_product.get('name'),
        "title": wc_product.get('name'),
        "brand": brand,
        "category": category,
        "images": images,
        "main_image": images[0] if images else None,
        "source": "woocommerce",
        "description": wc_product.get('description', '').replace('<p>', '').replace('</p>', '\n').strip(),
        "article": wc_product.get('sku') or str(wc_product.get('id')),
        "attributes": attributes,
        "parameters": {
            "Цена": price
        }
    }

def fetch_wc_products(page: int = 1, limit: int = 20, query: Optional[str] = None, category: Optional[str] = None, sort: Optional[str] = None, brand: Optional[str] = None) -> Tuple[List[dict], int]:
    """Fetch products from WooCommerce API with caching."""
    
    # Create cache key from parameters
    cache_key = f"wc_products:{page}:{limit}:{query}:{category}:{sort}:{brand}"
    
    # Check cache
    cached = _get_from_cache(cache_key)
    if cached:
        return cached[0], cached[1]
            
    auth = _get_auth()
    if not auth:
        return [], 0

    # Cap limit at 100 due to WooCommerce API constraints
    if limit > 100:
        limit = 100
        
    params = {
        "per_page": limit,
        "page": page,
        "status": "publish"
    }
    if query:
        params["search"] = query
    
    if category and category != 'all':
        params["category"] = category

    if brand and brand != 'all':
        # Use taxonomy filter for pwb-brand
        params["pwb-brand"] = brand

    if sort:
        if sort == 'price_asc':
            params["orderby"] = "price"
            params["order"] = "asc"
        elif sort == 'price_desc':
            params["orderby"] = "price"
            params["order"] = "desc"
        
    try:
        response = requests.get(
            f"{BASE_URL}/products",
            auth=auth,
            params=params,
            timeout=10
        )
        if response.status_code == 200:
            total = int(response.headers.get('X-WP-Total', 0))
            products = [normalize_wc_product(p) for p in response.json()]
            result = (products, total)
            
            # Cache the result
            _save_to_cache(cache_key, result)
            return result
        print(f"WC API Error: {response.status_code} - {response.text}")
        return [], 0
    except Exception as e:
        print(f"WC API Exception: {e}")
        return [], 0

def fetch_wc_brands() -> List[dict]:
    """Fetch distinct brands from WooCommerce pwb-brand taxonomy with caching."""
    cache_key = "wc_brands_list"
    cached = _get_from_cache(cache_key, ttl=86400) # Cache for 24 hours
    if cached:
        return cached

    auth = _get_auth()
    if not auth:
        return []

    try:
        # Use WP API for taxonomies directly
        wp_base = BASE_URL.split("/wp-json/")[0].rstrip("/")
        wp_url = f"{wp_base}/wp-json/wp/v2/pwb-brand"
        resp = requests.get(
            wp_url,
            auth=auth,
            params={"per_page": 100, "hide_empty": True},
            timeout=10
        )
        if resp.status_code == 200:
            brands = [{"id": str(b["id"]), "name": b["name"]} for b in resp.json()]
            _save_to_cache(cache_key, brands)
            return brands
        return []
    except Exception as e:
        print(f"WC Brand Fetch Error: {e}")
        return []

def get_wc_product_by_slug(slug: str) -> Optional[dict]:
    """Fetch a single details by slug with caching."""
    cache_key = f"wc_product_slug:{slug}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    auth = _get_auth()
    if not auth:
        return None

    try:
        # Search by slug
        response = requests.get(
            f"{BASE_URL}/products",
            auth=auth,
            params={"slug": slug},
            timeout=10
        )
        if response.status_code == 200:
            products = response.json()
            if products:
                product = normalize_wc_product(products[0])
                _save_to_cache(cache_key, product)
                return product
        return None
    except Exception:
        return None

def fetch_wc_categories() -> List[dict]:
    """Fetch categories from WooCommerce API with caching."""
    cache_key = "wc_categories_list"
    cached = _get_from_cache(cache_key, ttl=86400) # Cache for 24h
    if cached:
        return cached

    auth = _get_auth()
    if not auth:
        return []

    try:
        response = requests.get(
            f"{BASE_URL}/products/categories",
            auth=auth,
            params={"per_page": 100, "hide_empty": True, "parent": 0},
            timeout=10
        )
        if response.status_code == 200:
            cats = [{"id": str(c["id"]), "name": c["name"], "count": c["count"]} for c in response.json()]
            _save_to_cache(cache_key, cats)
            return cats
        return []
    except Exception as e:
        print(f"WC Category Fetch Error: {e}")
        return []
