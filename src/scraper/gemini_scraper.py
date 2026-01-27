"""
Гибридный скрапер: Playwright + Gemini Vision для анализа динамического контента
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from rich.console import Console

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

from config.settings import VandersandenConfig, GEMINI_API_KEY, DATA_DIR
from src.scraper.gemini_analyzer import GeminiVisionAnalyzer
from src.scraper.utils import clean_text, extract_article


console = Console()

# Директория для скриншотов
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class GeminiProductScraper:
    """
    Гибридный скрапер продуктов Vandersanden:
    - Playwright для навигации и скриншотов
    - Gemini Vision для анализа скриншотов
    """
    
    def __init__(self, api_key: str = None, headless: bool = True):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
        
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.gemini: Optional[GeminiVisionAnalyzer] = None
        self.base_url = VandersandenConfig.BASE_URL
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.gemini = GeminiVisionAnalyzer(self.api_key)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()
        if self.gemini:
            self.gemini.close()
    
    async def scrape_product(self, url: str) -> dict:
        """
        Полный скраппинг продукта с использованием скриншотов и Gemini
        
        Args:
            url: URL страницы продукта
            
        Returns:
            Словарь с данными продукта
        """
        console.log(f"[bold blue]🧱 Gemini+Browser scraping:[/bold blue] {url}")
        
        page = await self.browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(url, wait_until="networkidle")
        
        try:
            # Закрываем popup
            await self._dismiss_popups(page)
            
            # Slug и базовая инфа из URL
            slug = url.rstrip("/").split("/")[-1]
            
            product_data = {
                "url": url,
                "slug": slug,
                "scraped_at": datetime.now().isoformat(),
            }
            
            # 1. Скриншот верхней части страницы для базовой инфы
            console.log("[cyan]Taking header screenshot...[/cyan]")
            header_screenshot = SCREENSHOTS_DIR / f"{slug}_header.png"
            await page.screenshot(path=str(header_screenshot), full_page=False)
            
            # Анализируем с Gemini
            header_info = self.gemini.analyze_product_info(header_screenshot)
            console.log(f"[green]Header info:[/green] {header_info.get('name', 'N/A')} ({header_info.get('article', 'N/A')})")
            
            product_data.update({
                "name": header_info.get("name") or slug.title(),
                "article": header_info.get("article") or slug.upper(),
                "texture": header_info.get("texture"),
                "color": header_info.get("color"),
                "raw_material": header_info.get("raw_material"),
                "description": header_info.get("description"),
            })
            
            # 2. Скроллим к секции табов
            await self._scroll_to_tabs(page)
            
            # 3. Делаем скриншот таба "швы"
            console.log("[cyan]Taking joints tab screenshot...[/cyan]")
            joints_screenshot = SCREENSHOTS_DIR / f"{slug}_joints.png"
            await self._click_tab(page, "швы")
            await asyncio.sleep(0.8)
            await page.screenshot(path=str(joints_screenshot), full_page=False)
            
            # 4. Делаем скриншот таба "Доступные форматы"
            console.log("[cyan]Taking formats tab screenshot...[/cyan]")
            formats_screenshot = SCREENSHOTS_DIR / f"{slug}_formats.png"
            await self._click_tab(page, "формат")
            await asyncio.sleep(0.8)
            await page.screenshot(path=str(formats_screenshot), full_page=False)
            
            # 5. Анализируем оба скриншота с Gemini
            console.log("[cyan]Analyzing tabs with Gemini...[/cyan]")
            
            joints_data = self.gemini.analyze_product_tabs(joints_screenshot)
            formats_data = self.gemini.analyze_product_tabs(formats_screenshot)
            
            # Объединяем данные
            joints = joints_data.get("joints", [])
            formats = formats_data.get("formats", [])
            
            # Если в joints попали форматы — перенести
            if not formats and joints_data.get("formats"):
                formats = joints_data.get("formats", [])
            
            # Если в formats есть joints — добавить
            if formats_data.get("joints") and not joints:
                joints = formats_data.get("joints", [])
            
            product_data["joints"] = joints
            product_data["available_formats"] = formats
            
            console.log(f"[green]Found {len(joints)} joints, {len(formats)} formats[/green]")
            
            return product_data
            
        finally:
            await page.close()
    
    async def _dismiss_popups(self, page: Page):
        """Закрыть popup-ы"""
        try:
            # Кликаем на кнопку закрытия popup
            close_btn = await page.query_selector(".popup__close")
            if close_btn:
                is_visible = await close_btn.is_visible()
                if is_visible:
                    console.log("[yellow]Closing popup[/yellow]")
                    await close_btn.click()
                    await asyncio.sleep(0.5)
            
            # Принимаем cookies
            cookie_btn = await page.query_selector("#onetrust-accept-btn-handler")
            if cookie_btn:
                is_visible = await cookie_btn.is_visible()
                if is_visible:
                    await cookie_btn.click()
                    await asyncio.sleep(0.3)
            
            # Скрываем overlay через JS
            await page.evaluate("""
                document.querySelectorAll('.popup__overlay, .popup').forEach(el => {
                    el.style.display = 'none';
                });
            """)
        except Exception as e:
            console.log(f"[yellow]Popup handling: {e}[/yellow]")
    
    async def _scroll_to_tabs(self, page: Page):
        """Скроллить к секции табов"""
        try:
            tabs_section = await page.query_selector(".c-tabs")
            if tabs_section:
                await tabs_section.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
            else:
                # Скроллим вниз
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(0.5)
        except Exception:
            await page.evaluate("window.scrollBy(0, 800)")
    
    async def _click_tab(self, page: Page, tab_text: str):
        """Кликнуть на таб по тексту"""
        try:
            tabs = await page.query_selector_all("a.c-tabs__link, .c-tabs__item")
            for tab in tabs:
                text = await tab.inner_text()
                if tab_text.lower() in text.lower():
                    await tab.click()
                    return True
        except Exception as e:
            console.log(f"[yellow]Tab click failed: {e}[/yellow]")
        return False


async def scrape_with_gemini(url: str, api_key: str = None, headless: bool = True) -> dict:
    """
    Удобная функция для скраппинга с Gemini
    
    Args:
        url: URL продукта
        api_key: Gemini API key (опционально, берётся из .env)
        headless: Запускать браузер в фоне
        
    Returns:
        Данные продукта
    """
    async with GeminiProductScraper(api_key=api_key, headless=headless) as scraper:
        return await scraper.scrape_product(url)
