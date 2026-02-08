
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, Depends
from fastapi.responses import Response
import httpx
from typing import List, Optional
import json
import os
from config.settings import DATA_DIR, PRODUCTS_JSON_PATH, HTTPX_VERIFY_SSL
from src.ai.embeddings import BrickEmbeddings
from pydantic import BaseModel
from slugify import slugify
import ipaddress
import socket
from urllib.parse import urlparse
from src.api.auth.jwt import get_current_user

router = APIRouter()

CUSTOM_CATALOGS_DIR = DATA_DIR / "custom_catalogs"
CUSTOM_CATALOGS_DIR.mkdir(parents=True, exist_ok=True)
SOURCES_CONFIG_PATH = DATA_DIR / "sources_config.json"

# Shared sources accessible by all users
SHARED_SOURCES = {"catalog", "woocommerce"}

def _is_public_hostname(hostname: str) -> bool:
    h = hostname.strip().strip(".").lower()
    if not h:
        return False
    if h == "localhost" or h.endswith(".localhost"):
        return False
    try:
        addr_infos = socket.getaddrinfo(h, None)
    except Exception:
        return False
    for info in addr_infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True

def _validate_external_http_url(url: str) -> str:
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Invalid URL protocol")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Invalid URL")
    hostname = parsed.hostname
    if not hostname or not _is_public_hostname(hostname):
        raise HTTPException(status_code=400, detail="Invalid URL host")
    return url

