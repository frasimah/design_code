"""
Скрипт для связывания основного каталога с обработанными PDF данными.
Добавляет поле 'parsed_pdf_data' в каждый продукт в full_catalog.json.
"""

import json
from pathlib import Path
import sys

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATA_DIR
from rich.console import Console

console = Console()

def link_pdfs():
    catalog_path = DATA_DIR / "processed" / "full_catalog.json"
    pdfs_dir = DATA_DIR / "processed" / "pdfs"
    
    if not catalog_path.exists():
        console.print("[red]Каталог не найден![/red]")
        return
        
    console.print("[cyan]Загрузка каталога...[/cyan]")
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
        
    linked_count = 0
    missing_count = 0
    
    for product in catalog:
        slug = product.get("slug")
        if not slug:
            continue
            
        # Путь к файлу с распарсенными PDF
        pdf_data_path = pdfs_dir / f"{slug}.json"
        
        if pdf_data_path.exists():
            # Добавляем ссылку на данные
            product["parsed_pdf_data"] = str(pdf_data_path.absolute())
            linked_count += 1
        else:
            product["parsed_pdf_data"] = None
            missing_count += 1
            
    # Сохраняем обновленный каталог
    console.print(f"[cyan]Сохранение обновленного каталога...[/cyan]")
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        
    console.print(f"[bold green]✓ Готово![/bold green]")
    console.print(f"  Связано продуктов: [green]{linked_count}[/green]")
    console.print(f"  Ожидают парсинга: [yellow]{missing_count}[/yellow]")
    console.print(f"  Каталог обновлен: {catalog_path}")

if __name__ == "__main__":
    link_pdfs()
