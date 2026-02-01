"""
Поиск кирпича по изображению
Использует Gemini Vision для анализа + ChromaDB для поиска похожих
"""
import base64
import json
from pathlib import Path
from typing import List, Dict, Optional, Union
import google.generativeai as genai
from rich.console import Console
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import GEMINI_API_KEY, DATA_DIR
from src.ai.embeddings import BrickEmbeddings

console = Console()
genai.configure(api_key=GEMINI_API_KEY, transport="rest")

# Модель для анализа изображений
vision_model = genai.GenerativeModel("gemini-3-flash-preview")

ANALYSIS_PROMPT = """Проанализируй изображение предмета мебели или света и опиши его характеристики для поиска в каталоге.

Опиши:
1. Тип предмета (светильник, диван, стул, стол, кресло)
2. Материалы (дерево, металл, стекло, ткань, кожа, камень)
3. Цвет (основной цвет, цвет деталей, отделка)
4. Визуальный стиль (сканди, лофт, современный, классика, минимализм)

Верни JSON:
{
    "item_type": "тип предмета...",
    "material_description": "описание материалов...",
    "color_description": "описание цвета...",
    "style_tags": ["лофт", "минимализм"],
    "search_query": "короткий запрос для поиска в каталоге, например: серый диван в стиле лофт"
}
"""


