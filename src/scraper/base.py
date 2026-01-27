"""
Базовый класс скрапера с общей функциональностью
"""

import asyncio
import httpx
from abc import ABC, abstractmethod
from typing import Optional, Any
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from config.settings import ScrapingConfig


console = Console()


class BaseScraper(ABC):
    """Базовый класс для всех скраперов"""
    
    def __init__(
        self,
        timeout: int = ScrapingConfig.REQUEST_TIMEOUT,
        max_retries: int = ScrapingConfig.MAX_RETRIES,
        delay: float = ScrapingConfig.DELAY_BETWEEN_REQUESTS,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay
        self.headers = ScrapingConfig.DEFAULT_HEADERS.copy()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self.headers,
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._client:
            await self._client.aclose()
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Получить HTTP клиент"""
        if not self._client:
            raise RuntimeError("Scraper must be used as async context manager")
        return self._client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def fetch(self, url: str) -> str:
        """
        Загрузить страницу по URL
        
        Args:
            url: URL для загрузки
            
        Returns:
            HTML контент страницы
        """
        console.log(f"[blue]Fetching:[/blue] {url}")
        response = await self.client.get(url)
        response.raise_for_status()
        await asyncio.sleep(self.delay)  # Rate limiting
        return response.text
    
    async def fetch_json(self, url: str) -> dict:
        """Загрузить JSON по URL"""
        console.log(f"[blue]Fetching JSON:[/blue] {url}")
        response = await self.client.get(url)
        response.raise_for_status()
        await asyncio.sleep(self.delay)
        return response.json()
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """Парсинг HTML в BeautifulSoup объект"""
        return BeautifulSoup(html, "lxml")
    
    @abstractmethod
    async def scrape(self, *args, **kwargs) -> Any:
        """Основной метод скраппинга — реализуется в подклассах"""
        pass
    
    @abstractmethod
    async def scrape_all(self) -> list[Any]:
        """Скраппинг всех элементов — реализуется в подклассах"""
        pass
