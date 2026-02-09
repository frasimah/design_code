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
    if wc_brands and isinstance(wc_brands, list) and len(wc_brands) > 0:
        brand = wc_brands[0].get('name', "De-co-de")
    else:
        # Check attributes for brand-like fields
        found_brand = False
        for attr in wc_product.get('attributes', []):
            name_lower = attr['name'].lower()
            slug_lower = attr.get('slug', '').lower()
            
            if name_lower in ['brand', 'manufacturer', 'бренд', 'производитель'] or \
               slug_lower in ['pa_brand', 'pa_manufacturer', 'brand']:
                if attr['options']:
                    brand = attr['options'][0]
                    found_brand = True
                    break
        
        # Check meta_data if not found in attributes
        if not found_brand:
            for meta in wc_product.get('meta_data', []):
                if meta.get('key') == 'brand' or meta.get('key') == '_brand':
                    brand = meta.get('value')
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

def get_brand_id_by_name(name: str) -> Optional[int]:
    """Resolve brand name to WooCommerce taxonomy ID."""
    brands = fetch_wc_brands()
    for b in brands:
        if b['name'].lower() == name.lower():
            return b['id']
    return None

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
    # Try to load from FULL CACHE first
    full_cache_path = DATA_DIR / "wc_full_cache.json"
    normalized_cache_path = DATA_DIR / "processed" / "wc_catalog.json"
    
    all_items = []
    is_normalized = False
    
    if full_cache_path.exists():
        try:
            with open(full_cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                all_items = cache_data.get('products', [])
                is_normalized = False
        except Exception as e:
            print(f"Error reading local WC raw cache: {e}")
    
    # Fallback to normalized catalog if raw cache is missing
    if not all_items and normalized_cache_path.exists():
        try:
            with open(normalized_cache_path, 'r', encoding='utf-8') as f:
                all_items = json.load(f)
                is_normalized = True
        except Exception as e:
            print(f"Error reading normalized WC catalog: {e}")

    if all_items:
        try:
            # Filter in Python
            filtered_items = []
            
            # Resolve Brand ID if needed for raw items
            target_brand_id = None
            if brand and brand != 'all':
                if brand.isdigit():
                    target_brand_id = int(brand)
                else:
                    brand_id_str = get_brand_id_by_name(brand)
                    if brand_id_str:
                        target_brand_id = int(brand_id_str)
            
            brand_query_lower = brand.lower() if brand and brand != 'all' else None

            # Filtering Loop
            for p in all_items:
                # 1. Search Query
                if query:
                    q_str = query.lower()
                    if q_str not in p.get('name', '').lower() and q_str not in p.get('sku', '').lower():
                        continue
                
                # 2. Category (Basic check, might need strict ID check depending on data)
                if category and category != 'all':
                    # Support normalized data that has 'category' as a string field
                    p_category_str = p.get('category', '').lower()
                    category_lower = category.lower()
                    
                    # If category is a numeric ID, try to resolve it to a name
                    category_name_for_matching = category_lower
                    if category.isdigit():
                        # Lookup category name from WC categories cache
                        wc_cats = fetch_wc_categories()  # Uses cache
                        for wc_cat in wc_cats:
                            if str(wc_cat.get('id')) == category:
                                category_name_for_matching = wc_cat.get('name', '').lower()
                                break
                    
                    # First try to match against the normalized 'category' string
                    if p_category_str and category_name_for_matching in p_category_str:
                        pass  # Match found, continue processing
                    else:
                        # Check if category ID, Slug, or Name matches in categories array
                        # p['categories'] is list of dicts {id, name, slug}
                        cats = p.get('categories', [])
                        match = False
                        for c in cats:
                            if (str(c.get('id')) == category or 
                                c.get('slug') == category or
                                c.get('name', '').lower() == category_name_for_matching):
                                match = True
                                break
                        if not match:
                            continue

                # 3. Brand
                if brand and brand != 'all':
                    # Support both raw WooCommerce 'brands' field and normalized 'brand' field
                    p_brands = p.get('brands', [])
                    p_brand_name = p.get('brand', '') # from normalized data
                    
                    found_brand = False
                    if target_brand_id and any(b.get('id') == target_brand_id for b in p_brands):
                         found_brand = True
                    elif brand_query_lower and p_brand_name.lower() == brand_query_lower:
                         found_brand = True
                    # Also check if brand name matches in brands list
                    elif brand_query_lower and any(b.get('name', '').lower() == brand_query_lower for b in p_brands):
                         found_brand = True
                         
                    if not found_brand:
                        continue
                
                if is_normalized:
                    filtered_items.append(p)
                else:
                    filtered_items.append(normalize_wc_product(p))
            
            # Sorting
            if sort:
                if sort == 'price_asc':
                    filtered_items.sort(key=lambda x: float(x.get('parameters', {}).get('Цена', '0').replace(' EUR', '') or 0))
                elif sort == 'price_desc':
                    filtered_items.sort(key=lambda x: float(x.get('parameters', {}).get('Цена', '0').replace(' EUR', '') or 0), reverse=True)
                elif sort == 'date_desc':
                    pass # Assuming already sorted by date or complex logic needed
            
            # Pagination
            total_items = len(filtered_items)
            start = (page - 1) * limit
            end = start + limit
            page_slice = filtered_items[start:end]
            
            return page_slice, total_items

        except Exception as e:
            print(f"Error reading local WC cache: {e}. Falling back to API.")

    # FALLBACK TO REMOTE API (Old Logic)
    
    if query:
        params["search"] = query
    
    if category and category != 'all':
        params["category"] = category

    if brand and brand != 'all':
        # Resolve brand ID
        target_brand_id = None
        if brand.isdigit():
             target_brand_id = int(brand)
        else:
             brand_id_str = get_brand_id_by_name(brand)
             if brand_id_str:
                 target_brand_id = int(brand_id_str)
        
        if target_brand_id:
             try:
                 params["pwb-brand"] = target_brand_id 
             except: pass

    if sort:
        if sort == 'price_asc':
            params["orderby"] = "price"
            params["order"] = "asc"
        elif sort == 'price_desc':
            params["orderby"] = "price"
            params["order"] = "desc"
        elif sort == 'date_desc':
            params["orderby"] = "date"
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
            # Cache the remote page result
            _save_to_cache(cache_key, (products, total))
            return products, total
        
        print(f"WC API Error: {response.status_code}")
        return [], 0
    except Exception as e:
        print(f"WC API Exception: {e}")
        return [], 0

def fetch_all_wc_products() -> List[dict]:
    """Fetch ALL products from WooCommerce by iterating through all pages.
    Used for syncing to ChromaDB embeddings.
    """
    all_products = []
    page = 1
    per_page = 100  # Max allowed by WooCommerce
    
    auth = _get_auth()
    if not auth:
        print("WooCommerce credentials not configured")
        return []
    
    while True:
        params = {
            "per_page": per_page,
            "page": page,
            "status": "publish"
        }
        
        try:
            response = requests.get(
                f"{BASE_URL}/products",
                auth=auth,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"WC API Error on page {page}: {response.status_code}")
                break
                
            products = response.json()
            if not products:
                break  # No more products
                
            normalized = [normalize_wc_product(p) for p in products]
            all_products.extend(normalized)
            
            print(f"Fetched page {page}: {len(products)} products (total: {len(all_products)})")
            
            # Check if we've reached the last page
            total_pages = int(response.headers.get('X-WP-TotalPages', 1))
            if page >= total_pages:
                break
                
            page += 1
            
        except Exception as e:
            print(f"WC API Exception on page {page}: {e}")
            break
    
    print(f"Total WooCommerce products fetched: {len(all_products)}")
    return all_products

def get_active_wc_brands() -> List[dict]:
    """Get brands that actually exist in the cached products."""
    full_cache_path = DATA_DIR / "wc_full_cache.json"
    if full_cache_path.exists():
        try:
            with open(full_cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                products = data.get('products', [])
            
            active_brands = set()
            for p in products:
                # Check 'brands' list
                for b in p.get('brands', []):
                    if b.get('name'):
                        active_brands.add(b['name'])
                
                # Also check attributes if brands are missing there
                if not p.get('brands') and p.get('attributes'):
                     for a in p['attributes']:
                         if 'brand' in a.get('name', '').lower():
                             for opt in a.get('options', []):
                                 active_brands.add(opt)

            return [{"id": b, "name": b} for b in sorted(list(active_brands))]
        except Exception as e:
            print(f"Error loading active brands from cache: {e}")
            
    # Fallback to fetching all definitions if cache missing
    return fetch_wc_brands()

def fetch_wc_brands() -> List[dict]:
    """Fetch distinct brands from WooCommerce pwb-brand taxonomy with caching."""
    cache_key = "wc_brands_list_full"
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
        
        all_brands = []
        page = 1
        per_page = 100
        
        while True:
            resp = requests.get(
                wp_url,
                auth=auth,
                params={"per_page": per_page, "page": page, "hide_empty": True},
                timeout=10
            )
            
            if resp.status_code != 200:
                print(f"Error fetching brands page {page}: {resp.status_code}")
                break
                
            data = resp.json()
            if not data:
                break
                
            brands_page = [{"id": str(b["id"]), "name": b["name"]} for b in data]
            all_brands.extend(brands_page)
            
            # Check pagination headers
            total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
            if page >= total_pages:
                break
            page += 1

        _save_to_cache(cache_key, all_brands)
        return all_brands
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

def fetch_wc_categories(brand: Optional[str] = None) -> List[dict]:
    """Fetch categories from WooCommerce API with caching."""
    if brand and brand != 'all':
        # If brand is specified, extract categories from products associated with this brand
        from .woocommerce import fetch_wc_products
        # We fetch a large number of products for this brand to get an accurate category list
        # Using limit=100 as a reasonable upper bound for category extraction
        products, _ = fetch_wc_products(page=1, limit=100, brand=brand)
        
        unique_brand_cats = {}
        for p in products:
            cat_name = p.get('category')
            if cat_name:
                # Extract parent category (before " / ") if present
                if ' / ' in cat_name:
                    parent_cat = cat_name.split(' / ')[0].strip()
                else:
                    parent_cat = cat_name
                # Use parent category name as ID for UI consistency
                if parent_cat not in unique_brand_cats:
                    unique_brand_cats[parent_cat] = {"id": parent_cat, "name": parent_cat}
        
        return sorted(list(unique_brand_cats.values()), key=lambda x: x['name'])

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
