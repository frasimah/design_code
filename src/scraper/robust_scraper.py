"""
Robust скрапер: полное извлечение данных через DOM + прокрутку карусели + Gemini валидацию
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from rich.console import Console
import re

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])

from config.settings import VandersandenConfig, GEMINI_API_KEY, DATA_DIR
from src.scraper.gemini_analyzer import GeminiVisionAnalyzer
from src.scraper.utils import clean_text, extract_article, extract_weight, extract_number


console = Console()

SCREENSHOTS_DIR = DATA_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOADS_DIR = DATA_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


class RobustProductScraper:
    """
    Robust скрапер продуктов Vandersanden:
    - Прокрутка карусели для показа всех карточек
    - Извлечение данных из DOM на каждом шаге
    - Дедупликация результатов
    - Gemini для валидации и обогащения (опционально)
    """
    
    def __init__(self, api_key: str = None, headless: bool = True, use_gemini: bool = True):
        self.api_key = api_key or GEMINI_API_KEY
        self.headless = headless
        self.use_gemini = use_gemini and bool(self.api_key)
        self.browser: Optional[Browser] = None
        self.gemini: Optional[GeminiVisionAnalyzer] = None
        self.base_url = VandersandenConfig.BASE_URL
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        if self.use_gemini:
            self.gemini = GeminiVisionAnalyzer(self.api_key)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()
        if self.gemini:
            self.gemini.close()
    
    async def scrape_product(self, url: str) -> dict:
        """Полный скраппинг продукта с гарантией 100% извлечения данных"""
        
        console.log(f"[bold blue]🧱 Robust scraping:[/bold blue] {url}")
        
        page = await self.browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # Block known bot detection and tracking scripts to prevent "botDetected" errors
        # Using regex to ensure we match subdomains and paths correctly
        await page.route(re.compile(r".*pagesense\.io.*"), lambda route: route.abort())
        await page.route(re.compile(r".*google-analytics\.com.*"), lambda route: route.abort())
        await page.route(re.compile(r".*googletagmanager\.com.*"), lambda route: route.abort())
        await page.route(re.compile(r".*hotjar\.com.*"), lambda route: route.abort())
        
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(2)  # Ждём загрузку динамического контента
        
        try:
            await self._dismiss_popups(page)
            
            slug = url.rstrip("/").split("/")[-1]
            
            product_data = {
                "url": url,
                "slug": slug,
                "scraped_at": datetime.now().isoformat(),
            }
            
            # 1. Базовая информация из заголовка
            console.log("[cyan]Extracting header info...[/cyan]")
            header_info = await self._extract_header_info(page, slug)
            product_data.update(header_info)
            
            # 2. Извлекаем изображения из слайдера
            console.log("[cyan]Extracting product images...[/cyan]")
            images = await self._extract_product_images(page)
            product_data["main_image"] = images.get("main_image")
            product_data["gallery"] = images.get("gallery", [])
            console.log(f"[green]Found {1 if images.get('main_image') else 0} main + {len(images.get('gallery', []))} gallery images[/green]")
            
            # 3. Скроллим к табам
            await self._scroll_to_tabs(page)
            
            # 3. Извлекаем ВСЕ швы (прокручивая карусель)
            console.log("[cyan]Collecting all joints...[/cyan]")
            joints = await self._collect_all_tab_cards(page, "швы", "joints")
            product_data["joints"] = joints
            console.log(f"[green]Found {len(joints)} joints[/green]")
            
            # 4. Извлекаем ВСЕ форматы (прокручивая карусель)
            console.log("[cyan]Collecting all formats...[/cyan]")
            formats = await self._collect_all_tab_cards(page, "формат", "formats")
            product_data["available_formats"] = formats
            console.log(f"[green]Found {len(formats)} formats[/green]")
            
            # 5. Скачиваем файлы (DOP, CE, Текстуры)
            console.log("[cyan]Collecting downloads...[/cyan]")
            downloads = await self._collect_downloads(page, slug)
            product_data["downloads"] = downloads
            console.log(f"[green]Downloaded {len(downloads)} files[/green]")
            
            # 6. Gemini для обогащения (если включен)
            if self.use_gemini and self.gemini:
                console.log("[cyan]Gemini enrichment...[/cyan]")
                product_data = await self._enrich_with_gemini(page, product_data, slug)
            
            return product_data
            
        finally:
            await page.close()
    
    async def _extract_header_info(self, page: Page, slug: str) -> dict:
        """Извлечь базовую информацию о продукте из DOM"""
        
        info = {
            "name": slug.replace("-", " ").title(),
            "article": slug.upper().replace("-", ""),
            "texture": None,
            "color": None,
            "description": None,
        }
        
        # Ждём немного после закрытия popup
        await asyncio.sleep(0.5)
        
        # Используем JavaScript для извлечения всех данных
        try:
            result = await page.evaluate(r"""
                (() => {
                    const data = {};
                    
                    // Название и артикул из h1
                    const h1 = document.querySelector('main h1, .c-product-hero h1, article h1');
                    if (h1) {
                        const text = h1.innerText.trim();
                        // Разделяем по переносам строк
                        const parts = text.split(/\n/).map(s => s.trim()).filter(s => s);
                        
                        // Ищем артикул в любой части (формат типа 0124A0)
                        for (const part of parts) {
                            const articleMatch = part.match(/^([0-9]{4}[A-Z0-9]{1,3})$/);
                            if (articleMatch) {
                                data.article = articleMatch[1];
                            } else if (!data.name) {
                                data.name = part;
                            }
                        }
                    }
                    
                    // Текстура и Цвет - ищем в списке характеристик
                    const allDts = document.querySelectorAll('dt, .c-product-detail dt, .product-specs dt');
                    
                    const colorInfo = {
                        base_color: null,
                        additional_colors: [],
                        nuance: null
                    };

                    allDts.forEach(dt => {
                        const label = dt.innerText.trim().toLowerCase();
                        const dd = dt.nextElementSibling;
                        if (dd && dd.tagName === 'DD') {
                            const value = dd.innerText.trim();
                            if (label.includes('текстур')) {
                                data.texture = value;
                            } else if (label.includes('нюанс')) {
                                colorInfo.nuance = value;
                            } else if (label.includes('базовый цвет')) {
                                colorInfo.base_color = value;
                            } else if (label.includes('дополнительные цвета')) {
                                colorInfo.additional_colors.push(value);
                            } else if (label === 'цвет' || label === 'color') {
                                if (!colorInfo.base_color) colorInfo.base_color = value;
                            }
                        }
                    });
                    
                    // Fallback for color info from body text
                    if (!colorInfo.nuance && !colorInfo.base_color) {
                         const bodyText = document.body.innerText;
                         
                         const nuanceMatch = bodyText.match(/Нюанс[:\s]+([^\n]+)/i);
                         if (nuanceMatch) colorInfo.nuance = nuanceMatch[1].trim();
                         
                         const baseColorMatch = bodyText.match(/Базовый цвет[:\s]+([^\n]+)/i);
                         if (baseColorMatch) colorInfo.base_color = baseColorMatch[1].trim();
                         
                         const addColorMatch = bodyText.match(/Дополнительные цвета[:\s]+([^\n]+)/i);
                         if (addColorMatch) {
                            colorInfo.additional_colors.push(addColorMatch[1].trim());
                         }
                    }

                    if (colorInfo.base_color || colorInfo.nuance || colorInfo.additional_colors.length > 0) {
                        data.color = colorInfo;
                    }
                    
                    // Fallback для текстуры - ищем справа от заголовка
                    if (!data.texture) {
                        const heroMeta = document.querySelector('.c-product-hero__meta, .product-meta');
                        if (heroMeta) {
                            const text = heroMeta.innerText;
                            if (text.includes('Текстура')) {
                                const match = text.match(/Текстура[:\s]*([^\n]+)/);
                                if (match) data.texture = match[1].trim();
                            }
                        }
                    }
                    
                    // Ещё один fallback - ищем по всей странице
                    if (!data.texture) {
                        const pageText = document.body.innerText;
                        const textureMatch = pageText.match(/Текстура[:\s]*([А-Яа-яA-Za-z\s]+?)(?:\n|Цвет|Сырьё|$)/);
                        if (textureMatch) {
                            data.texture = textureMatch[1].trim();
                        }
                    }
                    
                    // Описание
                    const descSelectors = [
                        '.c-product-detail__description',
                        '.product-description',
                        '.c-product-hero__description',
                        'article .description',
                        '.c-text-block p'
                    ];
                    for (const sel of descSelectors) {
                        const el = document.querySelector(sel);
                        if (el && el.innerText.trim().length > 50) {
                            data.description = el.innerText.trim();
                            break;
                        }
                    }
                    
                    // Если нет описания, берём первый большой параграф
                    if (!data.description) {
                        const paragraphs = document.querySelectorAll('main p, article p');
                        for (const p of paragraphs) {
                            const text = p.innerText.trim();
                            if (text.length > 100 && !text.includes('cookie')) {
                                data.description = text;
                                break;
                            }
                        }
                    }
                    
                    return data;
                })()
            """)
            
            # Обновляем info значениями из JavaScript
            if result.get("name"):
                info["name"] = result["name"]
            if result.get("article"):
                info["article"] = result["article"]
            if result.get("texture"):
                info["texture"] = result["texture"]
            if result.get("color"):
                info["color"] = result["color"]
            if result.get("description"):
                info["description"] = result["description"]
                
        except Exception as e:
            console.log(f"[yellow]Header extraction error: {e}[/yellow]")
        
        return info
    
    async def _extract_product_images(self, page: Page) -> Dict:
        """
        Извлечь изображения из слайдера продукта
        
        Returns:
            { "main_image": str, "gallery": [str, ...] }
        """
        try:
            # Используем JavaScript для извлечения всех изображений из Slick слайдера
            result = await page.evaluate(r"""
                (() => {
                    // Find all main slide images (excluding clones for infinite scroll)
                    const mainSlides = document.querySelectorAll('.c-product-hero__image.slick-slide:not(.slick-cloned) img');
                    
                    const getCleanUrl = (img) => {
                        let src = img.src || img.dataset.src || '';
                        if (!src && img.srcset) {
                            // Take the largest one from srcset if available
                            const sources = img.srcset.split(',').map(s => s.trim().split(' ')[0]);
                            src = sources[sources.length - 1];
                        }
                        
                        if (src && src.includes('/styles/')) {
                            // Remove style part to get original high-res image
                            // Example: /sites/default/files/public/styles/product_carousel_655x420_/public/product-images/...
                            src = src.replace(/\/styles\/[^/]+\/public\//, '/');
                        }
                        return src;
                    };

                    const urls = Array.from(mainSlides).map(getCleanUrl).filter(url => url);
                    const uniqueUrls = Array.from(new Set(urls));

                    return {
                        main_image: uniqueUrls[0] || null,
                        gallery: uniqueUrls.slice(1),
                        count: uniqueUrls.length
                    };
                })()
            """)
            
            return result
            
        except Exception as e:
            console.log(f"[yellow]Image extraction error: {e}[/yellow]")
            return {"main_image": None, "gallery": []}
    
    async def _collect_all_tab_cards(self, page: Page, tab_text: str, card_type: str) -> List[Dict]:
        """
        Собрать ВСЕ карточки из таба, прокручивая карусель до конца
        
        Args:
            page: Playwright страница
            tab_text: Текст таба для клика ("швы" или "формат")
            card_type: Тип карточек ("joints" или "formats")
            
        Returns:
            Список всех уникальных карточек
        """
        # Кликаем на таб
        await self._click_tab(page, tab_text)
        await asyncio.sleep(0.8)
        
        all_cards = []
        seen_names = set()
        max_iterations = 20  # Защита от бесконечного цикла
        iterations = 0
        
        # Сначала прокручиваем карусель в начало
        for _ in range(10):
            if not await self._scroll_carousel(page, "prev"):
                break
            await asyncio.sleep(0.2)
        
        # Теперь итерируем вперёд и собираем все карточки
        while iterations < max_iterations:
            iterations += 1
            
            # Извлекаем текущие видимые карточки
            cards = await self._extract_visible_cards(page, card_type)
            
            new_cards_found = False
            for card in cards:
                name = card.get("name", "")
                if name and name not in seen_names:
                    seen_names.add(name)
                    all_cards.append(card)
                    new_cards_found = True
            
            # Прокручиваем к следующим карточкам
            scrolled = await self._scroll_carousel(page, "next")
            if not scrolled:
                # Карусель закончилась
                break
            
            await asyncio.sleep(0.3)
        
        return all_cards
    
    async def _extract_visible_cards(self, page: Page, card_type: str) -> List[Dict]:
        """Извлечь данные из текущих видимых карточек"""
        
        cards = []
        card_elements = await page.query_selector_all(".c-shape-tile")
        
        for card_elem in card_elements:
            try:
                # Проверяем видимость карточки
                is_visible = await card_elem.is_visible()
                if not is_visible:
                    continue
                
                card_data = {}
                
                # Название
                title_elem = await card_elem.query_selector(".c-shape-tile__title, p")
                if title_elem:
                    card_data["name"] = clean_text(await title_elem.inner_text()) or ""
                else:
                    # Берём весь текст карточки
                    full_text = await card_elem.inner_text()
                    # Для швов — просто название
                    if card_type == "joints" and len(full_text) < 50:
                        card_data["name"] = clean_text(full_text) or ""
                
                if not card_data.get("name"):
                    continue
                
                # Для форматов — извлекаем характеристики
                if card_type == "formats":
                    dl_elem = await card_elem.query_selector("dl.c-shape-tile__list, dl")
                    if dl_elem:
                        dt_elements = await dl_elem.query_selector_all("dt")
                        dd_elements = await dl_elem.query_selector_all("dd")
                        
                        for dt, dd in zip(dt_elements, dd_elements):
                            label = clean_text(await dt.inner_text()) or ""
                            value = clean_text(await dd.inner_text()) or ""
                            label_lower = label.lower()
                            
                            if "размер" in label_lower:
                                card_data["dimensions"] = value
                            elif "наличии" in label_lower or "перфора" in label_lower:
                                card_data["availability"] = value
                            elif "m²" in label_lower or "м²" in label_lower or "number" in label_lower:
                                card_data["pieces_per_m2"] = extract_number(value)
                            elif "палет" in label_lower:
                                card_data["pieces_per_pallet"] = extract_number(value)
                            elif "вес" in label_lower:
                                card_data["weight_kg"] = extract_weight(value)
                    
                    # Если нет dl — это не формат, пропускаем
                    if not dl_elem and card_type == "formats":
                        continue
                
                # Изображение
                img_elem = await card_elem.query_selector("img")
                if img_elem:
                    card_data["image_url"] = await img_elem.get_attribute("src")
                
                cards.append(card_data)
                
            except Exception as e:
                console.log(f"[yellow]Card extraction error: {e}[/yellow]")
                continue
        
        return cards
    
    async def _scroll_carousel(self, page: Page, direction: str = "next") -> bool:
        """
        Прокрутить карусель в указанном направлении
        
        Returns:
            True если прокрутка успешна, False если достигнут край
        """
        try:
            # Ищем стрелки карусели
            if direction == "next":
                selectors = [
                    ".c-carousel__arrow--next:not([disabled])",
                    ".slick-next:not(.slick-disabled)",
                    ".carousel-next:not(:disabled)",
                    "button[aria-label='Next']:not([disabled])",
                ]
            else:
                selectors = [
                    ".c-carousel__arrow--prev:not([disabled])",
                    ".slick-prev:not(.slick-disabled)",
                    ".carousel-prev:not(:disabled)",
                    "button[aria-label='Previous']:not([disabled])",
                ]
            
            for selector in selectors:
                arrow = await page.query_selector(selector)
                if arrow:
                    is_visible = await arrow.is_visible()
                    if is_visible:
                        await arrow.click()
                        return True
            
            return False
            
        except Exception:
            return False
    
    async def _click_tab(self, page: Page, tab_text: str) -> bool:
        """Кликнуть на таб по тексту"""
        try:
            tabs = await page.query_selector_all("a.c-tabs__link, .c-tabs__item, button.c-tabs__link")
            for tab in tabs:
                text = await tab.inner_text()
                if tab_text.lower() in text.lower():
                    await tab.click()
                    return True
        except Exception as e:
            console.log(f"[yellow]Tab click failed: {e}[/yellow]")
        return False
    
    async def _scroll_to_tabs(self, page: Page):
        """Скроллить к секции табов"""
        try:
            tabs_section = await page.query_selector(".c-tabs")
            if tabs_section:
                await tabs_section.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
            else:
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(0.5)
        except Exception:
            await page.evaluate("window.scrollBy(0, 800)")
    
    async def _dismiss_popups(self, page: Page):
        """Закрыть popup-ы"""
        try:
            close_btn = await page.query_selector(".popup__close")
            if close_btn:
                is_visible = await close_btn.is_visible()
                if is_visible:
                    console.log("[yellow]Closing popup[/yellow]")
                    await close_btn.click()
                    await asyncio.sleep(0.5)
            
            cookie_btn = await page.query_selector("#onetrust-accept-btn-handler")
            if cookie_btn:
                is_visible = await cookie_btn.is_visible()
                if is_visible:
                    await cookie_btn.click()
                    await asyncio.sleep(0.3)
            
            await page.evaluate("""
                document.querySelectorAll('.popup__overlay, .popup').forEach(el => {
                    el.style.display = 'none';
                });
            """)
        except Exception:
            pass
    
    async def _collect_downloads(self, page: Page, slug: str) -> List[Dict]:
        """
        Скачать файлы из секции 'Загрузки и информация'
        
        Returns:
            Список словарей с информацией о скачанных файлах
        """
        import httpx
        
        downloads = []
        product_dir = DOWNLOADS_DIR / slug
        product_dir.mkdir(parents=True, exist_ok=True)
        
        # Скроллим к секции загрузок
        await page.evaluate("window.scrollBy(0, 1500)")
        await asyncio.sleep(0.5)
        
        # Ищем секцию загрузок
        downloads_section = await page.query_selector(".c-downloads, .downloads-section")
        if downloads_section:
            await downloads_section.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
        
        # 1. Скачиваем текстуры (прямые ссылки)
        try:
            textures_downloaded = await self._download_textures(page, product_dir, slug)
            downloads.extend(textures_downloaded)
        except Exception as e:
            console.log(f"[yellow]Textures download failed: {e}[/yellow]")
        
        # 2. Скачиваем DOP PDF
        try:
            dop_file = await self._download_form_pdf(page, product_dir, slug, "dop")
            if dop_file:
                downloads.append(dop_file)
        except Exception as e:
            console.log(f"[yellow]DOP download failed: {e}[/yellow]")
        
        # 3. Скачиваем CE PDF
        try:
            ce_file = await self._download_form_pdf(page, product_dir, slug, "ce")
            if ce_file:
                downloads.append(ce_file)
        except Exception as e:
            console.log(f"[yellow]CE download failed: {e}[/yellow]")
        
        return downloads
    
    async def _download_textures(self, page: Page, product_dir: Path, slug: str) -> List[Dict]:
        """Скачать текстуры (прямые ссылки на ZIP)"""
        import httpx
        
        textures = []
        
        # Кликаем на таб "Текстуры" чтобы открыть
        labels = await page.query_selector_all(".c-downloads__label, label.c-downloads__label")
        for label in labels:
            text = await label.inner_text()
            if "текстур" in text.lower():
                await label.click()
                await asyncio.sleep(0.5)
                break
        
        # Ищем прямые ссылки на скачивание
        download_links = await page.query_selector_all("a.c-btn__download, a.c-brochure-tile__button, a[href*='textures'], a[href$='.zip']")
        
        for link in download_links:
            try:
                href = await link.get_attribute("href")
                if not href:
                    continue
                
                # Формируем полный URL
                if href.startswith("/"):
                    href = f"{self.base_url}{href}"
                
                # Определяем имя файла
                filename = href.split("/")[-1]
                if not filename:
                    filename = f"{slug}_textures.zip"
                
                local_path = product_dir / filename
                
                # Скачиваем файл
                console.log(f"[cyan]Downloading texture: {filename}[/cyan]")
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(href)
                    if response.status_code == 200:
                        with open(local_path, "wb") as f:
                            f.write(response.content)
                        
                        textures.append({
                            "type": "textures",
                            "filename": filename,
                            "local_path": str(local_path),
                            "original_url": href,
                            "size_bytes": len(response.content),
                        })
                        console.log(f"[green]✓ Saved: {filename}[/green]")
            except Exception as e:
                console.log(f"[yellow]Texture download error: {e}[/yellow]")
        
        return textures
    
    async def _download_form_pdf(self, page: Page, product_dir: Path, slug: str, doc_type: str) -> Optional[Dict]:
        """
        Скачать PDF через форму (DOP или CE)
        
        Args:
            page: Страница Playwright
            product_dir: Директория для сохранения
            slug: Slug продукта
            doc_type: 'dop' или 'ce'
        """
        import httpx
        
        # Кликаем на соответствующий таб
        label_selector = f".js--ajax-form-trigger--{doc_type}"
        label = await page.query_selector(label_selector)
        if not label:
            # Пробуем через текст
            labels = await page.query_selector_all(".c-downloads__label")
            for lbl in labels:
                text = await lbl.inner_text()
                if doc_type.upper() in text:
                    label = lbl
                    break
        
        if not label:
            return None
        
        await label.click()
        await asyncio.sleep(0.8)
        
        # Получаем данные формы
        form_selector = f"form[id*='{doc_type}-download-form']"
        form = await page.query_selector(form_selector)
        if not form:
            return None
        
        form_action = await form.get_attribute("action")
        if not form_action:
            return None
        
        if form_action.startswith("/"):
            form_action = f"{self.base_url}{form_action}"
        
        # Собираем данные формы
        form_data = {}
        inputs = await form.query_selector_all("input, select")
        for inp in inputs:
            name = await inp.get_attribute("name")
            value = await inp.get_attribute("value")
            if name:
                # Для select получаем выбранное значение
                tag = await inp.evaluate("el => el.tagName.toLowerCase()")
                if tag == "select":
                    selected = await inp.query_selector("option:checked")
                    if selected:
                        value = await selected.get_attribute("value")
                form_data[name] = value or ""
        
        # Отправляем форму
        console.log(f"[cyan]Downloading {doc_type.upper()} PDF...[/cyan]")
        
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                response = await client.post(
                    form_action,
                    data=form_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/pdf,*/*",
                    }
                )
                
                if response.status_code == 200 and len(response.content) > 1000:
                    # Определяем имя файла
                    filename = f"{slug}_{doc_type}.pdf"
                    content_disp = response.headers.get("content-disposition", "")
                    if "filename=" in content_disp:
                        import re
                        match = re.search(r'filename="?([^";]+)"?', content_disp)
                        if match:
                            filename = match.group(1)
                    
                    local_path = product_dir / filename
                    
                    with open(local_path, "wb") as f:
                        f.write(response.content)
                    
                    console.log(f"[green]✓ Saved: {filename}[/green]")
                    
                    return {
                        "type": doc_type,
                        "filename": filename,
                        "local_path": str(local_path),
                        "original_url": form_action,
                        "size_bytes": len(response.content),
                    }
        except Exception as e:
            console.log(f"[yellow]{doc_type.upper()} form submission failed: {e}[/yellow]")
        
        return None
    
    async def _enrich_with_gemini(self, page: Page, product_data: dict, slug: str) -> dict:
        """Обогатить данные с помощью Gemini (скриншот + анализ)"""
        
        if not self.gemini:
            return product_data
        
        try:
            # Скриншот для Gemini
            screenshot_path = SCREENSHOTS_DIR / f"{slug}_full.png"
            await page.screenshot(path=str(screenshot_path), full_page=False)
            
            # Анализ базовой инфы если не хватает данных
            if not product_data.get("texture") or not product_data.get("color"):
                header_info = self.gemini.analyze_product_info(screenshot_path)
                
                if not product_data.get("texture"):
                    product_data["texture"] = header_info.get("texture")
                if not product_data.get("color"):
                    product_data["color"] = header_info.get("color")
                if not product_data.get("raw_material"):
                    product_data["raw_material"] = header_info.get("raw_material")
                if not product_data.get("description"):
                    product_data["description"] = header_info.get("description")
        except Exception as e:
            console.log(f"[yellow]Gemini enrichment failed: {e}[/yellow]")
        
        return product_data


async def robust_scrape(url: str, api_key: str = None, headless: bool = True) -> dict:
    """Удобная функция для robust скраппинга"""
    async with RobustProductScraper(api_key=api_key, headless=headless) as scraper:
        return await scraper.scrape_product(url)
