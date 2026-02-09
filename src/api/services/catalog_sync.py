import requests
import json
import logging
import time
from requests.auth import HTTPBasicAuth
from pathlib import Path
from typing import List, Dict, Any

# Configuration
from config.settings import WC_CONSUMER_KEY, WC_CONSUMER_SECRET, WC_BASE_URL
from src.api.services.woocommerce import normalize_wc_product

logger = logging.getLogger(__name__)

# Use absolute path relative to project root if possible, or reliable relative path
# Assuming this file is in src/api/services, data is in ../../../data
# Better to use a constant from settings or strictly defined path
DATA_DIR = Path("data/processed")
OUTPUT_FILE = DATA_DIR / "wc_catalog.json"

# ... imports

# Status tracking
class SyncStatus:
    is_running: bool = False
    status: str = "idle" # idle, running, saving, completed, error
    fetched: int = 0
    total_est: int = 0
    message: str = ""
    error: str = None
    started_at: float = 0

_sync_status = SyncStatus()

def get_sync_status():
    return {
        "is_running": _sync_status.is_running,
        "status": _sync_status.status,
        "fetched": _sync_status.fetched,
        "total_est": _sync_status.total_est,
        "message": _sync_status.message,
        "error": _sync_status.error,
        "started_at": _sync_status.started_at
    }

def fetch_all_products() -> List[Dict[str, Any]]:
    if not WC_CONSUMER_KEY or not WC_CONSUMER_SECRET:
        raise RuntimeError("WC_CONSUMER_KEY/WC_CONSUMER_SECRET are not set")
    
    if not WC_BASE_URL:
        raise RuntimeError("WC_BASE_URL is not set")

    page = 1
    per_page = 50
    all_products = []
    
    logger.info(f"Starting sync from {WC_BASE_URL}...")
    
    while True:
        logger.info(f"Fetching page {page}...")
        _sync_status.message = f"Загрузка страницы {page}..."
        
        # Retry logic
        retries = 3
        success = False
        while retries > 0:
            try:
                response = requests.get(
                    f"{WC_BASE_URL}/products",
                    auth=HTTPBasicAuth(WC_CONSUMER_KEY, WC_CONSUMER_SECRET),
                    params={"per_page": per_page, "page": page},
                    timeout=60
                )
                
                if response.status_code != 200:
                    logger.warning(f"Error fetching page {page}: {response.status_code} - {response.text}")
                    if response.status_code < 500 and response.status_code != 429:
                        break
                else:
                    success = True
                    # Update total estimate from headers on first page
                    if page == 1:
                        try:
                            _sync_status.total_est = int(response.headers.get('X-WP-Total', 0))
                        except:
                            pass
                    break
                    
            except Exception as e:
                logger.warning(f"Exception fetching page {page}: {e}")
                time.sleep(5)
            
            retries -= 1
        
        if not success:
           logger.error(f"Failed to fetch page {page} after retries.")
           break

        products = response.json()
        if not products:
            break
            
        all_products.extend(products)
        _sync_status.fetched = len(all_products)
        
        logger.info(f"Fetched {len(products)} products. Total so far: {len(all_products)}")
        
        page += 1
            
    logger.info(f"Finished fetching. Total raw products: {len(all_products)}")
    return all_products

def save_catalog(products: List[Dict[str, Any]]):
    _sync_status.status = "saving"
    _sync_status.message = "Сохранение и нормализация..."
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    normalized = []
    error_count = 0
    
    for p in products:
        try:
            norm = normalize_wc_product(p)
            normalized.append(norm)
        except Exception as e:
            logger.error(f"Error normalizing product {p.get('id')}: {e}")
            error_count += 1
            
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
        
    logger.info(f"Saved {len(normalized)} products to {OUTPUT_FILE}. Errors: {error_count}")

def sync_woocommerce_catalog():
    """
    Main entry point for syncing WooCommerce catalog.
    Can be run in background.
    """
    if _sync_status.is_running:
        logger.warning("Sync already running")
        return False

    try:
        _sync_status.is_running = True
        _sync_status.status = "running"
        _sync_status.fetched = 0
        _sync_status.total_est = 0
        _sync_status.error = None
        _sync_status.started_at = time.time()
        _sync_status.message = "Запуск..."
        
        logger.info("Starting WooCommerce catalog sync...")
        products = fetch_all_products()
        save_catalog(products)
        
        _sync_status.status = "completed"
        _sync_status.message = f"Успешно завершено. Товаров: {len(products)}"
        _sync_status.is_running = False
        
        logger.info("WooCommerce catalog sync completed successfully.")
        return True
    except Exception as e:
        logger.error(f"WooCommerce catalog sync failed: {e}")
        _sync_status.status = "error"
        _sync_status.error = str(e)
        _sync_status.message = "Ошибка синхронизации"
        _sync_status.is_running = False
        return False
