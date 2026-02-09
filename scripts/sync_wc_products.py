import sys
from pathlib import Path

# Add project root to path so we can import config and src
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.api.services.catalog_sync import sync_woocommerce_catalog
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

if __name__ == "__main__":
    print("Starting WooCommerce Sync Script...")
    success = sync_woocommerce_catalog()
    if success:
        print("Sync completed successfully.")
        sys.exit(0)
    else:
        print("Sync failed.")
        sys.exit(1)
