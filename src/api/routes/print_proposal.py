
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import json

from config.settings import DATA_DIR
from src.storage.project_storage import ProjectStorage

router = APIRouter()

DB_FILE = DATA_DIR / "user_data.db"
storage = ProjectStorage(DB_FILE)

# Jinja2 setup
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

# Load product catalog for enrichment
CATALOG_PATH = DATA_DIR / "processed" / "full_catalog.json"


def get_product_details(slug: str) -> dict:
    """Get full product details from catalog"""
    if not CATALOG_PATH.exists():
        return {}
    
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    for product in catalog:
        if product.get('slug') == slug:
            return product
    return {}


@router.get("/{project_slug}", response_class=HTMLResponse)
async def get_print_proposal(project_slug: str):
    """
    Generate printable commercial proposal HTML for a project.
    Open this page and use Ctrl+P / Cmd+P to export as PDF.
    """
    project = storage.get_project_by_slug(project_slug)
    
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")
    
    # Enrich project items with full product details
    enriched_items = []
    for item in project.get('items', []):
        slug = item.get('slug')
        if slug:
            details = get_product_details(slug)
            if details:
                # Merge item overrides with catalog details
                enriched = {**details, **item}
                enriched_items.append(enriched)
            else:
                enriched_items.append(item)
        else:
            enriched_items.append(item)
    
    # Paginate: 2 products per page
    items_per_page = 2
    pages = []
    for i in range(0, len(enriched_items), items_per_page):
        pages.append(enriched_items[i:i + items_per_page])
    
    # If no items, create at least one empty page
    if not pages:
        pages = [[]]
    
    # Render template
    template = jinja_env.get_template("commercial_proposal.html")
    html = template.render(
        project_name=project['name'],
        pages=pages,
        total_items=len(enriched_items)
    )
    
    return HTMLResponse(content=html)
