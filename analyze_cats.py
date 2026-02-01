import json
from collections import Counter

def analyze_categories():
    try:
        with open('products.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
            
        categories = []
        for p in products:
            cat = p.get('categories')
            if cat:
                categories.append(cat)
        
        counts = Counter(categories)
        print("Unique categories in products.json:")
        for cat, count in counts.most_common():
            print(f"{cat}: {count}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_categories()
