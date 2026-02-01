import json
from pathlib import Path

def merge_catalogs():
    project_root = Path(__file__).parent.parent
    wc_json = project_root / "data" / "processed" / "wc_catalog.json"
    output_json = project_root / "data" / "processed" / "full_catalog.json"
    
    full_catalog = []
    
    # 1. Load local catalog
    # 1. Load local catalog (LEGACY BRICKS - DISABLED)
    # if local_json.exists():
    #     with open(local_json, 'r', encoding='utf-8') as f:
    #         local_products = json.load(f)
    #         # Add source flag
    #         for p in local_products:
    #             if 'source' not in p:
    #                 p['source'] = 'local'
    #         full_catalog.extend(local_products)
    #         print(f"Loaded {len(local_products)} products from products.json")
    
    # 2. Load WooCommerce catalog
    if wc_json.exists():
        with open(wc_json, 'r', encoding='utf-8') as f:
            wc_products = json.load(f)
            full_catalog.extend(wc_products)
            print(f"Loaded {len(wc_products)} products from wc_catalog.json")
            
    # 2.5 Fix Currency Labels
    # It appears WooCommerce export labeled EUR prices as RUB (₽).
    # We fix this by replacing the symbol.
    for p in full_catalog:
        params = p.get('parameters', {})
        price = params.get('Цена')
        if price and isinstance(price, str) and '₽' in price:
            # Check if it looks like a Euro price (e.g. > 100 for lights)
            # Actually, given the context, we assume all ₽ are mistyped EURs.
            params['Цена'] = price.replace('₽', 'EUR').strip()
            
    # 3. Save full catalog
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(full_catalog, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully merged {len(full_catalog)} products to {output_json}")

if __name__ == "__main__":
    merge_catalogs()
