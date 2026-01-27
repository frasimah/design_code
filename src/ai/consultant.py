"""
AI-консультант по облицовочному кирпичу Vandersanden
Использует Gemini для генерации ответов и ChromaDB для поиска
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import google.generativeai as genai
import PIL.Image
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import GEMINI_API_KEY, DATA_DIR
from src.ai.embeddings import BrickEmbeddings
from src.ai.facade_generator import FacadeGenerator

console = Console()


# Загружаем промпт из внешнего файла
PROMPT_FILE = Path(__file__).parent.parent.parent / "config" / "consultant_prompt.txt"
if PROMPT_FILE.exists():
    SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8")
else:
    SYSTEM_PROMPT = "Ты консультант по кирпичу Vandersanden. Отвечай на русском языке."


class BrickConsultant:
    """AI-консультант по кирпичу"""
    
    def __init__(self):
        """Инициализация консультанта"""
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Модели
        self.chat_model = genai.GenerativeModel(
            "gemini-3-flash-preview",
            system_instruction=SYSTEM_PROMPT
        )
        
        # Эмбеддинги для поиска
        self.embeddings = BrickEmbeddings()
        
        # Генератор фасадов (Try-On)
        self.facade_generator = FacadeGenerator()
        
        # Загружаем полный каталог для детальной информации
        catalog_path = DATA_DIR / "processed" / "full_catalog.json"
        with open(catalog_path, 'r', encoding='utf-8') as f:
            self.catalog = {p['slug']: p for p in json.load(f)}
            self.slug_map = {p['name'].lower(): p['slug'] for p in self.catalog.values()}
            # Добавляем артикулы в карту
            for p in self.catalog.values():
                if p.get('article'):
                    self.slug_map[p['article'].lower()] = p['slug']
        
        # Инициализация хранилища истории
        from src.storage.chat_storage import ChatStorage
        self.storage = ChatStorage(DATA_DIR / "chat_history.db")
        
        console.print("[green]✓ Консультант инициализирован[/green]")
    
    def _get_product_details(self, slug: str) -> Optional[Dict]:
        """Получить полную информацию о продукте включая PDF данные"""
        product = self.catalog.get(slug)
        if not product:
            return None
        
        # Добавляем данные из PDF
        pdf_path = product.get('parsed_pdf_data')
        if pdf_path and Path(pdf_path).exists():
            try:
                with open(pdf_path, 'r', encoding='utf-8') as f:
                    product['pdf_data'] = json.load(f)
            except Exception:
                pass
        
        return product
    
    def _format_context(self, products: List[Dict]) -> str:
        """Форматирует контекст из найденных продуктов"""
        context_parts = []
        
        for p in products:
            # Если это "виртуальный" продукт (например, шов), у него уже есть все поля
            if p.get('description') and p.get('article') == "SEAM":
                details = p
                slug = p.get('slug', 'unknown')
            else:
                slug = p['slug']
                details = self._get_product_details(slug)
            
            if not details:
                continue
            
            part = f"## {details.get('name', slug)} (арт. {details.get('article', 'N/A')})\n"
            part += f"- Текстура: {details.get('texture', 'N/A')}\n"
            
            color = details.get('color', {})
            part += f"- Цвет: {color.get('base_color', 'N/A')}"
            if color.get('nuance'):
                part += f" ({color['nuance']})"
            part += "\n"
            
            if details.get('description'):
                part += f"- Описание: {details['description']}\n"
            
            # Форматы
            formats = details.get('available_formats', [])
            if formats:
                part += "- Форматы:\n"
                for fmt in formats[:3]:  # Первые 3
                    part += f"  - {fmt.get('name', '')}: {fmt.get('dimensions', '')}\n"
            
            # Швы (Joints)
            joints = details.get('joints', [])
            if joints:
                part += "- Рекомендуемые швы (из каталога):\n"
                for joint in joints:
                    part += f"  - {joint.get('name', '')}\n"
            
            # Технические характеристики из PDF
            if 'pdf_data' in details:
                for doc in details['pdf_data'].get('documents', []):
                    parsed = doc.get('parsed_data', {})
                    tech = parsed.get('технические_характеристики', {})
                    if tech:
                        part += "- Технические характеристики:\n"
                        for key, value in tech.items():
                            if value and not isinstance(value, dict):
                                 part += f"  - {key.replace('_', ' ')}: {value}\n"
                        break
            
            context_parts.append(part)
        
        return "\n".join(context_parts)
    
    def _extract_filters(self, query: str) -> Optional[Dict]:
        """Извлекает фильтры из запроса"""
        query_lower = query.lower()
        
        # 1. Проверка групп (светлые/темные)
        if any(w in query_lower for w in ["светлы", "light", "licht", "bright"]):
            console.print("[cyan]Detected Group Filter: LIGHT[/cyan]")
            return {"base_color": {"$in": ["белый", "бежевый", "жёлтый"]}}
            
        if any(w in query_lower for w in ["темны", "тёмны", "dark", "donker"]):
            console.print("[cyan]Detected Group Filter: DARK[/cyan]")
            return {"base_color": {"$in": ["чёрный", "коричневый", "пурпурный"]}}

        # 2. Карта конкретных цветов
        colors = {
            "черн": "чёрный", "black": "чёрный", "zwart": "чёрный",
            "бел": "белый", "white": "белый", " wit ": "белый",
            "красн": "красный", "red": "красный", "rood": "красный",
            "сер": "серый", "gray": "серый", "grey": "серый", "grijs": "серый",
            "коричн": "коричневый", "brown": "коричневый", "bruin": "коричневый",
            "бежев": "бежевый", "beige": "бежевый",
            "желт": "жёлтый", "жёлт": "жёлтый", "yellow": "жёлтый", "geel": "жёлтый",
            "оранж": "оранжевый", "orange": "оранжевый", "oranje": "оранжевый",
            "пурпур": "пурпурный", "magenta": "пурпурный",
            "розов": "розовый", "pink": "розовый",
            "зелен": "зеленый", "green": "зеленый", "groen": "зеленый"
        }
        
        detected_color = None
        for word, db_color in sorted(colors.items(), key=lambda x: len(x[0]), reverse=True):
            if word in query_lower:
                detected_color = db_color
                break
        
        if detected_color:
            console.print(f"[cyan]Detected Color Filter: {detected_color}[/cyan]")
            return {"base_color": detected_color}
            
        return None

    def _get_catalog_stats(self) -> str:
        """Собирает статистику по каталогу"""
        total = len(self.catalog)
        textures = {}
        colors = {}
        
        for p in self.catalog.values():
            # Текстуры
            tex = p.get('texture')
            if tex:
                textures[tex] = textures.get(tex, 0) + 1
            
            # Цвета
            col = p.get('color', {}).get('base_color')
            if col:
                colors[col] = colors.get(col, 0) + 1
                
        stats = f"Всего моделей в каталоге: {total}\n"
        
        stats += "Распределение по текстурам:\n"
        for k, v in sorted(textures.items(), key=lambda x: x[1], reverse=True):
            stats += f"- {k}: {v}\n"
            
        stats += "\nРаспределение по цветам:\n"
        for k, v in sorted(colors.items(), key=lambda x: x[1], reverse=True):
            stats += f"- {k}: {v}\n"
            
        return stats

    def answer(self, query: str, image_path: Optional[str] = None, user_id: str = "default", n_products: int = 5) -> Dict:
        """
        Ответить на вопрос пользователя с учетом истории и (опционально) изображения
        
        Returns:
            Dict: {'answer': str, 'simulation_image': bytes|None}
        """
        # 1. Загружаем историю
        history = self.storage.get_history(user_id, limit=10)
        
        # 2. Ищем релевантные продукты с учетом фильтров
        where = self._extract_filters(query)
        relevant = self.embeddings.search(query, n_results=n_products, where=where)
        
        # --- NEW LOGIC: Joints Detection ---
        joints_keywords = ["шов", "швы", "стык", "joint", "seam", "фуга", "раствор"]
        is_joint_query = any(k in query.lower() for k in joints_keywords)
        
        if is_joint_query:
             target_slug = self._resolve_slug_from_query(query)
             if not target_slug and relevant:
                 target_slug = relevant[0]['slug']
             
             if target_slug:
                 product_details = self._get_product_details(target_slug)
                 if product_details and product_details.get('joints'):
                     relevant = []
                     for joint in product_details['joints']:
                         image_url = joint.get('image_url', '')
                         if image_url.startswith('/'):
                             image_url = "https://www.vandersanden.com" + image_url
                             
                         relevant.append({
                             "slug": "joint-" + joint.get('name', 'unknown').replace(" ", "-"),
                             "name": f"Шов: {joint.get('name', '')}",
                             "article": "SEAM",
                             "main_image": image_url,
                             "texture": "Шов",
                             "color": {"base_color": joint.get('name', '')},
                             "description": "Рекомендуемый цвет шва для кирпича " + product_details.get('name', '')
                         })
                     console.print(f"[green]Returned {len(relevant)} joints as products for {target_slug}[/green]")
        

        # Enrich relevant products with details for chat.py
        for r in relevant:
            if 'slug' in r:
                details = self._get_product_details(r['slug'])
                if details:
                    r['details'] = details

        context = self._format_context(relevant)
        
        # Добавляем общую статистику
        stats_context = ""
        if any(w in query.lower() for w in ["сколько", "how many", "количество", "count"]):
            stats_context = f"\nОБЩАЯ СТАТИСТИКА КАТАЛОГА (для вопросов о количестве):\n{self._get_catalog_stats()}\n"

        # 3. Формируем сообщение для модели
        image_instruction = ""
        is_tryon = False
        if image_path:
            tryon_keywords = ["примен", "помер", "пример", "попроб", "покаж", "try on", "apply", "тест", "визуал"]
            if any(k in query.lower() for k in tryon_keywords):
                is_tryon = True
                image_instruction = "\nПОЛЬЗОВАТЕЛЬ ХОЧЕТ 'ПРИМЕРИТЬ' КИРПИЧ (Try-On). Проанализируй фото и опиши, как выбранный кирпич будет смотреться. Твой ответ должен вдохновлять.\n"
            else:
                image_instruction = "\nПОЛЬЗОВАТЕЛЬ ЗАГРУЗИЛ ФОТО. Проанализируй его. Если пользователь просит 'применить', 'визуализировать' или 'посмотреть' кирпич на этом фото — подробно опиши, как этот кирпич (из контекста или запроса) будет смотреться на данном объекте (фасаде, стене).\n"

        current_message_content = f"""Вопрос пользователя: {query}

