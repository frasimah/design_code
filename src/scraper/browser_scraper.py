"""
Playwright-based scraper для сбора данных с интерактивных табов
"""

import asyncio
import re
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser
from rich.console import Console

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

from config.settings import VandersandenConfig, ScrapingConfig
from src.models.product import (
    Product, ProductColor, ProductFormat, ProductImage, ProductProject
)
from src.scraper.utils import clean_text, extract_article, extract_dimensions, extract_weight, extract_number


console = Console()


class JointOption:
    """Вариант шва (цвет затирки)"""
    def __init__(self, name: str, image_url: Optional[str] = None):
        self.name = name
        self.image_url = image_url
    
    def to_dict(self) -> dict:
        return {"name": self.name, "image_url": self.image_url}


class FormatOption:
    """Вариант формата кирпича"""
    def __init__(
        self,
        name: str,
        dimensions: Optional[str] = None,
        availability: Optional[str] = None,
        pieces_per_m2: Optional[int] = None,
        pieces_per_pallet: Optional[int] = None,
        weight_kg: Optional[float] = None,
        image_url: Optional[str] = None,
    ):
        self.name = name
        self.dimensions = dimensions
        self.availability = availability
        self.pieces_per_m2 = pieces_per_m2
        self.pieces_per_pallet = pieces_per_pallet
        self.weight_kg = weight_kg
        self.image_url = image_url
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "dimensions": self.dimensions,
            "availability": self.availability,
            "pieces_per_m2": self.pieces_per_m2,
            "pieces_per_pallet": self.pieces_per_pallet,
            "weight_kg": self.weight_kg,
            "image_url": self.image_url,
        }


