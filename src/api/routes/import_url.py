
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import re
from typing import Optional, List, Dict

from config.settings import GEMINI_API_KEY, HTTPX_VERIFY_SSL
from src.api.routes.products import CUSTOM_CATALOGS_DIR, embeddings
import ipaddress
import socket
from urllib.parse import urlparse

# Import configured genai from consultant or configure strictly here
# We'll configure locally to be safe, assuming key is loaded
genai.configure(api_key=GEMINI_API_KEY, transport="rest")

router = APIRouter()

class ImportUrlRequest(BaseModel):
    url: str
    price_instruction: Optional[str] = None

class ProductImportResult(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "EUR"
    images: List[str] = []
    brand: Optional[str] = None
    materials: List[str] = []
    dimensions: Optional[str] = None
    attributes: Dict[str, str] = {}
    
def clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove scripts, styles
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()
        
    # Get text
    text = soup.get_text(separator=' ', strip=True)
    
    # Get structured data if mostly
    # Try to extract meta OG tags for image and title
    title = soup.title.string if soup.title else ""
    og_image = soup.find("meta", property="og:image")
    main_image = og_image["content"] if og_image else ""
    
    return f"Title: {title}\nMain Image: {main_image}\nContent: {text[:15000]}" # Limit context

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

@router.post("/parse/", response_model=ProductImportResult)
async def parse_url(request: ImportUrlRequest):
    print(f"Parsing URL: {request.url} with instruction: {request.price_instruction}")
    
    try:
        _validate_external_http_url(request.url)

        # 1. Fetch
        max_bytes = 2 * 1024 * 1024
        timeout = httpx.Timeout(20.0, connect=5.0)
        async with httpx.AsyncClient(follow_redirects=True, verify=HTTPX_VERIFY_SSL, timeout=timeout) as client:
            # Fake user agent to avoid basic blocking
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with client.stream("GET", request.url, headers=headers) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if content_type and not content_type.startswith("text/") and "html" not in content_type:
                    raise HTTPException(status_code=400, detail="Unsupported content type")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > max_bytes:
                        raise HTTPException(status_code=413, detail="Page content too large")
                encoding = response.encoding or "utf-8"
                html_content = bytes(content).decode(encoding, errors="replace")
            
        # 2. Extract Text
        context = clean_html(html_content)
        
        # 3. LLM Parsing
        # User asked for gemini-3-flash-preview specifically
        model = genai.GenerativeModel("gemini-3-flash-preview")
        
        prompt = f"""
        You are an expert scraper. Extract product details from the text below into a JSON object.
        
        USER PRICE INSTRUCTION: "{request.price_instruction if request.price_instruction else 'None'}"
        
        LOGIC FOR PRICE:
        1. Find the base price on the page (in original currency).
        2. If User Price Instruction is present:
           - If it is a FORMULA (e.g. "+20%", "-10%", "*1.2", "20%", "+ 1000 EUR"): Apply this mathematical operation to the base price found on page.
           - If it is a FIXED VALUE (e.g. "3000", "500 EUR", "Cover Price"): Use this exact value as the price, ignoring the page price.
        3. Convert currency to EUR if possible, or keep original.
        
        SCHEMA:
        {{
            "slug": "unique-slug-based-on-name",
            "name": "Product Name",
            "description": "Short description (Russian language)",
            "price": 123.45 (number or null),
            "currency": "EUR" or "USD" or "RUB",
            "brand": "Brand Name",
            "dimensions": "WxHxD cm string e.g. 120x60x40 cm",
            "materials": ["Material 1", "Material 2"],
            "images": ["url1"] (Include the main image from metadata if found, try to find high res urls in text if possible),
            "attributes": {{ "Key": "Value", "Light Source": "LED", ... }} (Extract ALL technical specs found on page)
        }}
        
        Use Russian for Name and Description. Keys in attributes can be translated to Russian if possible.
        
        DATA:
        {context}
        """
        
        result = model.generate_content(prompt)
        text = result.text
        
        # Extract JSON
        json_match = re.search(r'```json\s*({.*?})\s*```', text, re.DOTALL)
        if not json_match:
             json_match = re.search(r'```\s*({.*?})\s*```', text, re.DOTALL)
             
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            # Fallback plain JSON parsing attempt
            try:
                data = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                raise HTTPException(status_code=500, detail="Failed to parse AI response to JSON")

        # --- PERSISTENCE LOGIC START ---
        # Assign persistent source
        data['source'] = 'custom_links'
        
        # Ensure ID/Slug uniqueness
        if not data.get('slug'):
            from slugify import slugify
            data['slug'] = slugify(data.get('name', 'unknown-product'))
        
        # Load existing custom links or create new list
        custom_links_path = CUSTOM_CATALOGS_DIR / "custom_links.json"
        existing_products = []
        if custom_links_path.exists():
            try:
                with open(custom_links_path, 'r', encoding='utf-8') as f:
                    existing_products = json.load(f)
            except Exception as e:
                print(f"Warning: Could not read existing custom_links.json: {e}")
        
        # Dedup: Remove existing item with same slug if it exists (update)
        existing_products = [p for p in existing_products if p.get('slug') != data['slug']]
        existing_products.append(data)
        
        # Save back
        with open(custom_links_path, 'w', encoding='utf-8') as f:
            json.dump(existing_products, f, ensure_ascii=False, indent=2)
            
        print(f"Saved product {data['slug']} to custom_links.json")
        
        # Trigger re-index for this item
        try:
            embeddings.index_catalog(products_list=[data])
            print(f"Indexed product {data['slug']}")
        except Exception as e:
            print(f"Error indexing product {data['slug']}: {e}")

        # Note: In-memory global catalog update is skipped for now, 
        # relying on clients to re-fetch headers or data if needed.
        # Chat RAG uses embeddings directly so it will find it.
        # --- PERSISTENCE LOGIC END ---

        return data

    except Exception as e:
        print(f"Error parsing URL: {e}")
        raise HTTPException(status_code=400, detail=str(e))
