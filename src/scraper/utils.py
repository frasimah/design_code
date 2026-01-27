"""
Вспомогательные функции для скраппинга
"""

import re
from typing import Optional
from urllib.parse import urljoin, urlparse


def clean_text(text: Optional[str]) -> Optional[str]:
    """
    Очистить текст от лишних пробелов и переносов строк
    
    Args:
        text: Исходный текст
        
    Returns:
        Очищенный текст или None
    """
    if not text:
        return None
    # Убираем множественные пробелы и переносы
    cleaned = re.sub(r'\s+', ' ', text.strip())
    return cleaned if cleaned else None


def extract_article(text: str) -> Optional[str]:
    """
    Извлечь артикул из текста (формат: XXXX[A-Z]X)
    
    Args:
        text: Текст содержащий артикул
        
    Returns:
        Артикул или None
    """
    match = re.search(r'\b(\d{4}[A-Z]\d)\b', text)
    return match.group(1) if match else None


def extract_dimensions(text: str) -> Optional[str]:
    """
    Извлечь размеры из текста (формат: XXXxXXXxXX)
    
    Args:
        text: Текст с размерами
        
    Returns:
        Строка с размерами
    """
    match = re.search(r'(\+?/?-?\s*\d+\s*x\s*\d+\s*x\s*\d+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def extract_weight(text: str) -> Optional[float]:
    """
    Извлечь вес из текста
    
    Args:
        text: Текст с весом (например, "2.16 кг/шт")
        
    Returns:
        Вес в кг
    """
    match = re.search(r'(\d+[.,]\d+|\d+)\s*(?:кг|kg)', text, re.IGNORECASE)
    if match:
        weight_str = match.group(1).replace(',', '.')
        return float(weight_str)
    return None


def extract_number(text: str) -> Optional[int]:
    """
    Извлечь целое число из текста
    
    Args:
        text: Текст с числом
        
    Returns:
        Число
    """
    match = re.search(r'(\d+)', text)
    return int(match.group(1)) if match else None


def make_absolute_url(url: str, base_url: str) -> str:
    """
    Преобразовать относительный URL в абсолютный
    
    Args:
        url: Относительный или абсолютный URL
        base_url: Базовый URL
        
    Returns:
        Абсолютный URL
    """
    if url.startswith(('http://', 'https://')):
        return url
    return urljoin(base_url, url)


def extract_slug_from_url(url: str) -> str:
    """
    Извлечь slug из URL продукта
    
    Args:
        url: URL продукта
        
    Returns:
        Slug (последняя часть пути)
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip('/')
    return path.split('/')[-1]


def normalize_color(color: str) -> str:
    """
    Нормализовать название цвета
    
    Args:
        color: Название цвета
        
    Returns:
        Нормализованное название
    """
    color_map = {
        'белый': 'white',
        'серый': 'grey',
        'бежевый': 'beige',
        'жёлтый': 'yellow',
        'желтый': 'yellow',
        'розовый': 'pink',
        'оранжевый': 'orange',
        'красный': 'red',
        'пурпурный': 'purple',
        'зеленый': 'green',
        'зелёный': 'green',
        'коричневый': 'brown',
        'голубой': 'blue',
        'чёрный': 'black',
        'черный': 'black',
    }
    
    color_lower = color.strip().lower()
    return color_map.get(color_lower, color_lower)
