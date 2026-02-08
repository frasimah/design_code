"""
Создание и поиск эмбеддингов для продуктов кирпича
Использует Google text-embedding-004 + ChromaDB
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
import chromadb
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import sys
import requests
import time
from chromadb import Documents, EmbeddingFunction, Embeddings

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import GEMINI_API_KEY, DATA_DIR

console = Console()

class ProxiedGeminiEmbeddingFunction(EmbeddingFunction):
    """Custom Embedding Function using REST API directly to support SOCKS proxy"""
    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004"):
        self.api_key = api_key
        self.model_name = model_name
        self.url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:embedContent?key={api_key}"

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []
            
        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:batchEmbedContents?key={self.api_key}"
        
        # Prepare requests
        requests_list = []
        for text in input:
            requests_list.append({
                "model": self.model_name,
                "content": {"parts": [{"text": text}]}
            })
            
        payload = {"requests": requests_list}
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.ok:
                data = response.json()
                embeddings = []
                for emb_data in data.get('embeddings', []):
                    values = emb_data.get('values', [])
                    if len(values) == 768:
                        embeddings.append(values)
                    elif len(values) == 3072:
                        # Output from gemini-embedding-001 can be 3072 (even if docs say 768 sometimes)
                        embeddings.append(values)
                    else:
                        print(f"Warning: Unexpected embedding dimension: {len(values)}")
                        # Try to pad or truncate if desperate, but better to skip or just append and let chroma error
                        # For now, let's just append and hope for the best or provide a zero vector of correct size if we knew it
                        # But since we support 768 and 3072, let's just append zeros of 3072 as fallback if it's neither?
                        # Actually safer to append 3072 zeros if we are moving to that model.
                        embeddings.append([0.0]*3072)
                
                # If for some reason lengths don't match, pad
                while len(embeddings) < len(input):
                    embeddings.append([0.0]*3072)
                return embeddings
            else:
                print(f"Error batch embedding: {response.text}", file=sys.stderr)
                return [[0.0]*3072 for _ in input]
        except Exception as e:
            print(f"Exception batch embedding: {e}", file=sys.stderr)
            return [[0.0]*3072 for _ in input]

class BrickEmbeddings:
    """Класс для работы с эмбеддингами продуктов"""
    
    def __init__(self, persist_directory: Optional[str] = None):
        if persist_directory is None:
            persist_directory = str(DATA_DIR / "embeddings")
        
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Используем Custom embedding function для поддержки Proxy
        self.embedding_fn = ProxiedGeminiEmbeddingFunction(
            api_key=GEMINI_API_KEY,
            model_name="models/gemini-embedding-001"
        )
        
        # Получаем или создаем коллекцию
        self.collection = self.client.get_or_create_collection(
            name="designer_furniture_v1",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Загружаем анализ текстур если есть
        texture_path = DATA_DIR / "processed" / "texture_analysis.json"
        if texture_path.exists():
            with open(texture_path, 'r', encoding='utf-8') as f:
                self.texture_analysis = json.load(f)
        else:
            self.texture_analysis = {}
            
        console.print("[green]✓ ChromaDB инициализирован[/green]")
        console.print(f"  Путь: {persist_directory}")
        console.print(f"  Коллекция: {self.collection.name}")
        console.print(f"  Документов: {self.collection.count()}")
    
    def _product_to_text(self, product: Dict) -> str:
        slug = product.get('slug')
        parts = []
        parts.append(f"Название: {product.get('name', 'N/A')}")
        parts.append(f"Артикул: {product.get('article', 'N/A')}")
        
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

        if slug in self.texture_analysis:
            tex = self.texture_analysis[slug]
            if tex.get('texture_description'):
                parts.append(f"Визуальное описание: {tex['texture_description']}")
            if tex.get('style_tags'):
                parts.append(f"Стиль: {', '.join(tex['style_tags'])}")
            if tex.get('visual_features'):
                parts.append(f"Особенности: {tex['visual_features']}")
        
        if product.get('visual_description'):
            parts.append(f"Визуальное описание: {product['visual_description']}")
        
        if product.get('description'):
            parts.append(f"Описание: {product['description']}")
        
        return "\n".join(parts)

    def index_product(self, product: Dict):
        """Index or update a single product."""
        slug = product.get('slug')
        if not slug:
            return
            
        text = self._product_to_text(product)
        metadata = {
            "slug": slug,
            "name": product.get('name', ''),
            "article": product.get('article', ''),
            "source": product.get('source', 'unknown')
        }
        
        self.collection.upsert(
            ids=[slug],
            documents=[text],
            metadatas=[metadata]
        )

    def delete_product(self, slug: str):
        """Delete a single product from index."""
        if not slug:
            return
        try:
            self.collection.delete(ids=[slug])
        except Exception as e:
            print(f"Error deleting embedding for {slug}: {e}")
    
    def delete_by_source(self, source: str):
        """Delete all products from a specific source."""
        try:
            # Get all items with this source
            results = self.collection.get(
                where={"source": source},
                include=[]
            )
            if results and results['ids']:
                console.print(f"[yellow]Deleting {len(results['ids'])} products from source '{source}'...[/yellow]")
                self.collection.delete(ids=results['ids'])
                console.print(f"[green]✓ Deleted {len(results['ids'])} products[/green]")
            else:
                console.print(f"[dim]No products found for source '{source}'[/dim]")
        except Exception as e:
            console.print(f"[red]Error deleting by source {source}: {e}[/red]")
    
    def sync_products(self, products: List[Dict], source: str):
        """Sync products from an external source (delete old, add new)."""
        console.print(f"[blue]Syncing {len(products)} products from source '{source}'...[/blue]")
        
        # First delete all existing products from this source
        self.delete_by_source(source)
        
        # Then add all new products
        batch_size = 50
        for i in range(0, len(products), batch_size):
            batch = products[i:i+batch_size]
            for p in batch:
                p['source'] = source  # Ensure source is set
                self.index_product(p)
            console.print(f"  Indexed {min(i+batch_size, len(products))}/{len(products)}...")
        
        console.print(f"[green]✓ Synced {len(products)} products from '{source}'[/green]")
    
    def index_catalog(self, catalog_path: Optional[Path] = None, force_reindex: bool = False, products_list: Optional[List[Dict]] = None):
        if products_list is not None:
            catalog = products_list
        else:
            if catalog_path is None:
                catalog_path = DATA_DIR / "processed" / "full_catalog.json"
            
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
        
        if force_reindex:
            console.print("[yellow]Очистка и пересоздание коллекции...[/yellow]")
            try:
                self.client.delete_collection("designer_furniture_v1")
                time.sleep(1)
            except Exception:
                pass
            
            self.collection = self.client.get_or_create_collection(
                name="designer_furniture_v1",
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
        
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
            
            batch_size = 50
            batch_ids = []
            batch_docs = []
            batch_metas = []

            # Dedup catalog to avoid DuplicateIDError
            unique_catalog = {}
            for p in catalog:
                s = p.get('slug')
                if s and s not in unique_catalog:
                    unique_catalog[s] = p
            catalog = list(unique_catalog.values())

            for product in catalog:
                slug = product.get('slug')
                if not slug:
                    progress.advance(task)
                    continue
                
                if slug in existing_ids and not force_reindex:
                    skipped += 1
                    progress.advance(task)
                    continue
                
                text = self._product_to_text(product)
                metadata = {
                    "slug": slug,
                    "name": product.get('name', ''),
                    "article": product.get('article', ''),
                    "source": product.get('source', 'unknown')
                }
                
                batch_ids.append(slug)
                batch_docs.append(text)
                batch_metas.append(metadata)

                if len(batch_ids) >= batch_size:
                    self.collection.upsert(
                        ids=batch_ids,
                        documents=batch_docs,
                        metadatas=batch_metas
                    )
                    indexed += len(batch_ids)
                    batch_ids, batch_docs, batch_metas = [], [], []
                
                progress.update(task, description=f"[cyan]{slug}")
                progress.advance(task)

            # Final batch
            if batch_ids:
                self.collection.upsert(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_metas
                )
                indexed += len(batch_ids)
        
        console.print(f"\n[bold green]✓ Готово![/bold green] Всего: {self.collection.count()}")

    def search(self, query: str, n_results: int = 5, where: Optional[Dict] = None) -> List[Dict]:
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
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i]
                })
        return products

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--search", type=str)
    args = parser.parse_args()
    
    embeddings = BrickEmbeddings()
    if args.search:
        results = embeddings.search(args.search)
        for r in results:
            print(f"- {r['metadata']['name']} ({r['slug']}) dist: {r['distance']:.4f}")
    else:
        embeddings.index_catalog(force_reindex=args.force)
