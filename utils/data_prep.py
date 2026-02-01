import json
import os
import re

def clean_text(text):
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Normalize whitespace
    text = " ".join(text.split())
    return text

def format_product_for_rag(product):
    """
    Converts a product dictionary into a structured text format suitable for LLM indexing.
    """
    lines = []
    
    # Basic Info
    name = product.get('title') or product.get('name') or "Без названия"
    lines.append(f"Товар: {name}")
    
    brand = product.get('brand')
    if brand:
        lines.append(f"Бренд: {brand}")
        
    # Price
    params = product.get('parameters', {})
    price = params.get('Цена') or params.get('Price')
    if price:
        lines.append(f"Цена: {price}")
        
    # Article/SKU
    article = params.get('Артикул') or product.get('article')
    if article:
        lines.append(f"Артикул: {article}")
        
    # Categories
    categories = product.get('categories')
    if categories:
        if isinstance(categories, list):
            lines.append(f"Категории: {', '.join(categories)}")
        else:
            lines.append(f"Категория: {categories}")

    # Description
    desc = product.get('description')
    if desc:
        clean_desc = clean_text(desc)
        if clean_desc:
            lines.append(f"Описание: {clean_desc}")
            
    # Parameters (Dimensions, Material, etc.)
    # We iterate over the 'parameters' dict to catch everything else
    useful_params = []
    skip_keys = ['Цена', 'Price', 'Артикул', 'Article']
    
    for k, v in params.items():
        if k not in skip_keys and v:
            useful_params.append(f"{k}: {v}")
            
    if useful_params:
        lines.append("Характеристики:")
        lines.extend([f"- {p}" for p in useful_params])

    # Available formats (from WooCommerce normalization)
    formats = product.get('available_formats')
    if formats and isinstance(formats, list):
        lines.append("Доступные форматы:")
        for fmt in formats:
            fname = fmt.get('name')
            fdims = fmt.get('dimensions')
            if fname:
                line = f"- {fname}"
                if fdims:
                    line += f" ({fdims})"
                lines.append(line)

    lines.append(f"Slug: {product.get('slug')}")
    
    return "\n".join(lines)

def process_products(json_path, output_dir):
    """
    Reads products.json and creates text files in output_dir.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
            
        print(f"Loaded {len(products)} products from {json_path}")
        
        count = 0
        for p in products:
            name = p.get('name') or p.get('title')
            # Generate slug if missing
            slug = p.get('slug')
            if not slug and name:
                # Simple slugify
                slug = name.lower().strip()
                slug = re.sub(r'[^a-z0-9]+', '-', slug)
                slug = slug.strip('-')
            
            if not slug:
                # Fallback if absolutely no identifier
                continue
                
            text_content = format_product_for_rag(p)
            
            # Filename: product_{slug}.txt
            # Ensure filename is safe
            safe_slug = re.sub(r'[^a-zA-Z0-9_-]', '', slug)
            filename = f"product_{safe_slug}.txt"
            
            with open(os.path.join(output_dir, filename), 'w', encoding='utf-8') as out:
                out.write(text_content)
                
            count += 1
            
        print(f"Successfully created {count} text documents in {output_dir}")
        
    except Exception as e:
        print(f"Error processing products: {e}")

if __name__ == "__main__":
    # Adjust paths as needed
    JSON_PATH = "data/processed/full_catalog.json" 
    OUTPUT_DIR = "rag_documents"
    
    process_products(JSON_PATH, OUTPUT_DIR)
