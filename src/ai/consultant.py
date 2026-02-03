"""
AI-консультант по дизайнерской мебели De-co-de
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
import requests
import io
from functools import lru_cache


sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import GEMINI_API_KEY, DATA_DIR
from src.ai.embeddings import BrickEmbeddings

console = Console()


# Загружаем промпт из внешнего файла
PROMPT_FILE = Path(__file__).parent.parent.parent / "config" / "consultant_prompt.txt"
if PROMPT_FILE.exists():
    SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8")
else:
    SYSTEM_PROMPT = "Ты эксперт-консультант по дизайнерской мебели De-co-de. Отвечай на русском языке."


class Consultant:
    """AI-консультант по мебели"""
    
    def __init__(self):
        """Инициализация консультанта"""
        # Используем REST транспорт для поддержки SOCKS прокси
        genai.configure(api_key=GEMINI_API_KEY, transport="rest")
        
        # Модели
        self.chat_model = genai.GenerativeModel(
            "gemini-3-flash-preview",
            system_instruction=SYSTEM_PROMPT
        )
        
        # Эмбеддинги для поиска
        self.embeddings = BrickEmbeddings()
        
        # Загружаем полный каталог для детальной информации
        catalog_path = DATA_DIR / "processed" / "full_catalog.json"
        self.catalog = {}
        self.slug_map = {}
        
        if catalog_path.exists():
            with open(catalog_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.catalog = {p['slug']: p for p in data if p.get('slug')}
                self.slug_map = {p['name'].lower(): p['slug'] for p in self.catalog.values()}
                # Добавляем артикулы в карту
                for p in self.catalog.values():
                    if p.get('article'):
                        self.slug_map[str(p['article']).lower()] = p['slug']
        
        # Инициализация хранилища истории
        from src.storage.chat_storage import ChatStorage
        self.storage = ChatStorage(DATA_DIR / "chat_history.db")
        
        console.print("[green]✓ Консультант инициализирован[/green]")
    
    
    def _get_product_details(self, slug: str) -> Optional[Dict]:
        """Получить полную информацию о продукте"""
        return self.catalog.get(slug)
    
    @lru_cache(maxsize=100)
    def _fetch_image(self, url: str) -> Optional[PIL.Image.Image]:
        """Fetch image from URL with caching"""
        if not url:
            return None
        try:
            # Add timeout to avoid hanging
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                img = PIL.Image.open(io.BytesIO(resp.content))
                img.thumbnail((512, 512)) # Resize to save tokens
                return img
        except Exception as e:
            console.print(f"[yellow]Failed to fetch image {url}: {e}[/yellow]")
        return None

    
    def _format_context(self, products: List[Dict]) -> str:
        """Форматирует контекст из найденных продуктов"""
        context_parts = []
        
        for p in products:
            slug = p['slug']
            details = self._get_product_details(slug)
            
            if not details:
                continue
            
            part = f"## {details.get('title', details.get('name', slug))} (арт. {details.get('article', 'N/A')})\n"
            
            brand = details.get('brand')
            if brand:
                part += f"- Бренд: {brand}\n"
            
            price = details.get('price')
            currency = details.get('currency', '')
            if price:
                part += f"- Цена: {price} {currency}\n"
            
            if details.get('description'):
                desc = details['description'].replace('\n', ' ').strip()
                if len(desc) > 300:
                    desc = desc[:300] + "..."
                part += f"- Описание: {desc}\n"
            
            # Параметры
            params = details.get('parameters', {})
            if params:
                part += "- Характеристики:\n"
                for k, v in params.items():
                    if k != "Цена" and v:
                        part += f"  - {k}: {v}\n"

            context_parts.append(part)
        
        return "\n".join(context_parts)

    def _extract_filters(self, query: str) -> Optional[Dict]:
        """Извлекает фильтры из запроса"""
        # Пока возвращаем None, или можно добавить простую логику
        return None



    def _rerank_products(self, query: str, products: List[Dict]) -> List[Dict]:
        """
        Rerank and filter products using LLM to ensure they match specific constraints (color, material, etc).
        """
        if not products:
            return []
            
        # console.print("[cyan]Running LLM Reranking...[/cyan]")
        
        # Prepare candidates for LLM
        candidates_text = ""
        for i, p in enumerate(products):
            details = p.get('details', {})
            name = details.get('name', p['slug'])
            desc = details.get('description', '')[:200]
            attributes = details.get('attributes', {})
            
            candidates_text += f"Item {i}: {name}\nDesc: {desc}\nAttrs: {attributes}\n\n"
            
        prompt = f"""User Query: "{query}"

