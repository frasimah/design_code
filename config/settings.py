"""
Конфигурация проекта Vandersanden Scraper
"""

from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


# API Keys
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8384830526:AAEYlUUOKSETvodhi6GCLERby2SWYZDpHIA")
HF_TOKEN = os.getenv("HF_TOKEN", "")



# Пути
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Создаём директории если не существуют
for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# Vandersanden URLs
class VandersandenConfig:
    BASE_URL = "https://www.vandersanden.com"
    LOCALE = "ru-ru"
    
    # Основные эндпоинты
    PRODUCT_SEARCH_URL = f"{BASE_URL}/{LOCALE}/poisk-produkta"
    PRODUCTS_URL = f"{BASE_URL}/{LOCALE}/products-and-solutions"
    
    # Категории продуктов
    CATEGORIES = {
        "facade_bricks": "fasadnyy-kirpichi",
        "pavers": "trotuarnaya-plitka",
        "facade_panels": "fasadnye-paneli",
    }
    
    @classmethod
    def get_category_url(cls, category: str) -> str:
        """Получить URL категории"""
        category_slug = cls.CATEGORIES.get(category, category)
        return f"{cls.PRODUCT_SEARCH_URL}/{category_slug}"
    
    @classmethod
    def get_product_url(cls, product_slug: str) -> str:
        """Получить URL продукта"""
        return f"{cls.PRODUCTS_URL}/{product_slug}"


# Настройки скраппинга
class ScrapingConfig:
    # HTTP настройки
    REQUEST_TIMEOUT = 30  # секунды
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # секунды между попытками
    
    # Rate limiting
    REQUESTS_PER_SECOND = 2
    DELAY_BETWEEN_REQUESTS = 0.5  # секунды
    
    # Headers
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    
    # Playwright настройки (для JS-рендеринга)
    BROWSER_HEADLESS = True
    BROWSER_TIMEOUT = 60000  # мс


# Настройки экспорта
class ExportConfig:
    DEFAULT_FORMAT = "json"
    AVAILABLE_FORMATS = ["json", "csv", "excel"]
    
    JSON_INDENT = 2
    CSV_DELIMITER = ";"
    EXCEL_SHEET_NAME = "Products"