class BrowserProductScraper:
    """Playwright-based scraper для продуктов Vandersanden с поддержкой табов"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.base_url = VandersandenConfig.BASE_URL
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()
    
    async def scrape_product(self, url: str) -> dict:
        """
        Полный скраппинг продукта включая данные с табов
        
        Args:
            url: URL страницы продукта
            
        Returns:
            Словарь с данными продукта
        """
        console.log(f"[blue]Browser scraping:[/blue] {url}")
        
        page = await self.browser.new_page()
        await page.goto(url, wait_until="networkidle")
        
        try:
            # Закрываем popup языка/cookies если есть
            await self._dismiss_popups(page)
            
            # Базовая информация
            product_data = await self._parse_basic_info(page, url)
            
            # Данные с табов
            joints, formats = await self._parse_tabs_data(page)
            
            product_data["joints"] = [j.to_dict() for j in joints]
            product_data["available_formats"] = [f.to_dict() for f in formats]
            
            # Общие свойства
            properties = await self._parse_properties(page)
            product_data.update(properties)
            
            # Похожие продукты
            similar = await self._parse_similar_products(page)
            product_data["similar_products"] = similar
            
            # Проекты
            projects = await self._parse_projects(page)
            product_data["projects"] = projects
            
            return product_data
            
        finally:
            await page.close()
    
    async def _dismiss_popups(self, page: Page):
        """Закрытие всех popup-ов (язык, cookies и т.д.)"""
        
        # Попытка закрыть language redirect popup
        try:
            # Ищем кнопку закрытия или "Stay on this site"
            close_selectors = [
                ".popup__close",
                ".popup .close",
                "button[aria-label='close']",
                "button[aria-label='Close']",
                ".js--popup__close",
                ".popup__language-redirect .popup__close",
                # Кнопка "Остаться на сайте" / "Stay"
                "a.popup__button--secondary",
                "button.popup__button--secondary",
            ]
            
            for selector in close_selectors:
                close_btn = await page.query_selector(selector)
                if close_btn:
                    is_visible = await close_btn.is_visible()
                    if is_visible:
                        console.log(f"[yellow]Closing popup: {selector}[/yellow]")
                        await close_btn.click()
                        await asyncio.sleep(0.5)
                        break
        except Exception as e:
            console.log(f"[yellow]Popup close failed: {e}[/yellow]")
        
        # Принимаем cookies если есть
        try:
            cookie_selectors = [
                "#onetrust-accept-btn-handler",
                ".cookie-accept",
                "button[data-testid='cookie-accept']",
                ".accept-cookies",
            ]
            
            for selector in cookie_selectors:
                cookie_btn = await page.query_selector(selector)
                if cookie_btn:
                    is_visible = await cookie_btn.is_visible()
                    if is_visible:
                        console.log(f"[yellow]Accepting cookies: {selector}[/yellow]")
                        await cookie_btn.click()
                        await asyncio.sleep(0.5)
                        break
        except Exception as e:
            console.log(f"[yellow]Cookie accept failed: {e}[/yellow]")
        
        # Убедимся, что overlay не блокирует
        try:
            await page.evaluate("""
                const overlays = document.querySelectorAll('.popup__overlay, .popup');
                overlays.forEach(el => {
                    if (el.style.display !== 'none') {
                        el.style.display = 'none';
                    }
                });
            """)
        except Exception:
            pass
        
        await asyncio.sleep(0.3)
    
    async def _parse_basic_info(self, page: Page, url: str) -> dict:
        """Парсинг базовой информации (название, артикул)"""
        
        # Slug из URL (используем как fallback)
        slug = url.rstrip("/").split("/")[-1]
        
        # Заголовок - ищем в основном контенте, не в popup
        title_text = ""
        
        # Пробуем разные селекторы для основного заголовка
        title_selectors = [
            "main h1",
            ".c-product-detail h1",
            "article h1",
            "#main-content h1",
            "h1.c-product-detail__title",
        ]
        
        for selector in title_selectors:
            title_elem = await page.query_selector(selector)
            if title_elem:
                title_text = await title_elem.inner_text()
                title_text = clean_text(title_text) or ""
                if title_text and len(title_text) < 100:  # Разумная длина заголовка
                    break
        
        # Если не нашли, пробуем просто h1, но проверяем контент
        if not title_text:
            h1_elements = await page.query_selector_all("h1")
            for h1 in h1_elements:
                text = await h1.inner_text()
                text = clean_text(text) or ""
                # Проверяем, что это похоже на название продукта (содержит артикул или slug)
                if text and (extract_article(text) or slug.lower() in text.lower()):
                    title_text = text
                    break
        
        # Fallback на slug
        if not title_text:
            title_text = slug.replace("-", " ").title()
        
        # Разделяем название и артикул
        article = extract_article(title_text)
        name = title_text.replace(article, "").strip() if article else title_text
        
        return {
            "article": article or slug.upper().replace("-", ""),
            "name": name,
            "slug": slug,
            "url": url,
        }
    
    async def _parse_tabs_data(self, page: Page) -> tuple[list[JointOption], list[FormatOption]]:
        """
        Парсинг данных с табов "швы" и "Доступные форматы"
        """
        joints = []
        formats = []
        
        # Скроллим к секции с табами
        tabs_section = await page.query_selector(".c-tabs")
        if not tabs_section:
            console.log("[yellow]No tabs section found[/yellow]")
            return joints, formats
        
        await tabs_section.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        
        # Ищем табы
        tab_links = await page.query_selector_all("a.c-tabs__link")
        
        joints_tab = None
        formats_tab = None
        
        for tab in tab_links:
            text = await tab.inner_text()
            text_lower = text.lower().strip()
            
            if "швы" in text_lower:
                joints_tab = tab
            elif "формат" in text_lower:
                formats_tab = tab
        
        # Парсим таб "швы" - карточки БЕЗ характеристик (просто название + картинка)
        if joints_tab:
            console.log("[cyan]Parsing 'швы' tab...[/cyan]")
            await joints_tab.click()
            await asyncio.sleep(0.8)
            
            # Ищем активную панель или карусель
            active_cards = await page.query_selector_all(".c-shape-tile")
            
            for card in active_cards:
                # Проверяем, есть ли dl (характеристики) — если есть, это формат, а не шов
                has_specs = await card.query_selector("dl.c-shape-tile__list")
                if has_specs:
                    continue  # Пропускаем форматы
                
                # Название цвета шва
                name_elem = await card.query_selector(".c-shape-tile__title")
                if name_elem:
                    name = await name_elem.inner_text()
                else:
                    # Берём весь текст карточки, но убираем технические данные
                    full_text = await card.inner_text()
                    # Если текст короткий и без цифр — это название шва
                    if len(full_text) < 50 and not any(c.isdigit() for c in full_text):
                        name = full_text
                    else:
                        continue
                
                name = clean_text(name)
                if not name:
                    continue
                
                # Изображение
                img_elem = await card.query_selector("img")
                img_url = None
                if img_elem:
                    img_url = await img_elem.get_attribute("src")
                
                joints.append(JointOption(name=name, image_url=img_url))
        
        # Парсим таб "Доступные форматы" - карточки С характеристиками (dl/dt/dd)
        if formats_tab:
            console.log("[cyan]Parsing 'Доступные форматы' tab...[/cyan]")
            await formats_tab.click()
            await asyncio.sleep(0.8)
            
            format_cards = await page.query_selector_all(".c-shape-tile")
            
            for card in format_cards:
                # Проверяем, есть ли dl (характеристики) — только такие карточки парсим
                dl_elem = await card.query_selector("dl.c-shape-tile__list")
                if not dl_elem:
                    continue  # Пропускаем карточки без характеристик
                
                # Название формата
                title_elem = await card.query_selector(".c-shape-tile__title")
                format_name = ""
                if title_elem:
                    format_name = clean_text(await title_elem.inner_text()) or ""
                
                if not format_name:
                    continue
                
                # Характеристики из dl/dt/dd
                dimensions = None
                availability = None
                pieces_per_m2 = None
                pieces_per_pallet = None
                weight_kg = None
                
                dt_elements = await dl_elem.query_selector_all("dt")
                dd_elements = await dl_elem.query_selector_all("dd")
                
                for dt, dd in zip(dt_elements, dd_elements):
                    label = clean_text(await dt.inner_text()) or ""
                    value = clean_text(await dd.inner_text()) or ""
                    label_lower = label.lower()
                    
                    if "размер" in label_lower:
                        dimensions = value
                    elif "наличии" in label_lower or "перфора" in label_lower:
                        availability = value
                    elif "m²" in label_lower or "м²" in label_lower or "number" in label_lower:
                        pieces_per_m2 = extract_number(value)
                    elif "палет" in label_lower:
                        pieces_per_pallet = extract_number(value)
                    elif "вес" in label_lower:
                        weight_kg = extract_weight(value)
                
                # Изображение
                img_elem = await card.query_selector("img")
                img_url = None
                if img_elem:
                    img_url = await img_elem.get_attribute("src")
                
                formats.append(FormatOption(
                    name=format_name,
                    dimensions=dimensions,
                    availability=availability,
                    pieces_per_m2=pieces_per_m2,
                    pieces_per_pallet=pieces_per_pallet,
                    weight_kg=weight_kg,
                    image_url=img_url,
                ))
        
        console.log(f"[green]Found {len(joints)} joints, {len(formats)} formats[/green]")
        return joints, formats
    
    async def _parse_properties(self, page: Page) -> dict:
        """Парсинг общих свойств (текстура, цвет, сырьё)"""
        
        properties = {
            "texture": None,
            "raw_material": None,
            "color": None,
        }
        
        # Ищем секцию свойств
        content = await page.content()
        
        # Текстура
        texture_match = re.search(r"Текстура[:\s]*</?\w+[^>]*>?\s*([^<]+)", content)
        if texture_match:
            properties["texture"] = clean_text(texture_match.group(1))
        
        # Цвет
        base_color_match = re.search(r"Базовый цвет[:\s]*</?\w+[^>]*>?\s*([^<]+)", content)
        additional_match = re.search(r"Дополнительные цвета[:\s]*</?\w+[^>]*>?\s*([^<]+)", content)
        nuance_match = re.search(r"Нюанс[:\s]*</?\w+[^>]*>?\s*([^<]+)", content)
        
        if base_color_match:
            properties["color"] = {
                "base_color": clean_text(base_color_match.group(1)),
                "additional_colors": [],
                "nuance": None,
            }
            if additional_match:
                colors_str = clean_text(additional_match.group(1))
                if colors_str:
                    properties["color"]["additional_colors"] = [c.strip() for c in colors_str.split(",")]
            if nuance_match:
                properties["color"]["nuance"] = clean_text(nuance_match.group(1))
        
        # Сырьё / описание
        if "100% природные ресурсы" in content:
            raw_match = re.search(r"100% природные ресурсы[^<]*</\w+>\s*<p[^>]*>([^<]+)", content)
            if raw_match:
                properties["raw_material"] = clean_text(raw_match.group(1))
        
        return properties
    
    async def _parse_similar_products(self, page: Page) -> list[str]:
        """Парсинг похожих продуктов"""
        similar = []
        
        # Ищем секцию похожих продуктов
        similar_section = await page.query_selector("text=похожие продукты")
        if similar_section:
            parent = await similar_section.evaluate_handle("el => el.closest('section') || el.parentElement.parentElement")
            if parent:
                links = await parent.query_selector_all("a[href*='products-and-solutions']")
                for link in links:
                    href = await link.get_attribute("href")
                    if href:
                        # Извлекаем артикул из текста ссылки
                        text = await link.inner_text()
                        article = extract_article(text)
                        if article and article not in similar:
                            similar.append(article)
        
        return similar
    
    async def _parse_projects(self, page: Page) -> list[dict]:
        """Парсинг связанных проектов"""
        projects = []
        
        inspiration_section = await page.query_selector("text=Вдохновение")
        if inspiration_section:
            parent = await inspiration_section.evaluate_handle("el => el.closest('section') || el.parentElement.parentElement")
            if parent:
                links = await parent.query_selector_all("a[href*='/ru-ru/']")
                for link in links:
                    href = await link.get_attribute("href")
                    text = await link.inner_text()
                    text = clean_text(text)
                    
                    if text and href and "products-and-solutions" not in href:
                        # Извлекаем локацию
                        location_match = re.search(r"\(([A-Z]{2})\)", text)
                        location = location_match.group(1) if location_match else None
                        
                        full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                        
                        projects.append({
                            "name": text,
                            "url": full_url,
                            "location": location,
                        })
        
        return projects


async def scrape_product_with_browser(url: str, headless: bool = True) -> dict:
    """
    Удобная функция для скраппинга одного продукта
    
    Args:
        url: URL продукта
        headless: Запускать браузер в фоновом режиме
        
    Returns:
        Данные продукта
    """
    async with BrowserProductScraper(headless=headless) as scraper:
        return await scraper.scrape_product(url)