I have a list of candidate products found by semantic search. 
Your task is to FILTER out products that strictly DO NOT match the visual constraints in the user query (e.g. wrong color, wrong type).
If the query is vague, keep more products. If specific (e.g. "black lamp"), be strict.

Candidates:
{candidates_text}

Return a JSON with a list of indices of the best matching products (max 5), sorted by relevance.
Format: {{ "indices": [0, 2, ...] }}
"""
        try:
            response = self.chat_model.generate_content(prompt)
            text = response.text
            
            import re
            json_match = re.search(r'```json\s*({.*?})\s*```', text, re.DOTALL)
            if not json_match:
                json_match = re.search(r'```\s*({.*?})\s*```', text, re.DOTALL)
                
            if json_match:
                data = json.loads(json_match.group(1))
                indices = data.get("indices", [])
                
                reranked = []
                for idx in indices:
                    if 0 <= idx < len(products):
                        reranked.append(products[idx])
                
                if reranked:
                    # console.print(f"[green]Reranked to {len(reranked)} products[/green]")
                    return reranked
                    
        except Exception as e:
            console.print(f"[red]Reranking failed: {e}[/red]")
            
        return products[:5] # Fallback to top 5

    def answer(self, query: str, image_path: Optional[str] = None, user_id: str = "default", n_products: int = 5, sources: Optional[List[str]] = None) -> Dict:
        """
        Ответить на вопрос пользователя с учетом истории и (опционально) изображения
        """
        # 1. Загружаем историю
        history = self.storage.get_history(user_id, limit=10)
        
        # 2. Ищем релевантные продукты
        try:
            # Combine filters
            where_filters = self._extract_filters(query) or {}
            
            # Add source filter if specified
            if sources:
                if len(sources) == 1:
                    where_filters["source"] = sources[0]
                else:
                    where_filters["source"] = {"$in": sources}
            
            # If where_filters is empty, set to None
            if not where_filters:
                where_filters = None
            
            relevant = self.embeddings.search(query, n_results=20, where=where_filters)
            console.print(f"[dim]Search returned {len(relevant)} raw products (sources={sources})[/dim]")
            
            # Enrich relevant products with details locally first for reranking
            for r in relevant:
                if 'slug' in r:
                    details = self._get_product_details(r['slug'])
                    if details:
                        r['details'] = details
            
            # Rerank to get top 5 best matches
            relevant = self._rerank_products(query, relevant)
        except Exception as e:
            console.print(f"[yellow]Embedding search failed (ignoring): {e}[/yellow]")
            relevant = []
        
        # Enrich relevant products with details (already done for reranking, but ensuring safety)
        for r in relevant:
            if 'slug' in r and 'details' not in r:
                 details = self._get_product_details(r['slug'])
                 if details:
                     r['details'] = details

        context = self._format_context(relevant)
        
        # 3. Формируем сообщение для модели
        current_message_content = []
        
        # Текстовая часть запроса
        text_part = f"""Вопрос пользователя: {query}