class ImageSearch:
    """Поиск кирпича по изображению"""
    
    def __init__(self):
        self.embeddings = BrickEmbeddings()
        
        # Загружаем каталог для детальной информации
        catalog_path = DATA_DIR / "processed" / "full_catalog.json"
        with open(catalog_path, 'r', encoding='utf-8') as f:
            self.catalog = {p['slug']: p for p in json.load(f) if p.get('slug')}
        
        console.print("[green]✓ ImageSearch инициализирован[/green]")
    
    def analyze_image(self, image_data: Union[bytes, str, Path]) -> Dict:
        """
        Анализирует изображение кирпича
        
        Args:
            image_data: bytes изображения, путь к файлу или base64 строка
            
        Returns:
            Словарь с анализом (цвет, текстура, стиль)
        """
        # Подготовка изображения
        if isinstance(image_data, (str, Path)):
            path = Path(image_data)
            if path.exists():
                with open(path, 'rb') as f:
                    image_bytes = f.read()
            else:
                # Предполагаем base64
                image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # Запрос к Gemini Vision
        content = [
            ANALYSIS_PROMPT,
            {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_bytes).decode()
            }
        ]
        
        response = vision_model.generate_content(content)
        text = response.text
        
        # Парсим JSON из ответа
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        return json.loads(text.strip())
    
    def search_by_image(self, image_data: Union[bytes, str, Path], n_results: int = 5) -> List[Dict]:
        """
        Поиск похожих кирпичей по изображению
        
        Args:
            image_data: Изображение (bytes, путь или base64)
            n_results: Количество результатов
            
        Returns:
            Список найденных продуктов с метаданными
        """
        # Анализируем изображение
        analysis = self.analyze_image(image_data)
        
        # Формируем поисковый запрос
        search_query = analysis.get('search_query', '')
        if not search_query:
            # Формируем из компонентов
            search_query = f"{analysis.get('color_description', '')} {analysis.get('texture_description', '')}"
        
        # Ищем в ChromaDB (Топ-10 для Reranking)
        results = self.embeddings.search(search_query, n_results=10)
        
        # Добавляем детали продуктов
        detailed_results = []
        for r in results:
            product = self.catalog.get(r['slug'], {})
            detailed_results.append({
                **r,
                'product': product,
                'analysis': analysis
            })
            
        # RERANKING
        # Если есть байты изображения, запускаем Reranking
        if isinstance(image_data, bytes):
            detailed_results = self.rerank_candidates(image_data, detailed_results)
        elif isinstance(image_data, (str, Path)):
            p = Path(image_data)
            if p.exists():
                with open(image_data, "rb") as f:
                    detailed_results = self.rerank_candidates(f.read(), detailed_results)

        # Обрезаем до начального запроса n_results (обычно 5)
        return detailed_results[:n_results]
    
    def _get_best_texture_image(self, slug: str) -> Optional[Path]:
        """Ищет лучшее изображение текстуры для продукта"""
        textures_dir = DATA_DIR / "downloads" / slug / "textures"
        if not textures_dir.exists():
            return None
            
        # Ищем все jpg
        images = list(textures_dir.glob("*.jpg"))
        if not images:
            return None
            
        # Приоритет: WF, потом 01
        # Сортируем так, чтобы WF были первыми, и по имени
        images.sort(key=lambda p: (
            0 if "WF" in p.name and "50mm" not in p.name else 1, 
            0 if "_01_" in p.name else 1,
            p.name
        ))
        
        return images[0]

    def rerank_candidates(self, user_image_bytes: bytes, candidates: List[Dict]) -> List[Dict]:
        """
        Переранжирование кандидатов с помощью Gemini Vision
        Сравнивает фото пользователя с фото кандидатов
        """
        console.print("[cyan]Запуск Vision Reranking...[/cyan]")
        
        # Подготавливаем изображения кандидатов
        candidate_images = []
        candidates_map = {}
        
        for i, cand in enumerate(candidates):
            slug = cand['slug']
            img_path = self._get_best_texture_image(slug)
            
            # Если нет распакованной текстуры, пропускаем или берем main_imag (которого у нас нет локально кроме как в json url)
            # Но у нас есть URL, можно было бы скачать, но это долго.
            # Если нет текстуры, пропускаем участие в визуальном сравнении (оставляем как есть)
            if img_path:
                candidates_map[i] = cand
                with open(img_path, "rb") as f:
                    candidate_images.append({
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(f.read()).decode()
                    })
        
        if not candidate_images:
            console.print("[yellow]Нет локальных текстур для сравнения. Пропускаем Reranking.[/yellow]")
            return candidates

        # Промпт для сравнения
        prompt = (
            f"I have a user photo (first image) and {len(candidate_images)} candidate bricks (subsequent images).\n"
            f"Identify which candidate represents the brick in the user photo BEST.\n"
            "Compare color nuances, texture details, and surface style.\n"
            "Return JSON with 'best_match_index' (0-based index among candidates) and 'confidence' (0-1)."
        )
        
        content = [prompt]
        # 1. Фото пользователя
        content.append({
            "mime_type": "image/jpeg",
            "data": base64.b64encode(user_image_bytes).decode()
        })
        # 2. Фото кандидатов
        content.extend(candidate_images)
        
        try:
            response = vision_model.generate_content(content)
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            result = json.loads(text.strip())
            best_idx = result.get('best_match_index')
            confidence = result.get('confidence', 0.0)
            
            if best_idx is not None and best_idx in candidates_map:
                best_cand = candidates_map[best_idx]
                console.print(f"[green]Vision выбрал: {best_cand['slug']} (conf: {confidence})[/green]")
                
                # Перемещаем победителя наверх
                # Создаем новый список
                new_candidates = [best_cand]
                for c in candidates:
                    if c['slug'] != best_cand['slug']:
                        new_candidates.append(c)
                
                # Добавляем пометку
                best_cand['vision_confidence'] = confidence
                return new_candidates
                
        except Exception as e:
            console.print(f"[red]Ошибка Reranking: {e}[/red]")
            
        return candidates
    
    def format_results(self, results: List[Dict], include_analysis: bool = True) -> str:
        """Форматирует результаты для вывода"""
        if not results:
            return "Похожих кирпичей не найдено."
        
        lines = []
        
        if include_analysis and results[0].get('analysis'):
            analysis = results[0]['analysis']
            lines.append("📸 *Анализ изображения:*")
            lines.append(f"Цвет: {analysis.get('color_description', 'N/A')}")
            lines.append(f"Текстура: {analysis.get('texture_description', 'N/A')}")
            lines.append("")
        
        lines.append("🔍 *Похожие продукты:*")
        lines.append("")
        
        for i, r in enumerate(results, 1):
            product = r.get('product', {})
            name = product.get('name', r['slug'])
            article = product.get('article', '')
            color = product.get('color', {}).get('base_color', '')
            texture = product.get('texture', '')
            relevance = 1 - r['distance']
            
            lines.append(f"{i}. *{name}* ({article})")
            
            if r.get('vision_confidence'):
                lines.append(f"   🔥 [Vision Match: {r['vision_confidence']:.1f}]")
            
            lines.append(f"   {color} | {texture}")
            lines.append(f"   Совпадение: {relevance:.0%}")
            lines.append("")
        
        return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Поиск кирпича по изображению")
    parser.add_argument("image", help="Путь к изображению")
    parser.add_argument("-n", "--num", type=int, default=5, help="Количество результатов")
    
    args = parser.parse_args()
    
    searcher = ImageSearch()
    results = searcher.search_by_image(args.image, n_results=args.num)
    
    print(searcher.format_results(results))
