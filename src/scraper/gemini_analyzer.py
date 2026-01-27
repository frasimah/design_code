"""
Gemini Vision Analyzer - анализ скриншотов страниц с помощью Gemini AI
"""

import base64
import json
import httpx
from pathlib import Path
from typing import Optional, Any
from rich.console import Console

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])


console = Console()


class GeminiVisionAnalyzer:
    """Анализатор изображений с помощью Google Gemini API"""
    
    API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    MODEL = "gemini-3-flash-preview"  # Указанная пользователем модель
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.Client(timeout=60)
    
    def analyze_image(
        self,
        image_path: str | Path,
        prompt: str,
        json_output: bool = True
    ) -> dict | str:
        """
        Анализировать изображение с помощью Gemini
        
        Args:
            image_path: Путь к изображению (PNG, JPG, WEBP)
            prompt: Промпт для анализа
            json_output: Ожидать JSON ответ
            
        Returns:
            Результат анализа (dict если json_output=True)
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Читаем и кодируем изображение в base64
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        # Определяем MIME тип
        suffix = image_path.suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        mime_type = mime_types.get(suffix, "image/png")
        
        # Формируем запрос
        url = f"{self.API_URL}/{self.MODEL}:generateContent?key={self.api_key}"
        
        system_prompt = ""
        if json_output:
            system_prompt = "You must respond ONLY with valid JSON, no markdown, no explanation, just pure JSON object."
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_data
                            }
                        },
                        {
                            "text": f"{system_prompt}\n\n{prompt}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4096,
            }
        }
        
        console.log(f"[blue]Gemini analyzing image:[/blue] {image_path.name}")
        
        response = self.client.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # Извлекаем текст ответа
        try:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            console.log(f"[red]Gemini response error:[/red] {result}")
            raise ValueError(f"Failed to parse Gemini response: {e}")
        
        # Парсим JSON если нужно
        if json_output:
            # Убираем markdown обёртку если есть
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                console.log(f"[yellow]JSON parse warning:[/yellow] {e}")
                console.log(f"[yellow]Raw text:[/yellow] {text[:500]}")
                return {"raw_text": text, "parse_error": str(e)}
        
        return text
    
    def analyze_product_tabs(self, screenshot_path: str | Path) -> dict:
        """
        Анализировать скриншот страницы продукта для извлечения данных табов
        
        Args:
            screenshot_path: Путь к скриншоту
            
        Returns:
            Словарь с joints и formats
        """
        prompt = """Analyze this screenshot of a Vandersanden brick product page.
        
Look for the "Форматы и варианты" (Formats and Options) section with tabs:
1. "швы" (joints/mortar colors) - list of joint color options
2. "Доступные форматы" (Available formats) - list of brick format options with specifications

Extract the following data and return as JSON:

{
    "joints": [
        {"name": "joint color name in Russian", "visible": true/false}
    ],
    "formats": [
        {
            "name": "format name (e.g. Waaldikformaat, WF50mm)",
            "dimensions": "size in mm (e.g. +/- 215x100x65)",
            "weight_kg": number or null,
            "pieces_per_m2": number or null,
            "availability": "string or null"
        }
    ],
    "active_tab": "which tab is currently active: joints or formats"
}

If you cannot find this section or data, return empty arrays.
Be precise with Russian text - copy it exactly as shown."""

        return self.analyze_image(screenshot_path, prompt, json_output=True)
    
    def analyze_product_info(self, screenshot_path: str | Path, text_content: Optional[str] = None) -> dict:
        """
        Анализировать скриншот и текст для извлечения основной информации о продукте
        
        Args:
            screenshot_path: Путь к скриншоту
            text_content: Текстовое содержимое страницы (опционально)
            
        Returns:
            Словарь с информацией о продукте
        """
        prompt = """Analyze this screenshot of a Vandersanden brick product page."""
        
        if text_content:
            prompt += f"\n\nHere is the text content from the page:\n\n{text_content}\n"
            prompt += "\nUse both the image and the text to extract the most accurate information.\n"
            
        prompt += """
Extract the following product information and return as JSON:

{
    "name": "product name",
    "article": "article code (format like 0124A0)",
    "texture": "texture type (e.g. Ручная формовка)",
    "color": {
        "base_color": "main color (usually one word)",
        "additional_colors": ["list", "of", "secondary", "colors"],
        "nuance": "detailed nuance description (e.g. 'purple with blue accents')"
    },
    "raw_material": "material description if visible",
    "description": "any product description text"
}

Return null for fields you cannot find. Be precise with Russian text.
"""

        return self.analyze_image(screenshot_path, prompt, json_output=True)
    
    def close(self):
        """Закрыть HTTP клиент"""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Глобальный экземпляр для удобства
_analyzer: Optional[GeminiVisionAnalyzer] = None


def get_gemini_analyzer(api_key: Optional[str] = None) -> GeminiVisionAnalyzer:
    """
    Получить экземпляр GeminiVisionAnalyzer
    
    Args:
        api_key: API ключ (если None, берётся из переменной окружения)
        
    Returns:
        GeminiVisionAnalyzer
    """
    global _analyzer
    
    if _analyzer is None:
        import os
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY not provided and not found in environment")
        _analyzer = GeminiVisionAnalyzer(key)
    
    return _analyzer
