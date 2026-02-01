
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.routes.products import get_catalog
from src.ai.embeddings import BrickEmbeddings
from rich.console import Console

console = Console()

def run_reindex():
    console.print("[bold blue]Начало полного переиндексирования каталога...[/bold blue]")
    
    # 1. Получаем объединенный каталог
    catalog = get_catalog()
    console.print(f"Загружено [green]{len(catalog)}[/green] товаров из всех источников.")
    
    # 2. Инициализируем эмбеддинги
    embeddings = BrickEmbeddings()
    
    # 3. Запускаем индексацию
    # Force reindex to ensure absolute clean slate
    embeddings.index_catalog(products_list=catalog, force_reindex=True)
    
    console.print("[bold green]✓ Переиндексация завершена успешно![/bold green]")

if __name__ == "__main__":
    run_reindex()