Релевантные продукты из каталога (использовать как примеры):
{context}

{stats_context}
{image_instruction}"""
        
        # 4. Запускаем чат с историей
        chat = self.chat_model.start_chat(history=history or [])
        
        # Подготовка контента
        message_parts = [current_message_content]
        if image_path:
            try:
                img = PIL.Image.open(image_path)
                message_parts.append(img)
            except Exception as e:
                console.print(f"[red]Error loading image: {e}[/red]")

        response = chat.send_message(message_parts)
        response_text = response.text
        
        # 5. Пробуем запустить Try-On
        simulation_image = None
        if is_tryon and image_path:
            try:
                # Пытаемся вытащить slug из запроса
                target_slug = self._resolve_slug_from_query(query)
                if not target_slug and relevant:
                    target_slug = relevant[0]['slug']
                
                if target_slug:
                    console.print(f"[cyan]Запуск визуализации для {target_slug}...[/cyan]")
                    simulation_image = self.facade_generator.generate_facade(image_path, target_slug)
            except Exception as e:
                console.print(f"[red]Try-On Error: {e}[/red]")

        # 6. Сохраняем в базу
        self.storage.add_message(user_id, "user", query)
        self.storage.add_message(user_id, "model", response_text)
        
        return {
            "answer": response_text,
            "products": relevant,
            "simulation_image": simulation_image
        }

    def _resolve_slug_from_query(self, query: str) -> Optional[str]:
        """Пытается найти slug кирпича в тексте запроса"""
        import unicodedata
        
        def normalize(text):
            return "".join(c for c in unicodedata.normalize('NFD', text.lower())
                          if unicodedata.category(c) != 'Mn')

        q_norm = normalize(query)
        
        # 1. Поиск по нормализованным именам
        for name, slug in self.slug_map.items():
            if normalize(name) in q_norm:
                return slug
                
        # 2. Поиск по частям имен (для длинных названий)
        for name, slug in self.slug_map.items():
            name_norm = normalize(name)
            if len(name_norm) > 4 and name_norm in q_norm:
                return slug
                
        return None
    
    def search_products(self, query: str, n_results: int = 5) -> List[Dict]:
        """Поиск продуктов по запросу"""
        where = self._extract_filters(query)
        results = self.embeddings.search(query, n_results=n_results, where=where)
        
        detailed_results = []
        for r in results:
            details = self._get_product_details(r['slug'])
            if details:
                detailed_results.append({
                    **r,
                    'details': details
                })
        
        return detailed_results


def run_cli():
    """Запуск CLI-интерфейса консультанта"""
    console.print(Panel.fit(
        "[bold blue]🧱 AI-консультант по кирпичу Vandersanden[/bold blue]\n\n"
        "Задайте любой вопрос о кирпиче или опишите что ищете.\n"
        "Команды: [cyan]/search <запрос>[/cyan] — поиск продуктов\n"
        "         [cyan]/exit[/cyan] — выход",
        title="Добро пожаловать!"
    ))
    
    consultant = BrickConsultant()
    
    while True:
        try:
            query = Prompt.ask("\n[bold cyan]Вы[/bold cyan]")
            
            if not query.strip():
                continue
            
            if query.lower() in ['/exit', '/quit', '/q', 'выход']:
                console.print("[yellow]До свидания![/yellow]")
                break
            
            if query.startswith('/search '):
                search_query = query[8:].strip()
                console.print(f"\n[cyan]Поиск: {search_query}[/cyan]\n")
                results = consultant.search_products(search_query, n_results=5)
                
                for i, r in enumerate(results, 1):
                    d = r['details']
                    console.print(f"[bold]{i}. {d.get('name', r['slug'])}[/bold] (арт. {d.get('article', 'N/A')})")
                    console.print(f"   Текстура: {d.get('texture', 'N/A')}")
                    color = d.get('color', {})
                    console.print(f"   Цвет: {color.get('base_color', 'N/A')}")
                    console.print(f"   Релевантность: {1 - r['distance']:.1%}")
                    console.print()
                continue
            
            # Обычный вопрос
            console.print("\n[dim]Думаю...[/dim]")
            response = consultant.answer(query)
            
            console.print()
            console.print(Panel(
                Markdown(response),
                title="[bold green]Консультант[/bold green]",
                border_style="green"
            ))
            
        except KeyboardInterrupt:
            console.print("\n[yellow]До свидания![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Ошибка: {e}[/red]")


if __name__ == "__main__":
    run_cli()
