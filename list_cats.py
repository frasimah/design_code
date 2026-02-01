import sys
import os
import requests
from requests.auth import HTTPBasicAuth

# Ensure project root is in path
sys.path.append(os.getcwd())
from config.settings import WC_CONSUMER_KEY, WC_CONSUMER_SECRET, WC_BASE_URL

def list_categories():
    if not WC_CONSUMER_KEY or not WC_CONSUMER_SECRET:
        raise RuntimeError("WC_CONSUMER_KEY/WC_CONSUMER_SECRET are not set")

    print("Fetching WC categories...")
    try:
        response = requests.get(
            f"{WC_BASE_URL}/products/categories",
            auth=HTTPBasicAuth(WC_CONSUMER_KEY, WC_CONSUMER_SECRET),
            params={"per_page": 20},
            timeout=10
        )
        if response.status_code == 200:
            cats = response.json()
            for c in cats:
                print(f"ID: {c['id']}, Name: {c['name']}, Slug: {c['slug']}")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    list_categories()
