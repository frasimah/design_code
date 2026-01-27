"""
Скрапер продуктов Vandersanden
"""

import asyncio
import re
from typing import Optional
from bs4 import BeautifulSoup, Tag
from rich.console import Console
from rich.progress import Progress, TaskID

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

from config.settings import VandersandenConfig
from src.models.product import (
    Product, ProductColor, ProductFormat, ProductImage, ProductProject
)
from src.scraper.base import BaseScraper
from src.scraper.utils import (
    clean_text, extract_article, extract_dimensions,
    extract_weight, extract_number, make_absolute_url, extract_slug_from_url
)


console = Console()


class VandersandenProductScraper(BaseScraper):
    """Скрапер для продуктов Vandersanden"""
    
    def __init__(self, category: str = "facade_bricks", **kwargs):
        super().__init__(**kwargs)
        self.category = category
        self.base_url = VandersandenConfig.BASE_URL
        self.category_url = VandersandenConfig.get_category_url(category)
    
    async def get_product_links(self) -> list[str]:
        """
        Получить список ссылок на все продукты в категории
        
        Returns:
            Список URL продуктов
        """
        console.log(f"[green]Getting product links from:[/green] {self.category_url}")
        
        html = await self.fetch(self.category_url)
        soup = self.parse_html(html)
        
        product_links = []
        
        # Ищем ссылки на продукты
        # На странице каталога продукты обычно в карточках с ссылками
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Фильтруем только ссылки на продукты
            if '/products-and-solutions/' in href and href != '/ru-ru/products-and-solutions':
                full_url = make_absolute_url(href, self.base_url)
                if full_url not in product_links:
                    product_links.append(full_url)
        
        console.log(f"[green]Found {len(product_links)} products[/green]")
        return product_links
    
    async def scrape(self, url: str) -> Optional[Product]:
        """
        Скрапить один продукт по URL
        
        Args:
            url: URL страницы продукта
            
        Returns:
            Product или None если не удалось распарсить
        """
        try:
            html = await self.fetch(url)
            soup = self.parse_html(html)
            return self._parse_product(soup, url)
        except Exception as e:
            console.log(f"[red]Error scraping {url}:[/red] {e}")
            return None
    
    def _parse_product(self, soup: BeautifulSoup, url: str) -> Optional[Product]:
        """Парсинг страницы продукта"""
        
        # Название и артикул из заголовка
        title_elem = soup.find('h1')
        if not title_elem:
            return None
        
        title_text = clean_text(title_elem.get_text())
        if not title_text:
            return None
        
        # Разделяем название и артикул (формат: "Lima 0124A0")
        article = extract_article(title_text)
        name = title_text.replace(article, '').strip() if article else title_text
        
        # Slug из URL
        slug = extract_slug_from_url(url)
        
        # Описание и свойства
        description = None
        texture = None
        raw_material = None
        color_info = None
        
        # Ищем секцию с общими свойствами
        for section in soup.find_all(['div', 'section']):
            section_text = section.get_text()
            
            # Текстура
            if 'Текстура' in section_text:
                texture_match = re.search(r'Текстура\s*(.+?)(?:\n|$)', section_text)
                if texture_match:
                    texture = clean_text(texture_match.group(1))
            
            # Сырьё / описание материала
            if '100% природные ресурсы' in section_text or 'глин' in section_text.lower():
                desc_elem = section.find('p') or section.find('div')
                if desc_elem:
                    raw_material = clean_text(desc_elem.get_text())
            
            # Цвет
            if 'Базовый цвет' in section_text:
                color_info = self._parse_color(section)
        
        # Форматы
        formats = self._parse_formats(soup)
        
        # Изображения
        images = self._parse_images(soup, url)
        
        # Проекты
        projects = self._parse_projects(soup)
        
        # Похожие продукты
        similar = self._parse_similar_products(soup)
        
        return Product(
            article=article or slug.upper(),
            name=name,
            slug=slug,
            url=url,
            category=self.category,
            description=description,
            raw_material=raw_material,
            texture=texture,
            color=color_info,
            formats=formats,
            images=images,
            projects=projects,
            similar_products=similar,
        )
    
    def _parse_color(self, section: Tag) -> Optional[ProductColor]:
        """Парсинг информации о цвете"""
        text = section.get_text()
        
        base_color = None
        additional_colors = []
        nuance = None
        
        # Базовый цвет
        base_match = re.search(r'Базовый цвет[:\s]*([^\n]+)', text)
        if base_match:
            base_color = clean_text(base_match.group(1))
        
        # Дополнительные цвета
        add_match = re.search(r'Дополнительные цвета[:\s]*([^\n]+)', text)
        if add_match:
            colors_str = clean_text(add_match.group(1))
            if colors_str:
                additional_colors = [c.strip() for c in colors_str.split(',')]
        
        # Нюанс
        nuance_match = re.search(r'Нюанс[:\s]*([^\n]+)', text)
        if nuance_match:
            nuance = clean_text(nuance_match.group(1))
        
        if base_color:
            return ProductColor(
                base_color=base_color,
                additional_colors=additional_colors,
                nuance=nuance
            )
        return None
    
    def _parse_formats(self, soup: BeautifulSoup) -> list[ProductFormat]:
        """Парсинг форматов/размеров продукта"""
        formats = []
        
        # Ищем секцию с форматами
        format_sections = soup.find_all(string=re.compile(r'Waaldikformaat|WF\d+|Размеры'))
        
        for section in format_sections:
            parent = section.find_parent(['div', 'li', 'section'])
            if not parent:
                continue
            
            text = parent.get_text()
            
            # Название формата
            format_name_match = re.search(r'(Waaldikformaat|WF\d+mm|WF-S|DF|NF)', text)
            if not format_name_match:
                continue
            
            format_name = format_name_match.group(1)
            
            # Размеры
            dimensions = extract_dimensions(text)
            
            # Вес
            weight = extract_weight(text)
            
            # Штук/м²
            pieces_match = re.search(r'Number/m².*?(\d+)', text, re.DOTALL)
            pieces_per_m2 = int(pieces_match.group(1)) if pieces_match else None
            
            # Перфорация
            has_perforation = 'Без перфорации' not in text
            
            formats.append(ProductFormat(
                name=format_name,
                dimensions=dimensions or "N/A",
                weight_kg=weight,
                pieces_per_m2=pieces_per_m2,
                has_perforation=has_perforation
            ))
        
        return formats
    
    def _parse_images(self, soup: BeautifulSoup, base_url: str) -> list[ProductImage]:
        """Парсинг изображений продукта"""
        images = []
        
        for img in soup.find_all('img', src=True):
            src = img['src']
            alt = img.get('alt', '')
            
            # Фильтруем только изображения продукта (не иконки, логотипы и т.д.)
            if any(x in src.lower() for x in ['product', 'brick', 'texture', 'facade']):
                full_url = make_absolute_url(src, base_url)
                images.append(ProductImage(
                    url=full_url,
                    alt=clean_text(alt),
                    type="main"
                ))
        
        return images
    
    def _parse_projects(self, soup: BeautifulSoup) -> list[ProductProject]:
        """Парсинг связанных проектов"""
        projects = []
        
        # Ищем секцию с проектами
        projects_section = soup.find(string=re.compile(r'Вдохновение|Проекты'))
        if not projects_section:
            return projects
        
        parent = projects_section.find_parent(['div', 'section'])
        if not parent:
            return projects
        
        for link in parent.find_all('a', href=True):
            href = link['href']
            name = clean_text(link.get_text())
            
            if name and '/ru-ru/' in href:
                # Извлекаем локацию из названия (обычно в скобках)
                location_match = re.search(r'\(([A-Z]{2})\)', name)
                location = location_match.group(1) if location_match else None
                
                projects.append(ProductProject(
                    name=name,
                    url=make_absolute_url(href, self.base_url),
                    location=location
                ))
        
        return projects
    
    def _parse_similar_products(self, soup: BeautifulSoup) -> list[str]:
        """Парсинг похожих продуктов"""
        similar = []
        
        # Ищем секцию с похожими продуктами
        similar_section = soup.find(string=re.compile(r'похожие продукты', re.IGNORECASE))
        if not similar_section:
            return similar
        
        parent = similar_section.find_parent(['div', 'section'])
        if not parent:
            return similar
        
        # Извлекаем артикулы
        text = parent.get_text()
        articles = re.findall(r'\b(\d{4}[A-Z]\d)\b', text)
        
        return list(set(articles))
    
    async def scrape_all(self) -> list[Product]:
        """
        Скрапить все продукты в категории
        
        Returns:
            Список продуктов
        """
        product_links = await self.get_product_links()
        products = []
        
        with Progress() as progress:
            task = progress.add_task(
                "[green]Scraping products...",
                total=len(product_links)
            )
            
            for url in product_links:
                product = await self.scrape(url)
                if product:
                    products.append(product)
                    console.log(f"[green]✓[/green] {product.name} ({product.article})")
                progress.advance(task)
        
        console.log(f"\n[bold green]Successfully scraped {len(products)} products[/bold green]")
        return products
    
    async def scrape_batch(self, urls: list[str], batch_size: int = 5) -> list[Product]:
        """
        Скрапить продукты batches для эффективности
        
        Args:
            urls: Список URL
            batch_size: Размер batch
            
        Returns:
            Список продуктов
        """
        products = []
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            tasks = [self.scrape(url) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Product):
                    products.append(result)
                elif isinstance(result, Exception):
                    console.log(f"[red]Batch error:[/red] {result}")
            
            # Пауза между batches
            await asyncio.sleep(1)
        
        return products
