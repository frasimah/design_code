
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import json
from pathlib import Path
from config.settings import DATA_DIR
from src.ai.embeddings import BrickEmbeddings

router = APIRouter()

# Load catalog data once
def get_catalog():
    catalog_path = DATA_DIR / "processed" / "full_catalog.json"
    if not catalog_path.exists():
        return []
    with open(catalog_path, 'r', encoding='utf-8') as f:
        return json.load(f)

catalog_data = get_catalog()
catalog_dict = {p['slug']: p for p in catalog_data}

# Initialize embeddings for search
embeddings = BrickEmbeddings()

@router.get("/", response_model=List[dict])
async def get_products(
    skip: int = 0, 
    limit: int = 1000, 
    query: Optional[str] = None
):
    """
    Get list of products with optional search query.
    """
    if query:
        # Prioritize text search (Name or Article)
        q_lower = query.lower()
        text_matches = []
        
        for p in catalog_data:
            name_match = q_lower in p.get('name', '').lower()
            article_match = q_lower in p.get('article', '').lower()
            if name_match or article_match:
                text_matches.append(p)
        
        # If we have exact/substring matches, return them
        if text_matches:
            return text_matches
            
        # Fallback to semantic search if no text matches
        results = embeddings.search(query, n_results=limit)
        products = []
        for r in results:
            product = catalog_dict.get(r['slug'])
            if product:
                products.append(product)
        return products
    
    # Return paginated list
    return catalog_data[skip : skip + limit]

@router.get("/{slug}", response_model=dict)
async def get_product(slug: str):
    """
    Get detailed product information by slug.
    """
    product = catalog_dict.get(slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
