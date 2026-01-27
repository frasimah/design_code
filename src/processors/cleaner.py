"""
Очистка и нормализация данных
"""

from typing import Optional
from src.models.product import Product, ProductColor
from src.scraper.utils import normalize_color


class DataCleaner:
    """Класс для очистки и нормализации данных продуктов"""
    
    @staticmethod
    def clean_product(product: Product) -> Product:
        """
        Очистить и нормализовать данные продукта
        
        Args:
            product: Исходный продукт
            
        Returns:
            Очищенный продукт
        """
        # Нормализуем цвета
        if product.color:
            product.color = DataCleaner._normalize_color(product.color)
        
        # Убираем дубликаты в форматах
        seen_formats = set()
        unique_formats = []
        for fmt in product.formats:
            key = (fmt.name, fmt.dimensions)
            if key not in seen_formats:
                seen_formats.add(key)
                unique_formats.append(fmt)
        product.formats = unique_formats
        
        # Убираем дубликаты в похожих продуктах
        product.similar_products = list(set(product.similar_products))
        
        # Убираем собственный артикул из похожих
        if product.article in product.similar_products:
            product.similar_products.remove(product.article)
        
        return product
    
    @staticmethod
    def _normalize_color(color: ProductColor) -> ProductColor:
        """Нормализовать цвета"""
        return ProductColor(
            base_color=normalize_color(color.base_color),
            additional_colors=[normalize_color(c) for c in color.additional_colors],
            nuance=color.nuance
        )
    
    @staticmethod
    def clean_products(products: list[Product]) -> list[Product]:
        """
        Очистить список продуктов
        
        Args:
            products: Список продуктов
            
        Returns:
            Очищенный список
        """
        return [DataCleaner.clean_product(p) for p in products]
    
    @staticmethod
    def deduplicate(products: list[Product]) -> list[Product]:
        """
        Удалить дубликаты продуктов по артикулу
        
        Args:
            products: Список продуктов
            
        Returns:
            Список без дубликатов
        """
        seen = {}
        for product in products:
            if product.article not in seen:
                seen[product.article] = product
        return list(seen.values())
    
    @staticmethod
    def filter_valid(products: list[Product]) -> list[Product]:
        """
        Отфильтровать только валидные продукты
        
        Args:
            products: Список продуктов
            
        Returns:
            Отфильтрованный список
        """
        return [
            p for p in products
            if p.article and p.name and len(p.article) > 0
        ]