Релевантные продукты из каталога (использовать как примеры):
{context}
"""
        current_message_content.append(text_part)

        # Добавляем изображения продуктов для визуального контекста
        # Берем топ-3 продукта, чтобы не перегружать контекст
        products_with_images = 0
        for p in relevant[:3]:
            details = p.get('details', {})
            image_url = details.get('main_image') or (details.get('images', [])[0] if details.get('images') else None)
            
            if image_url:
                img = self._fetch_image(image_url)
                if img:
                    current_message_content.append(f"\nИзображение для товара {details.get('name')} (Арт. {details.get('article')}):")
                    current_message_content.append(img)
                    products_with_images += 1
        
        if products_with_images > 0:
            current_message_content.append("\nВАЖНО: Я предоставил изображения некоторых товаров. Используй их чтобы отвечать на вопросы о внешнем виде, цветах, стиле и форме.")

        image_instruction = ""
        if image_path:
            image_instruction = "\nПОЛЬЗОВАТЕЛЬ ЗАГРУЗИЛ СВОЕ ФОТО. Проанализируй его в контексте вопроса о мебели/интерьере.\n"
            current_message_content.append(image_instruction)
            try:
                img = PIL.Image.open(image_path)
                current_message_content.append(img)
            except Exception as e:
                console.print(f"[red]Error loading user image: {e}[/red]")
        
        # 4. Запускаем чат
        chat = self.chat_model.start_chat(history=history or [])
        
        try:
            response = chat.send_message(current_message_content)
            response_text = response.text
        except Exception as e:
            console.print(f"[red]Chat Error: {e}[/red]")
            # Retry text only if multimodal failed
            response = chat.send_message(text_part)
            response_text = response.text
        
        # --- UI Control (Optional: keep if frontend uses it) ---
        import re
        recommended_slugs = []
        
        # Ищем JSON блок
        json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
        if not json_match:
             json_match = re.search(r'```\s*({.*?})\s*```', response_text, re.DOTALL)

        if json_match:
            try:
                json_str = json_match.group(1)
                data = json.loads(json_str)
                recommended_slugs = data.get("recommended_slugs", [])
            except Exception:
                pass
        
        final_products = []
        if recommended_slugs:
            relevant_map = {p['slug']: p for p in relevant}
            for slug in recommended_slugs:
                if slug in relevant_map:
                    final_products.append(relevant_map[slug])
        else:
             final_products = [] # Strict mode: do not show products if not explicitly recommended

        # Clean up response (remove JSON block if present)
        clean_response = response_text
        import re
        
        # 1. Remove JSON in code blocks (```json ... ``` or ``` ... ```)
        # 1. New Robust Logic: Find "recommended_slugs" and cut backwards
        # Start looking from the end to find the JSON block
        
        # Check if "recommended_slugs" exists at all
        idx = clean_response.rfind("recommended_slugs")
        if idx != -1:
            # Look backwards from 'recommended_slugs' to find the opening '{'
            # We scan backwards up to 300 chars to be safe (JSON header shouldn't be huge)
            start_search = max(0, idx - 300)
            brace_idx = clean_response.rfind("{", start_search, idx)
            
            if brace_idx != -1:
                # We found the block start. verifying it looks like our target JSON
                # Validate slightly to ensure we don't cut innocent text
                # We assume the block is at the END of the message usually.
                
                # Cut everything from brace_idx to the end
                potential_json = clean_response[brace_idx:]
                # Double check closing brace exists
                if "}" in potential_json:
                     clean_response = clean_response[:brace_idx]

        # 2. Cleanup artifacts like ```json or empty lines left behind
        clean_response = re.sub(r'```json\s*$', '', clean_response).strip()
        clean_response = re.sub(r'```\s*$', '', clean_response).strip()
        
        # 3. Final cleanup of trailing whitespace
        clean_response = clean_response.strip()
        
        self.storage.add_message(user_id, "user", query)
        self.storage.add_message(user_id, "model", response_text) # Save full response with JSON for debugging/future use
        
        return {
            "answer": clean_response,
            "products": final_products
        }

    def search_products(self, query: str, n_results: int = 5) -> List[Dict]:
        """Поиск продуктов по запросу"""
        results = self.embeddings.search(query, n_results=n_results)
        
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
        "[bold blue]🛋️ AI-консультант De-co-de[/bold blue]\n\n"
        "Задайте любой вопрос о мебели.\n"
        "Команды: [cyan]/search <запрос>[/cyan] — поиск продуктов\n"
        "         [cyan]/exit[/cyan] — выход",
        title="Welcome"
    ))
    
    consultant = Consultant()
    
    while True:
        try:
            query = Prompt.ask("\n[bold cyan]Вы[/bold cyan]")
            
            if not query.strip():
                continue
            
            if query.lower() in ['/exit', '/quit', '/q', 'выход']:
                break
            
            if query.startswith('/search '):
                search_query = query[8:].strip()
                results = consultant.search_products(search_query, n_results=5)
                
                for i, r in enumerate(results, 1):
                    d = r['details'] or {}
                    console.print(f"[bold]{i}. {d.get('name', r['slug'])}[/bold]")
                    console.print(f"   Цена: {d.get('price')} {d.get('currency')}")
                    console.print()
                continue
            
            # Обычный вопрос
            console.print("\n[dim]Думаю...[/dim]")
            response = consultant.answer(query)
            
            console.print()
            console.print(Panel(
                Markdown(response['answer']),
                title="[bold green]Консультант[/bold green]",
                border_style="green"
            ))
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Ошибка: {e}[/red]")


if __name__ == "__main__":
    run_cli()
