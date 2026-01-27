"""
Генерация фасада с помощью Gemini Image
Использует модель gemini-3-pro-image-preview для редактирования изображений
"""
import base64
import json
import logging
from pathlib import Path
from typing import Optional, Union, Dict
import google.generativeai as genai
from rich.console import Console
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import GEMINI_API_KEY, DATA_DIR

console = Console()
logger = logging.getLogger(__name__)

# Настраиваем Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Модель для редактирования изображений
# Важно: используем правильное название модели из документации
IMAGE_MODEL_NAME = "gemini-3-pro-image-preview"

class FacadeGenerator:
    """Генератор фасадов с помощью AI"""
    
    def __init__(self):
        # Загружаем каталог для получения описаний текстур
        catalog_path = DATA_DIR / "processed" / "full_catalog.json"
        texture_path = DATA_DIR / "processed" / "texture_analysis.json"
        
        with open(catalog_path, 'r', encoding='utf-8') as f:
            self.catalog = {p['slug']: p for p in json.load(f)}
            
        if texture_path.exists():
            with open(texture_path, 'r', encoding='utf-8') as f:
                self.textures = json.load(f)
        else:
            self.textures = {}
            
        console.print("[green]✓ FacadeGenerator инициализирован[/green]")

    def _get_brick_description(self, product_slug: str) -> str:
        """Получает визуальное описание кирпича для промпта"""
        
        # 1. Сначала ищем в детальном анализе текстур
        if product_slug in self.textures:
            tex = self.textures[product_slug]
            color = tex.get('color_analysis', '')
            texture = tex.get('texture_description', '')
            style = ", ".join(tex.get('style_tags', []))
            return f"brick with {texture}, color is {color}. Style: {style}"
            
        # 2. Если нет, берем из каталога
        product = self.catalog.get(product_slug)
        if product:
            color = product.get('color', {}).get('base_color', '')
            texture = product.get('texture', '')
            return f"{color} brick with {texture} texture"
            
        return "brick"

    def generate_facade(self, 
                       house_image: Union[bytes, str, Path], 
                       product_slug: str,
                       output_path: Optional[Path] = None) -> Optional[bytes]:
        """
        Заменяет фасад дома на выбранный кирпич
        
        Args:
            house_image: Исходное фото дома
            product_slug: Slug кирпича (например 'aalborg')
            output_path: Куда сохранить результат
            
        Returns:
            bytes сгенерированного изображения
        """
        try:
            # Получаем описание кирпича
            brick_desc = self._get_brick_description(product_slug)
            product_name = self.catalog.get(product_slug, {}).get('name', product_slug)
            
            console.print(f"[cyan]Генерация фасада с {product_name}...[/cyan]")
            
            # Подготовка изображения
            if isinstance(house_image, (str, Path)):
                with open(house_image, 'rb') as f:
                    image_bytes = f.read()
            else:
                image_bytes = house_image

            # Формируем промпт для редактирования
            # Используем специальные токены если модель поддерживает, или просто instruction
            prompt = (
                f"Replace the facade material of the house with {product_name} brick. "
                f"The brick should look like this: {brick_desc}. "
                "Keep the windows, roof, door, and surroundings exactly the same. "
                "Ensure realistic lighting, shadows, and perspective. "
                "High quality, photorealistic architectural visualization."
            )
            
            # TODO: В текущей версии Python SDK для Gemini Image редактирование может отличаться.
            # Если прямой edit не поддерживается, используем generate_content с image input
            
            # Вариант 1: Использование Image Generation API (если доступно через genai)
            # В документации (которую мы читали) упоминается prompt + image input
            
            model = genai.GenerativeModel(IMAGE_MODEL_NAME)
            
            content = [
                prompt,
                {
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(image_bytes).decode()
                }
            ]
            
            response = model.generate_content(content)
            
            # Проверяем, есть ли изображение в ответе
            # Ответ может прийти как InlineData или FileUri (зависит от версии)
            
            # В Python SDK images обычно находятся в response.parts или response.candidates
            # Но для Gemini Image API (Imagen 3) формат может отличаться.
            # Пока попробуем стандартный generate_content и проверим response.parts[0].inline_data
            
            # 1. Сначала ищем картинку в ответе (успешный сценарий)
            if hasattr(response, 'parts'):
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        result_bytes = part.inline_data.data
                        
                        if output_path:
                            with open(output_path, 'wb') as f:
                                f.write(result_bytes)
                        
                        return result_bytes
            
            # 2. Если картинки нет, проверяем текст (может быть отказ)
            try:
                if hasattr(response, 'text') and response.text:
                    logger.warning(f"Модель вернула текст: {response.text}")
                    console.print(f"[yellow]Предупреждение от модели:[/yellow] {response.text}")
            except Exception:
                # Игнорируем ошибку доступа к text, если он недоступен для multi-part
                pass

            # 3. Проверяем Safety Ratings
            if hasattr(response, 'candidates') and response.candidates:
                 console.print(f"[red]Safety Ratings:[/red] {response.candidates[0].safety_ratings}")
            
            logger.error("Не удалось получить изображение от модели. Пустой ответ.")
            return None

        except Exception as e:
            logger.error(f"Ошибка генерации фасада: {e}", exc_info=True)
            console.print(f"[bold red]Ошибка:[/bold red] {e}")
            return None

if __name__ == "__main__":
    # Тест
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="Фото дома")
    parser.add_argument("brick", help="Slug кирпича (напр. 'aalborg')")
    args = parser.parse_args()
    
    generator = FacadeGenerator()
    result = generator.generate_facade(args.image, args.brick, Path("output_facade.jpg"))
    
    if result:
        print("Готово! Сохранено в output_facade.jpg")
    else:
        print("Ошибка генерации.")
