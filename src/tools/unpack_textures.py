
import json
import zipfile
import shutil
from pathlib import Path
from rich.console import Console
from rich.progress import track
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import DATA_DIR

console = Console()

def unpack_textures():
    """Распаковывает ZIP архивы с текстурами"""
    downloads_dir = DATA_DIR / "downloads"
    
    # Ищем все ZIP файлы
    zip_files = list(downloads_dir.glob("**/*.zip"))
    console.print(f"[cyan]Найдено {len(zip_files)} архивов для распаковки[/cyan]")
    
    success = 0
    errors = 0
    
    for zip_path in track(zip_files, description="Распаковка..."):
        try:
            # Slug - это имя родительской папки
            slug = zip_path.parent.name
            
            # Целевая папка для текстур
            target_dir = zip_path.parent / "textures"
            target_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Фильтруем только картинки
                image_files = [f for f in zip_ref.namelist() if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                
                for file in image_files:
                    # Извлекаем только filename (плоская структура)
                    filename = Path(file).name
                    source = zip_ref.open(file)
                    target = open(target_dir / filename, "wb")
                    shutil.copyfileobj(source, target)
                    source.close()
                    target.close()
            
            success += 1
            
        except Exception as e:
            console.print(f"[red]Ошибка распаковки {zip_path.name}: {e}[/red]")
            errors += 1

    console.print(f"[green]Готово![/green] Распаковано: {success}, Ошибок: {errors}")

if __name__ == "__main__":
    unpack_textures()
