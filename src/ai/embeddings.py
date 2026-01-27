"""
Создание и поиск эмбеддингов для продуктов кирпича
Использует Google text-embedding-004 + ChromaDB
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import GEMINI_API_KEY, DATA_DIR

console = Console()


class BrickEmbeddings:
    """Класс для работы с эмбеддингами продуктов"""
    
    def __init__(self, persist_directory: Optional[str] = None):
        """
        Инициализация ChromaDB и эмбеддинг-функции
        
        Args:
            persist_directory: Папка для хранения БД (по умолчанию data/embeddings)
        """
        if persist_directory is None:
            persist_directory = str(DATA_DIR / "embeddings")
        
        # Инициализируем ChromaDB с персистентным хранилищем
        self.client = chromadb.PersistentClient(path=persist_directory)
        
import os
import requests
from chromadb import Documents, EmbeddingFunction, Embeddings

class ProxiedGeminiEmbeddingFunction(EmbeddingFunction):
    """Custom Embedding Function using REST API directly to support SOCKS proxy"""
    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004"):
        self.api_key = api_key
        self.model_name = model_name
        self.url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:embedContent?key={api_key}"

    def __call__(self, input: Documents) -> Embeddings:
        # Batching is better, but for simplicity let's do one by one or small batches
        # API supports batchEmbedContents but here we implement single embed per doc for safety
        # or we can iterate. Input is a list of strings.
        embeddings = []
        for text in input:
            payload = {
                "model": self.model_name,
                "content": {"parts": [{"text": text}]}
            }
            try:
                response = requests.post(self.url, json=payload, timeout=20)
                if response.ok:
                    data = response.json()
                    # Extract embedding. Format: {'embedding': {'values': [...]}}
                    emb = data.get('embedding', {}).get('values', [])
                    embeddings.append(emb)
                else:
                    print(f"Error embedding text: {response.text}", file=sys.stderr)
                    # return empty list or zero vector to avoid crash? 
                    # specific length needed? 768 usually.
                    embeddings.append([0.0]*768) 
            except Exception as e:
                print(f"Exception embedding text: {e}", file=sys.stderr)
                embeddings.append([0.0]*768)
        return embeddings

class BrickEmbeddings:
    """Класс для работы с эмбеддингами продуктов"""
    
    def __init__(self, persist_directory: Optional[str] = None):
        """
        Инициализация ChromaDB и эмбеддинг-функции
        
        Args:
            persist_directory: Папка для хранения БД (по умолчанию data/embeddings)
        """
        if persist_directory is None:
            persist_directory = str(DATA_DIR / "embeddings")
        
        # Инициализируем ChromaDB с персистентным хранилищем
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Используем Custom embedding function для поддержки Proxy
        self.embedding_fn = ProxiedGeminiEmbeddingFunction(
            api_key=GEMINI_API_KEY,
            model_name="models/text-embedding-004"
        )
        
        # Получаем или создаем коллекцию
        self.collection = self.client.get_or_create_collection(
            name="vandersanden_bricks",
            embedding_function=self.embedding_fn,
            metadata={"description": "Каталог облицовочного кирпича Vandersanden"}
        )
        
        # Загружаем анализ текстур если есть
        texture_path = DATA_DIR / "processed" / "texture_analysis.json"
        if texture_path.exists():
            with open(texture_path, 'r', encoding='utf-8') as f:
                self.texture_analysis = json.load(f)
        else:
            self.texture_analysis = {}
            
        console.print(f"[green]✓ ChromaDB инициализирован[/green]")
        console.print(f"  Путь: {persist_directory}")
        console.print(f"  Документов в коллекции: {self.collection.count()}")
        console.print(f"  Доступно анализов текстур: {len(self.texture_analysis)}")
    
    def _product_to_text(self, product: Dict) -> str:
        """Преобразует продукт в текстовое описание для эмбеддинга"""
        slug = product.get('slug')
        parts = []
        
        # 1. Основная информация (Высокий приоритет для текстового поиска)
        parts.append(f"Название: {product.get('name', 'N/A')}")
        parts.append(f"Артикул: {product.get('article', 'N/A')}")
        
        # Цвет - критически важен
        color = product.get('color', {})
        if color:
            color_parts = []
            if color.get('base_color'):
                color_parts.append(f"базовый цвет: {color['base_color']}")
            if color.get('nuance'):
                color_parts.append(f"нюанс: {color['nuance']}")
            if color.get('additional_colors'):
                color_parts.append(f"доп. цвета: {', '.join(color['additional_colors'])}")
            if color_parts:
                parts.append(f"Цвет: {', '.join(color_parts)}")

        parts.append(f"Текстура: {product.get('texture', 'N/A')}")

        # 2. Данные из анализа текстур (Визуальный поиск)
        if slug in self.texture_analysis:
            tex = self.texture_analysis[slug]
            if tex.get('texture_description'):
                parts.append(f"Визуальное описание: {tex['texture_description']}")
            if tex.get('style_tags'):
                parts.append(f"Стиль: {', '.join(tex['style_tags'])}")
            if tex.get('visual_features'):
                parts.append(f"Особенности: {tex['visual_features']}")
            if tex.get('color_analysis'):
                 parts.append(f"Детальный цвет: {tex['color_analysis']}")
        
        # Описание
        if product.get('description'):
            parts.append(f"Описание: {product['description']}")
        
        # Форматы
        formats = product.get('available_formats', [])
        if formats:
            format_strs = []
            for fmt in formats:
                name = fmt.get('name', '')
                dims = fmt.get('dimensions', '')
                weight = fmt.get('weight', '')
                format_strs.append(f"{name}: {dims}, {weight}")
            parts.append(f"Форматы: {'; '.join(format_strs)}")
        
        # Швы
        joints = product.get('joints', [])
        if joints:
            joint_names = [j.get('name', '') for j in joints if j.get('name')]
            parts.append(f"Швы: {', '.join(joint_names)}")
        
        # Данные из PDF (технические характеристики)
        pdf_path = product.get('parsed_pdf_data')
        if pdf_path and Path(pdf_path).exists():
            try:
                with open(pdf_path, 'r', encoding='utf-8') as f:
                    pdf_data = json.load(f)
                for doc in pdf_data.get('documents', []):
                    parsed = doc.get('parsed_data', {})
                    if 'error' in parsed:
                        continue
                    
                    # Технические характеристики
                    tech = parsed.get('технические_характеристики', {})
                    if tech:
                        if tech.get('прочность_на_сжатие'):
                            parts.append(f"Прочность на сжатие: {tech['прочность_на_сжатие']}")
                        if tech.get('морозостойкость'):
                            parts.append(f"Морозостойкость: {tech['морозостойкость']}")
                        if tech.get('водопоглощение'):
                            parts.append(f"Водопоглощение: {tech['водопоглощение']}")
                        if tech.get('теплопроводность'):
                            parts.append(f"Теплопроводность: {tech['теплопроводность']}")
                        if tech.get('класс_огнестойкости'):
                            parts.append(f"Класс огнестойкости: {tech['класс_огнестойкости']}")
                        if tech.get('плотность'):
                            parts.append(f"Плотность: {tech['плотность']}")
            except Exception:
                pass
        
        return "\n".join(parts)
    
    def index_catalog(self, catalog_path: Optional[Path] = None, force_reindex: bool = False):
        """
        Индексирует весь каталог продуктов
        
        Args:
            catalog_path: Путь к full_catalog.json
            force_reindex: Принудительно переиндексировать всё
        """
        if catalog_path is None:
            catalog_path = DATA_DIR / "processed" / "full_catalog.json"
        
        console.print(f"[cyan]Загрузка каталога: {catalog_path}[/cyan]")
        
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        
        console.print(f"[cyan]Найдено {len(catalog)} продуктов[/cyan]")
        
        if force_reindex:
            console.print("[yellow]Очистка существующих эмбеддингов...[/yellow]")
            # Удаляем все документы
            existing = self.collection.get()
            if existing['ids']:
                self.collection.delete(ids=existing['ids'])
        
        # Получаем уже проиндексированные
        existing_ids = set(self.collection.get()['ids'])
        
        indexed = 0
        skipped = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Индексация...", total=len(catalog))
            
            for product in catalog:
                slug = product.get('slug')
                
                if not slug:
                    progress.advance(task)
                    continue
                
                # Пропускаем если уже индексирован
                if slug in existing_ids and not force_reindex:
                    skipped += 1
                    progress.advance(task)
                    continue
                
                # Создаем текстовое представление
                text = self._product_to_text(product)
                
                # Метаданные для фильтрации
                metadata = {
                    "slug": slug,
                    "name": product.get('name', ''),
                    "article": product.get('article', ''),
                    "texture": product.get('texture', ''),
                    "base_color": product.get('color', {}).get('base_color', ''),
                    "nuance": product.get('color', {}).get('nuance', ''),
                    "url": product.get('url', ''),
                }
                
                # Добавляем в коллекцию
                self.collection.upsert(
                    ids=[slug],
                    documents=[text],
                    metadatas=[metadata]
                )
                
                indexed += 1
                progress.update(task, description=f"[cyan]{slug}")
                progress.advance(task)
        
        console.print(f"\n[bold green]✓ Индексация завершена![/bold green]")
        console.print(f"  Проиндексировано: [green]{indexed}[/green]")
        console.print(f"  Пропущено (уже есть): [yellow]{skipped}[/yellow]")
        console.print(f"  Всего в коллекции: [cyan]{self.collection.count()}[/cyan]")
    
    def search(self, query: str, n_results: int = 5, where: Optional[Dict] = None) -> List[Dict]:
        """
        Поиск похожих продуктов по текстовому запросу
        
        Args:
            query: Текст запроса
            n_results: Количество результатов
            where: Фильтр метаданных (ChromaDB syntax)
            
        Returns:
            Список найденных продуктов с метаданными и расстоянием
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        products = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                products.append({
                    "slug": results['ids'][0][i],
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i]
                })
        
        return products
    
    def get_product(self, slug: str) -> Optional[Dict]:
        """Получить продукт по slug"""
        result = self.collection.get(ids=[slug], include=["documents", "metadatas"])
        if result['ids']:
            return {
                "slug": result['ids'][0],
                "document": result['documents'][0],
                "metadata": result['metadatas'][0]
            }
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Индексация продуктов в ChromaDB")
    parser.add_argument("--force", action="store_true", help="Принудительно переиндексировать")
    parser.add_argument("--search", type=str, help="Тестовый поиск")
    
    args = parser.parse_args()
    
    embeddings = BrickEmbeddings()
    
    if args.search:
        console.print(f"\n[cyan]Поиск: {args.search}[/cyan]\n")
        results = embeddings.search(args.search, n_results=3)
        for i, r in enumerate(results, 1):
            console.print(f"[bold]{i}. {r['metadata']['name']}[/bold] ({r['slug']})")
            console.print(f"   Артикул: {r['metadata']['article']}")
            console.print(f"   Цвет: {r['metadata']['base_color']}")
            console.print(f"   Расстояние: {r['distance']:.4f}")
            console.print()
    else:
        embeddings.index_catalog(force_reindex=args.force)
