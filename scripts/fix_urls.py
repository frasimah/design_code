
import json
from pathlib import Path

DATA_DIR = Path("data/processed")
CATALOG_PATH = DATA_DIR / "full_catalog.json"
BASE_URL = "https://www.vandersanden.com"

def fix_urls():
    if not CATALOG_PATH.exists():
        print("Catalog not found")
        return

    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fixed_count = 0
    for product in data:
        # Fix joints
        if 'joints' in product:
            for joint in product['joints']:
                url = joint.get('image_url', '')
                if url.startswith('/'):
                    joint['image_url'] = BASE_URL + url
                    fixed_count += 1
        
        # Fix gallery if needed (though they looked absolute in the snippet)
        if 'gallery' in product:
             product['gallery'] = [
                 (BASE_URL + img) if img.startswith('/') else img 
                 for img in product['gallery']
             ]
             
    with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Fixed {fixed_count} relative URLs in catalog.")

if __name__ == "__main__":
    fix_urls()
