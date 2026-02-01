
import json
import sys
import time
import requests
import io
from pathlib import Path
from typing import Dict, List, Optional

import google.generativeai as genai
import PIL.Image
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import GEMINI_API_KEY, DATA_DIR

console = Console()

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY, transport="rest")
# Using the verified preview model
MODEL_NAME = "gemini-3-flash-preview" 

VISUAL_PROMPT = """
Analyze this product image for a furniture catalog.
Describe the visual characteristics in Russian. Focus on:
1. Shape (geometry, silhouette, unusual forms).
2. Material appearance (texture, finish, gloss vs matte).
3. Color nuances (not just "green", but "olive green", "emerald").
4. Style (minimalist, industrial, classic, etc.).
5. Distinctive features (legs, handles, patterns).

Keep the description concise (2-3 sentences).
Return ONLY the raw text description. Do not use Markdown formatting or prefixes like "Description:".
"""

def fetch_image(url: str) -> Optional[PIL.Image.Image]:
    """Fetch image from URL."""
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            img = PIL.Image.open(io.BytesIO(resp.content))
            return img
    except Exception:
        pass
    return None

def main():
    catalog_path = DATA_DIR / "processed" / "full_catalog.json"
    output_path = DATA_DIR / "processed" / "full_catalog_enriched.json"
    
    if not catalog_path.exists():
        console.print(f"[red]Catalog not found at {catalog_path}[/red]")
        return

    with open(catalog_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    console.print(f"[bold]Starting visual enrichment for {len(products)} products...[/bold]")
    
    model = genai.GenerativeModel(MODEL_NAME)
    
    # Check if we have partial progress or existing enriched file
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            enriched_products = json.load(f)
            # Create a map of already enriched slugs
            enriched_map = {p['slug']: p.get('visual_description') for p in enriched_products if p.get('visual_description')}
            console.print(f"[yellow]Found existing enriched catalog with {len(enriched_map)} descriptions.[/yellow]")
    else:
        enriched_map = {}

    updated_products = []
    
    # We will process in batches to save periodically
    
    # Simple loop without Rich for better logging
    total = len(products)
    processed = 0
    enriched_count = 0
    
    print(f"Starting loop for {total} products...")
    
    for i, product in enumerate(products):
        slug = product.get('slug')
        product_copy = product.copy()
        
        # Skip if already enriched
        if slug in enriched_map:
            product_copy['visual_description'] = enriched_map[slug]
            updated_products.append(product_copy)
            processed += 1
            if processed % 10 == 0:
                print(f"Skipped {processed}/{total} (already enriched)")
            continue
        
        # Get Image
        image_url = product.get('main_image') or (product.get('images', [])[0] if product.get('images') else None)
        
        if not image_url:
            print(f"No image for {slug}, skipping")
            updated_products.append(product_copy)
            processed += 1
            continue
        
        # Process with Gemini
        try:
            print(f"Enriching {slug}...")
            img = fetch_image(image_url)
            if img:
                # Rate limiting protection
                time.sleep(1) 
                
                response = model.generate_content([VISUAL_PROMPT, img])
                description = response.text.strip()
                product_copy['visual_description'] = description
                
                # Update map
                enriched_map[slug] = description
                enriched_count += 1
                print(f"SUCCESS: {slug} -> {description[:50]}...")
            else:
                print(f"Failed to fetch image for {slug}: {image_url}")
                pass
        except Exception as e:
            print(f"Error analyzing {slug}: {e}")
            time.sleep(2)
        
        updated_products.append(product_copy)
        processed += 1
        
        # Save periodically (every 10 items)
        if i % 10 == 0:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(updated_products + products[i+1:], f, ensure_ascii=False, indent=2) 

    # Final save
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(updated_products, f, ensure_ascii=False, indent=2)
    
    # Overwrite the main catalog?
    # For safety, let's keep them separate for now or ask user. 
    # But implementation plan said "merge logic".
    # Let's overwrite full_catalog.json with the enriched version as the final step.
    console.print("[bold green]Enrichment complete![/bold green]")
    console.print(f"Saved to {output_path}")
    
    # Replacing the original file
    import shutil
    shutil.copy(output_path, catalog_path)
    console.print(f"[bold]Overwrote {catalog_path} with enriched data.[/bold]")

if __name__ == "__main__":
    main()