def get_sources_config():
    if not SOURCES_CONFIG_PATH.exists():
        return {}
    try:
        with open(SOURCES_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_sources_config(config):
    with open(SOURCES_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

class ImportStatus(BaseModel):
    status: str
    message: str
    source_id: Optional[str] = None

# Load catalog data once
def get_catalog():
    # 1. Custom catalogs first (PRIORITY)
    paths = list(CUSTOM_CATALOGS_DIR.glob("*.json"))
    
    # 2. Standard paths
    paths.extend([
        PRODUCTS_JSON_PATH,
        DATA_DIR / "processed" / "full_catalog.json"
    ])
    
    all_data = []
    seen_slugs = set()
    
    from slugify import slugify
    import re

    def parse_complex_price(price_str):
        if not price_str or not isinstance(price_str, str):
            return None, None
        
        # Determine currency
        currency = 'RUB'
        if any(euro_sym in price_str.upper() for euro_sym in ['€', 'EUR', 'EURO', 'ЕВРО']):
            currency = 'EUR'
        
        # Extract numbers - handle ranges (take first number)
        # Handles 1 234,56 or 1234.56
        # Matches the first number found including optional decimal part
        match = re.search(r'(\d[\d\s,.]*)', price_str)
        if match:
            val_str = match.group(1)
            # Remove spaces
            val_str = val_str.replace(' ', '').replace('\u00a0', '')
            # If both comma and dot exist, comma is likely decimal if it is after dot, or vice versa.
            # Usually in RU: 1.234,56 -> dot is thousand, comma is decimal
            # For simplicity: if comma is followed by 2 digits at the end, it's decimal.
            if ',' in val_str and '.' in val_str:
                if val_str.find(',') > val_str.find('.'):
                    val_str = val_str.replace('.', '').replace(',', '.')
                else:
                    val_str = val_str.replace(',', '')
            elif ',' in val_str:
                val_str = val_str.replace(',', '.')
            
            try:
                # If there are multiple dots now (e.g. 1.234.56), keep only the last one
                if val_str.count('.') > 1:
                    parts = val_str.split('.')
                    val_str = "".join(parts[:-1]) + "." + parts[-1]
                
                return float(val_str), currency
            except Exception:
                return None, None
        return None, None

    for p in paths:
        if p.exists():
            try:
                # Determine source name from filename
                if p.parent == CUSTOM_CATALOGS_DIR:
                    source_name = p.stem
                elif p.name == "products.json":
                    source_name = "catalog"
                else:
                    source_name = p.stem
                
                with open(p, 'r', encoding='utf-8') as f:
                    batch = json.load(f)
                    if not batch:
                        continue
                    
                    for item in batch:
                        # Normalize slug early for deduplication
                        if 'slug' not in item or not item['slug']:
                            candidate = item.get('name') or item.get('title') or 'unknown-product'
                            item['slug'] = slugify(candidate)
                        
                        if item['slug'] not in seen_slugs:
                            # Attach source info if missing
                            if not item.get('source'):
                                item['source'] = source_name
                            seen_slugs.add(item['slug'])
                            
                            # Normalization: Name and Title
                            if not item.get('title'):
                                item['title'] = item.get('name') or 'unknown-product'
                            if not item.get('name'):
                                item['name'] = item['title']
                                
                            # Normalization: Images
                            if not item.get('main_image'):
                                if item.get('images') and len(item['images']) > 0:
                                    item['main_image'] = item['images'][0]
                            if not item.get('images'):
                                if item.get('main_image'):
                                    item['images'] = [item['main_image']]
                                else:
                                    item['images'] = []
                            
                            # Normalize Price
                            if 'price' in item:
                                if isinstance(item['price'], list):
                                    if len(item['price']) > 0:
                                        item['price'] = item['price'][0]
                                    else:
                                        item['price'] = None
                            
                            # Force currency for specific sources
                            if source_name == 'varaschin' and item.get('price'):
                                item['currency'] = 'EUR'

                            # Normalize Price from parameters (Fallback if price is missing)
                            if not item.get('price') and 'parameters' in item and 'Цена' in item['parameters']:
                                price_val, curr = parse_complex_price(item['parameters']['Цена'])
                                if price_val is not None:
                                    item['price'] = price_val
                                    item['currency'] = curr
                            
                            all_data.append(item)
            except Exception as e:
                print(f"Error loading {p}: {e}")
                continue
            
    return all_data

# Global cache
catalog_data = get_catalog()
catalog_dict = {p['slug']: p for p in catalog_data if p.get('slug')}

# Initialize embeddings for search
embeddings = BrickEmbeddings()

@router.get("/sources/", response_model=List[dict])
async def get_sources(user: Optional[dict] = Depends(get_current_user)):
    """List all available product sources (shared + user's custom)"""
    config = get_sources_config()
    user_id = user.get("id") if user else None
    
    # Shared sources available to all
    sources = [
        {"id": "catalog", "name": config.get("catalog", "Локальный каталог")},
        {"id": "woocommerce", "name": config.get("woocommerce", "de-co-de.ru (WC)")}
    ]
    
    # Custom sources only for authenticated users - only show sources owned by this user
    if user_id:
        for p in CUSTOM_CATALOGS_DIR.glob("*.json"):
            source_id = p.stem
            source_meta = config.get(f"_meta_{source_id}", {})
            source_owner = source_meta.get("user_id")
            
            # Only show source if owner explicitly matches current user
            # Legacy sources (no owner) are hidden to prevent cross-user leakage
            if source_owner == user_id:
                sources.append({"id": source_id, "name": source_meta.get("name", source_id)})
        
    return sources

@router.post("/import/", response_model=ImportStatus)
async def import_catalog(
    file: UploadFile = File(...),
    name: str = Form(...),
    user: dict = Depends(get_current_user)
):
    """Import a new JSON catalog (user-specific)"""
    if not user or not user.get("id"):
        raise HTTPException(status_code=401, detail="Authentication required to import catalogs")
    
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")
    
    from slugify import slugify
    source_id = slugify(name)
    target_path = CUSTOM_CATALOGS_DIR / f"{source_id}.json"
    
    try:
        content = await file.read()
        data = json.loads(content)
        
        # Basic validation: must be a list
        if not isinstance(data, list):
            raise HTTPException(status_code=400, detail="JSON must be an array of products")
            
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Save source metadata with user_id
        config = get_sources_config()
        config[f"_meta_{source_id}"] = {
            "name": name,
            "user_id": user["id"]
        }
        save_sources_config(config)
            
        # 1. Refresh global cache
        global catalog_data, catalog_dict
        catalog_data = get_catalog()
        catalog_dict = {p['slug']: p for p in catalog_data if p.get('slug')}
        
        # 2. Re-index embeddings
        embeddings.index_catalog(products_list=catalog_data, force_reindex=False)
        
        return ImportStatus(status="success", message=f"Каталог '{name}' успешно импортирован", source_id=source_id)
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sources/{source_id}", response_model=ImportStatus)
async def delete_source(source_id: str, user: dict = Depends(get_current_user)):
    """Delete a custom JSON catalog"""
    if not user or not user.get("id"):
        raise HTTPException(status_code=401, detail="Authentication required")
        
    # Protect core sources
    if source_id in ['catalog', 'woocommerce']:
        raise HTTPException(status_code=403, detail="Cannot delete core sources")
    
    # Check ownership for custom catalogs
    config = get_sources_config()
    source_meta = config.get(f"_meta_{source_id}", {})
    source_owner = source_meta.get("user_id")
    
    if source_owner and source_owner != user["id"]:
        raise HTTPException(status_code=403, detail="You do not own this source")

    target_path = CUSTOM_CATALOGS_DIR / f"{source_id}.json"
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    
    try:
        os.remove(target_path)
        
        # Remove from config
        if f"_meta_{source_id}" in config:
            del config[f"_meta_{source_id}"]
        save_sources_config(config)
        
        # 1. Refresh global cache
        global catalog_data, catalog_dict
        catalog_data = get_catalog()
        catalog_dict = {p['slug']: p for p in catalog_data if p.get('slug')}
        
        # 2. Re-index embeddings to remove deleted items
        embeddings.index_catalog(products_list=catalog_data, force_reindex=False)
        
        return ImportStatus(status="success", message=f"Источник '{source_id}' успешно удален", source_id=source_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RenameSourceRequest(BaseModel):
    name: str

@router.put("/sources/{source_id}/rename", response_model=ImportStatus)
async def rename_source(source_id: str, request: RenameSourceRequest, user: dict = Depends(get_current_user)):
    """Rename a custom JSON catalog or core source"""
    if not user or not user.get("id"):
        raise HTTPException(status_code=401, detail="Authentication required")

    # Handle core sources
    if source_id in ['catalog', 'woocommerce']:
        try:
            config = get_sources_config()
            config[source_id] = request.name
            save_sources_config(config)
            return ImportStatus(status="success", message=f"Источник переименован в '{request.name}'", source_id=source_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Check ownership for custom catalogs
    config = get_sources_config()
    source_meta = config.get(f"_meta_{source_id}", {})
    source_owner = source_meta.get("user_id")
    
    if source_owner and source_owner != user["id"]:
        raise HTTPException(status_code=403, detail="You do not own this source")

    current_path = CUSTOM_CATALOGS_DIR / f"{source_id}.json"
    if not current_path.exists():
        raise HTTPException(status_code=404, detail="Source not found")
        
    from slugify import slugify
    new_id = slugify(request.name)
    new_path = CUSTOM_CATALOGS_DIR / f"{new_id}.json"
    
    if new_path.exists() and new_path != current_path:
        raise HTTPException(status_code=400, detail="Source with this name already exists")
        
    try:
        # Rename file
        current_path.rename(new_path)
        
        # Update config metadata
        if f"_meta_{source_id}" in config:
            meta = config.pop(f"_meta_{source_id}")
            meta["name"] = request.name
            config[f"_meta_{new_id}"] = meta
            save_sources_config(config)
        
        # 1. Refresh global cache
        global catalog_data, catalog_dict
        catalog_data = get_catalog()
        catalog_dict = {p['slug']: p for p in catalog_data if p.get('slug')}
        
        embeddings.index_catalog(products_list=catalog_data, force_reindex=False)
        
        return ImportStatus(status="success", message=f"Источник переименован в '{request.name}'", source_id=new_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class UpdatePriceRequest(BaseModel):
    price: float
    currency: str = "EUR"

@router.put("/{slug}/price")
async def update_price(slug: str, request: UpdatePriceRequest, user: dict = Depends(get_current_user)):
    """Update price for a specific product"""
    if not user or not user.get("id"):
        raise HTTPException(status_code=401, detail="Authentication required")

    if slug not in catalog_dict:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = catalog_dict[slug]
    source = product.get('source', 'catalog')
    
    # Ownership check for custom sources
    if source not in ['catalog', 'woocommerce']:
        config = get_sources_config()
        source_meta = config.get(f"_meta_{source}", {})
        source_owner = source_meta.get("user_id")
        if source_owner and source_owner != user["id"]:
            raise HTTPException(status_code=403, detail="You do not own this product's source")
    
    # Identify target file
    target_file = None
    if source == 'catalog':
        target_file = PRODUCTS_JSON_PATH
    elif source == 'woocommerce':
        target_file = DATA_DIR / "processed" / "full_catalog.json"
    else:
        # Custom source
        target_file = CUSTOM_CATALOGS_DIR / f"{source}.json"
        
    if not target_file.exists():
         raise HTTPException(status_code=404, detail=f"Source file not found: {target_file}")
         
    try:
        # Load, Find, Update, Save
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        updated = False
        for item in data:
            # We need to match by slug. 
            # Note: get_catalog() generates slugs on the fly if missing. 
            # So we must replicate slug generation to match? 
            # Ideally the source JSON already has slugs or we match by Title if slug missing in JSON but present in cache.
            # Safe bet: Check if item has slug, if not generate it and compare.
            item_slug = item.get('slug')
            if not item_slug:
                from slugify import slugify
                name = item.get('name') or item.get('title')
                if name:
                    item_slug = slugify(name)
            
            if item_slug == slug:
                item['price'] = request.price
                item['currency'] = request.currency
                # Update in-memory product too
                product['price'] = request.price
                product['currency'] = request.currency
                updated = True
                break
        
        if not updated:
            raise HTTPException(status_code=500, detail="Product found in cache but not in source file")
            
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        # Re-index specific item
        embeddings.index_product(product)
        
        return {"status": "success", "message": "Price updated", "product": product}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{slug}")
async def delete_product(slug: str, user: dict = Depends(get_current_user)):
    """Delete a specific product"""
    if not user or not user.get("id"):
        raise HTTPException(status_code=401, detail="Authentication required")
        
    if slug not in catalog_dict:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = catalog_dict[slug]
    source = product.get('source', 'catalog')
    
    # Ownership check for custom sources
    if source not in ['catalog', 'woocommerce']:
        config = get_sources_config()
        source_meta = config.get(f"_meta_{source}", {})
        source_owner = source_meta.get("user_id")
        if source_owner and source_owner != user["id"]:
            raise HTTPException(status_code=403, detail="You do not own this product's source")
    
    # Identify target file
    target_file = None
    if source == 'catalog':
        target_file = PRODUCTS_JSON_PATH
    elif source == 'woocommerce':
        target_file = DATA_DIR / "processed" / "full_catalog.json"
    else:
        target_file = CUSTOM_CATALOGS_DIR / f"{source}.json"
        
    if not target_file.exists():
         raise HTTPException(status_code=404, detail=f"Source file not found: {target_file}")
         
    try:
        # Load, Find, Remove, Save
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        initial_len = len(data)
        # Filter out the item
        new_data = []
        for item in data:
            item_slug = item.get('slug')
            if not item_slug:
                from slugify import slugify
                name = item.get('name') or item.get('title')
                if name:
                    item_slug = slugify(name)
            
            if item_slug != slug:
                new_data.append(item)
        
        if len(new_data) == initial_len:
             raise HTTPException(status_code=500, detail="Product found in cache but not in source file")
            
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
            
        # Update global cache
        if slug in catalog_dict:
            del catalog_dict[slug]
        
        # Remove from list (inefficient but needed for consistency)
        global catalog_data
        catalog_data = [p for p in catalog_data if p.get('slug') != slug]
            
        # Delete from embeddings
        embeddings.delete_product(slug)
        
        return {"status": "success", "message": "Product deleted"}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=dict)
async def get_products(
    skip: int = 0, 
    limit: int = 20, 
    query: Optional[str] = None,
    color: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    source: Optional[str] = 'catalog',
    sort: Optional[str] = None,
    user: Optional[dict] = Depends(get_current_user)
):
    """
    Get list of products with optional search query and source.
    """
    # Parse sources
    requested_sources = source.split(',') if source else ['catalog']
    
    # Get allowed sources for this user
    allowed_sources_list = await get_sources(user)
    allowed_source_ids = {s['id'] for s in allowed_sources_list}
    
    # Filter requested sources to only include allowed ones
    requested_sources = [s for s in requested_sources if s in allowed_source_ids]
    
    if 'all' in requested_sources or source == 'all':
        requested_sources = list(allowed_source_ids)
        
    wc_products = []
    wc_total = 0

    # 1. Fetch WooCommerce Data if requested
    if 'woocommerce' in requested_sources:
        from src.api.services.woocommerce import fetch_wc_products
        page = (skip // limit) + 1
        wc_products, wc_total = fetch_wc_products(page=page, limit=limit, query=query, category=category, sort=sort, brand=brand)

    # 2. Fetch Local/Custom Catalog Data
    local_candidates = []
    
    # Filter catalog_data by requested sources
    # EXCLUDE 'woocommerce' from local search if we're fetching it from live API
    # This prevents double-counting
    local_sources = [s for s in requested_sources if s != 'woocommerce'] 
    
    if local_sources:
        # Filter by source name
        if 'catalog' in local_sources:
             # 'catalog' usually maps to the core concatenated data or specific files
             # For simplicity, if 'catalog' is in requested_sources, we take items with source 'catalog' or 'products_json'
             relevant_data = [p for p in catalog_data if p.get('source') in local_sources or (p.get('source') == 'products_json' and 'catalog' in local_sources)]
        else:
             relevant_data = [p for p in catalog_data if p.get('source') in local_sources]

        if query:
            # Prioritize text search
            q_lower = query.lower()
            text_matches = []
            
            for p in relevant_data:
                name_match = q_lower in p.get('name', '').lower()
                article_match = q_lower in p.get('article', '').lower()
                if name_match or article_match:
                    text_matches.append(p)
            
            local_candidates = text_matches
            
            # Fallback to semantic search
            if not local_candidates:
                # Note: Embeddings search currently doesn't filter by source in the vector query itself
                # until we update the index with metadata. Let's do a post-filter for now.
                results = embeddings.search(query, n_results=500) 
                for r in results:
                    product = catalog_dict.get(r['slug'])
                    if product and (product.get('source') in local_sources or (product.get('source') == 'products_json' and 'catalog' in local_sources)):
                        local_candidates.append(product)
        else:
            local_candidates = relevant_data

        # Apply Color Filter
        if color:
            color_lower = color.lower()
            local_candidates = [
                p for p in local_candidates 
                if p.get('color') and p['color'].get('base_color') and p['color']['base_color'].lower() == color_lower
            ]

        # Apply Category Filter
        if category and category != 'all':
            cat_map = {
                "41": "Освещение",
                "15": "Мебель",
                "92": "Диваны",
                "51": "Кресла",
                "172": "Столики",
                "2468": "Ковры",
                "71": "Аксессуары и декор"
            }
            target_cat = cat_map.get(str(category), str(category)).lower()
            
            filtered = []
            for p in local_candidates:
                p_cat = p.get('category', '').lower()
                if not p_cat and p.get('categories'):
                     p_cat = str(p.get('categories')).lower()
                
                if target_cat in p_cat:
                    filtered.append(p)
            local_candidates = filtered

        # Apply Brand Filter
        if brand and brand != 'all':
            brand_lower = brand.lower()
            local_candidates = [p for p in local_candidates if p.get('brand', '').lower() == brand_lower]

    # Calculate total counts
    total_local = len(local_candidates)
    total_wc = wc_total if 'woocommerce' in requested_sources else 0
    total_count = total_local + total_wc

    final_results = []
    
    # 3. Assemble current page items
    if 'woocommerce' in requested_sources:
        final_results.extend(wc_products)
        
    if local_sources:
        # If we have both live and local items for the same source (like WooCommerce),
        # we should prioritize live but include local if live is empty or for items not in live.
        # Deduplication by slug:
        seen_slugs = {p['slug'] for p in final_results if p.get('slug')}
        
        local_subset = []
        for p in local_candidates:
            if p.get('slug') not in seen_slugs:
                local_subset.append(p)
                seen_slugs.add(p['slug'])
        
        # Apply pagination to the local part if needed or to the combined set
        # For simplicity, if we have live results, we append local ones up to the limit
        # BUT this might break pagination logic strictly. 
        # Better: if live results exist, they are already paginated. 
        # If we want a seamless merged list, we'd need to fetch ALL live and ALL local then paginate.
        # Given live API is usually used for search/sort, sticking to this:
        
        start = max(0, skip - total_wc) if 'woocommerce' in requested_sources else skip
        count_needed = limit - len(final_results)
        
        if count_needed > 0:
            final_results.extend(local_subset[start : start + count_needed])

    # Global sort for the current page
    def parse_price(p):
        try:
            val = p.get('parameters', {}).get('Цена', '0')
            clean = val.replace('₽', '').replace('EUR', '').replace(' ', '').replace(',', '.')
            return float(clean)
        except Exception:
            return 0

    if sort:
        reverse = sort == 'price_desc'
        final_results.sort(key=parse_price, reverse=reverse)
    
    # Enrich for frontend
    for p in final_results:
        if 'attributes' not in p and 'parameters' in p:
            p['attributes'] = {k: v for k, v in p['parameters'].items() if k != 'Цена'}
        
    return {
        "items": final_results,
        "total": total_count
    }

@router.get("/brands/", response_model=List[dict])
async def get_brands(source: str = 'catalog'):
    all_brands = set()
    requested_sources = source.split(',') if source else ['catalog']
    
    # 1. WooCommerce Brands
    if 'woocommerce' in requested_sources or 'all' in requested_sources:
        from src.api.services.woocommerce import get_active_wc_brands
        wc_brands = get_active_wc_brands()
        # Use Name as ID for unification
        for b in wc_brands:
            if b.get('name'):
                all_brands.add(b['name'])

    # 2. Local/Custom Catalog Brands
    # If source is specific custom catalog, filter by it. 
    # If 'catalog' or 'all' is requested, include all local brands.
    local_needed = False
    if 'all' in requested_sources or 'catalog' in requested_sources:
        local_needed = True
    else:
        # Check if any custom source is requested
        # For simplicity, if any non-wc source requested, we scan local cache
        if any(s != 'woocommerce' for s in requested_sources):
             local_needed = True

    if local_needed:
        # Strict filtering matching get_products logic
        target_sources = set(requested_sources)
        blacklist = {'DE-CO-DE', 'CATALOG', 'UNKNOWN', 'NONE'}
        
        for p in catalog_data:
            p_source = p.get('source', 'catalog')
            
            should_include = False
            if 'all' in target_sources:
                should_include = True
            elif p_source in target_sources:
                should_include = True
            # Handle implicit 'catalog' source mapping
            elif 'catalog' in target_sources and (p_source == 'products_json' or p_source == 'catalog'):
                should_include = True
                
            if should_include:
                brand = p.get('brand')
                if brand and brand.strip():
                    if brand.strip().upper() not in blacklist:
                        all_brands.add(brand.strip())

    sorted_brands = sorted(list(all_brands))
    return [{"id": b, "name": b} for b in sorted_brands]

@router.get("/categories/", response_model=List[dict])
async def get_categories(source: str = 'catalog'):
    if source == 'woocommerce':
        from src.api.services.woocommerce import fetch_wc_categories
        cats = fetch_wc_categories()
        return [{"id": "all", "name": "Все категории"}] + cats

    unique_cats = set()
    for p in catalog_data:
        c = p.get('category')
        if c:
            unique_cats.add(c)
    
    sorted_cats = sorted(list(unique_cats))
    res = [{"id": "all", "name": "Все категории"}]
    for c in sorted_cats:
        res.append({"id": c, "name": c})
    return res

@router.get("/{slug}/", response_model=dict)
async def get_product(slug: str):
    product = catalog_dict.get(slug)
    if product:
        product_copy = product.copy()
        if 'source' not in product_copy:
            product_copy['source'] = 'catalog'
        if 'parameters' in product_copy and 'attributes' not in product_copy:
             product_copy['attributes'] = {k: v for k, v in product_copy['parameters'].items() if k != 'Цена'}
        return product_copy
    
    from src.api.services.woocommerce import get_wc_product_by_slug
    product = get_wc_product_by_slug(slug)
    if product:
        return product
        
    raise HTTPException(status_code=404, detail="Product not found")
@router.get("/proxy-image")
async def proxy_image(url: str = Query(..., description="The URL of the external image")):
    """
    Proxy an external image URL to bypass regional restrictions or CORS.
    """
    _validate_external_http_url(url)
        
    try:
        max_bytes = 8 * 1024 * 1024
        timeout = httpx.Timeout(10.0, connect=5.0)
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, verify=HTTPX_VERIFY_SSL) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    raise HTTPException(status_code=400, detail="URL is not an image")
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_bytes:
                    raise HTTPException(status_code=413, detail="Image too large")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > max_bytes:
                        raise HTTPException(status_code=413, detail="Image too large")
                return Response(
                    content=bytes(content),
                    media_type=content_type,
                    headers={
                        "Cache-Control": "public, max-age=31536000",
                        "Access-Control-Allow-Origin": "*"
                    }
                )
    except Exception as e:
        print(f"Error proxying image {url}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")

class UpdateImageRequest(BaseModel):
    image_url: str

@router.put("/{slug}/image")
async def update_product_image(slug: str, request: UpdateImageRequest, user: dict = Depends(get_current_user)):
    """Update a product's image"""
    if not user or not user.get("id"):
        raise HTTPException(status_code=401, detail="Authentication required")

    new_image_url = request.image_url
    
    # Validation loop similar to price update
    product = catalog_dict.get(slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    source_id = product.get('source', 'catalog')
    
    # Ownership check for custom sources
    if source_id not in ['catalog', 'woocommerce']:
        config = get_sources_config()
        source_meta = config.get(f"_meta_{source_id}", {})
        source_owner = source_meta.get("user_id")
        if source_owner and source_owner != user["id"]:
            raise HTTPException(status_code=403, detail="You do not own this product's source")
    
    # Determine file path
    file_path = None
    if source_id == 'catalog':
        file_path = PRODUCTS_JSON_PATH
    elif source_id == 'woocommerce':
        # Allow editing WooCommerce cache
        file_path = DATA_DIR / "processed" / "full_catalog.json"
    elif source_id == 'custom_links':
        file_path = CUSTOM_CATALOGS_DIR / "custom_links.json"
    else:
        file_path = CUSTOM_CATALOGS_DIR / f"{source_id}.json"
    
    if not file_path or not file_path.exists():
         raise HTTPException(status_code=404, detail="Source file not found")

    try:
        # Load, find, update, save
        print(f"[DEBUG update_image] Looking for slug='{slug}' in source_id='{source_id}' file='{file_path}'")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        updated = False
        target_item = None
        
        # Handle list vs dict (links)
        items_list = data if isinstance(data, list) else data.get("items", [])
        print(f"[DEBUG update_image] items_list has {len(items_list)} items")
            
        for item in items_list:
            # Match by slug (direct match)
            item_slug = item.get('slug', '') or ''
            
            # Match by generated slug from title
            title_slug = slugify(item.get('title', '')) if item.get('title') else ''
            
            # Match by generated slug from name (catalog_dict uses this)
            name_slug = slugify(item.get('name', '')) if item.get('name') else ''
            
            # Match by article number
            item_article = str(item.get('article', '')).lower().strip()
            slug_lower = slug.lower()
            
            # Check all possible matches
            if (item_slug == slug or 
                title_slug == slug or
                name_slug == slug or
                (item_article and item_article == slug_lower) or
                (item_article and slug_lower.endswith(item_article))):
                # UPDATE LOGIC
                item['main_image'] = new_image_url
                if 'images' not in item or not isinstance(item['images'], list):
                    item['images'] = []
                # Prepend to images if not exists
                if new_image_url not in item['images']:
                    item['images'].insert(0, new_image_url)
                
                target_item = item
                updated = True
                break
        
        if updated:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Update global cache
            if target_item:
                product['main_image'] = new_image_url
                product['images'] = target_item['images']
            
            # Re-index
            try:
                # We need to reconstruct the search text for this item
                # reusing logic from index_catalog is hard without refactor, 
                # so we will just re-add this single item using add_texts logic
                # But embeddings.add_texts expects list of (text, metadata).
                # Simplified: just update embeddings? Actually it's better to implement index_product in embeddings.
                # For now, we accept that image change doesn't drastically change vector unless using detailed captioning.
                # But to be safe, let's try to update if possible.
                # Since we don't have a clean single-item indexer exposed, we skip vector update for image change
                # primarily because image URL change rarely affects semantic text search unless we use vision-to-text.
                pass 
            except Exception as ex:
                print(f"Failed to re-index: {ex}")

            return {"status": "success", "image_url": new_image_url}
        else:
             raise HTTPException(status_code=404, detail="Product not found in source file")

    except Exception as e:
        print(f"Error updating image: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update image: {str(e)}")
