"""
Модели данных для продуктов Vandersanden
"""

from typing import Optional
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class ProductColor(BaseModel):
    """Цвет продукта"""
    base_color: str = Field(..., description="Базовый цвет")
    additional_colors: list[str] = Field(default_factory=list, description="Дополнительные цвета")
    nuance: Optional[str] = Field(None, description="Нюанс (с нюансами / без нюансов)")


class JointOption(BaseModel):
    """Вариант шва (цвет затирки)"""
    name: str = Field(..., description="Название цвета шва")
    image_url: Optional[str] = Field(None, description="URL изображения")


class FormatOption(BaseModel):
    """Детальный вариант формата из таба 'Доступные форматы'"""
    name: str = Field(..., description="Название формата (Waaldikformaat, WF50mm и т.д.)")
    dimensions: Optional[str] = Field(None, description="Размеры")
    availability: Optional[str] = Field(None, description="Доступность (Без перфорации и т.д.)")
    pieces_per_m2: Optional[int] = Field(None, description="Штук на м²")
    pieces_per_pallet: Optional[int] = Field(None, description="Штук в палете")
    weight_kg: Optional[float] = Field(None, description="Вес в кг")
    image_url: Optional[str] = Field(None, description="URL изображения")


class ProductFormat(BaseModel):
    """Формат/размер продукта"""
    name: str = Field(..., description="Название формата (например, Waaldikformaat)")
    dimensions: str = Field(..., description="Размеры (например, +/- 215x100x65)")
    weight_kg: Optional[float] = Field(None, description="Вес в кг/шт")
    pieces_per_m2: Optional[int] = Field(None, description="Штук на м² (при шве 12мм)")
    pieces_per_pallet: Optional[int] = Field(None, description="Штук в палете")
    has_perforation: bool = Field(False, description="Есть перфорация")


class ProductImage(BaseModel):
    """Изображение продукта"""
    url: str = Field(..., description="URL изображения")
    alt: Optional[str] = Field(None, description="Alt текст")
    type: str = Field("main", description="Тип: main, texture, bim, project")


class ProductProject(BaseModel):
    """Проект с использованием продукта"""
    name: str = Field(..., description="Название проекта")
    url: str = Field(..., description="URL страницы проекта")
    location: Optional[str] = Field(None, description="Локация (страна)")


class Product(BaseModel):
    """Основная модель продукта Vandersanden"""
    
    # Идентификация
    article: str = Field(..., description="Артикул (например, 0124A0)")
    name: str = Field(..., description="Название (например, Lima)")
    slug: str = Field(..., description="URL slug")
    url: str = Field(..., description="Полный URL продукта")
    
    # Категория
    category: str = Field(..., description="Категория продукта")
    
    # Описание
    description: Optional[str] = Field(None, description="Описание продукта")
    raw_material: Optional[str] = Field(None, description="Сырьё (описание материалов)")
    
    # Характеристики
    texture: Optional[str] = Field(None, description="Текстура (Ручная формовка и т.д.)")
    color: Optional[ProductColor] = Field(None, description="Информация о цвете")
    
    # Форматы и размеры
    formats: list[ProductFormat] = Field(default_factory=list, description="Доступные форматы")
    
    # Медиа
    images: list[ProductImage] = Field(default_factory=list, description="Изображения")
    
    # Связанные проекты
    projects: list[ProductProject] = Field(default_factory=list, description="Проекты")
    
    # Похожие продукты
    similar_products: list[str] = Field(default_factory=list, description="Артикулы похожих продуктов")
    
    # Метаданные
    scraped_at: datetime = Field(default_factory=datetime.now, description="Время скраппинга")
    source_locale: str = Field("ru-ru", description="Язык источника")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_flat_dict(self) -> dict:
        """Преобразовать в плоский словарь для CSV/Excel"""
        return {
            "article": self.article,
            "name": self.name,
            "url": self.url,
            "category": self.category,
            "description": self.description,
            "texture": self.texture,
            "base_color": self.color.base_color if self.color else None,
            "additional_colors": ", ".join(self.color.additional_colors) if self.color else None,
            "color_nuance": self.color.nuance if self.color else None,
            "formats_count": len(self.formats),
            "formats": "; ".join([f.name for f in self.formats]),
            "projects_count": len(self.projects),
            "similar_count": len(self.similar_products),
            "scraped_at": self.scraped_at.isoformat(),
        }
