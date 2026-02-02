"""
Конфигурация проекта Vandersanden Scraper (Furniture Edition)
"""

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()


# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# TELEGRAM_BOT_TOKEN removed
HF_TOKEN = os.getenv("HF_TOKEN", "")
GEMINI_PROXY_URL = os.environ.get("GEMINI_PROXY_URL")
WC_CONSUMER_KEY = os.environ.get("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.environ.get("WC_CONSUMER_SECRET")
WC_BASE_URL = os.environ.get("WC_BASE_URL", "https://de-co-de.ru/wp-json/wc/v3")
HTTPX_VERIFY_SSL = os.environ.get("HTTPX_VERIFY_SSL", "true").lower() in {"1", "true", "yes", "y"}

# Apply Proxy if set
if GEMINI_PROXY_URL:
    # Use socks5h to force remote DNS resolution
    proxy_url = GEMINI_PROXY_URL.replace('socks5://', 'socks5h://')
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url


# Пути
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR
DATA_DIR = BASE_DIR / "data"
PRODUCTS_JSON_PATH = PROJECT_ROOT / "products.json"

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Создаём директории если не существуют
for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# Настройки экспорта
class ExportConfig:
    DEFAULT_FORMAT = "json"
    AVAILABLE_FORMATS = ["json", "csv", "excel"]
    
    JSON_INDENT = 2
    CSV_DELIMITER = ";"
    EXCEL_SHEET_NAME = "Products"
