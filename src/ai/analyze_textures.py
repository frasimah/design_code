"""
Анализ текстур кирпича с помощью Gemini Vision
"""
import json
import time
import base64
import requests
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import google.generativeai as genai
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import GEMINI_API_KEY, DATA_DIR

console = Console()
genai.configure(api_key=GEMINI_API_KEY)

# Модель из README.md
model = genai.GenerativeModel("gemini-3-flash-preview")

TEXTURE_PROMPT = """Ты — эксперт по архитектурным материалам и дизайну.
Проанализируй изображение облицовочного кирпича и дай подробное описание его визуальных характеристик на русском языке.

Опиши следующее:
1. **Фактура поверхности:** (гладкая, шероховатая, рваная, зернистая, с трещинами, "водяная" water-struck, наличие песка).
2. **Ровность:** Оцени по шкале от 1 до 10, где 1 — очень рваная/неровная, 10 — идеально гладкая/геометричная.
3. **Имитация ручной кладки:** ЕСТЬ или НЕТ. Опиши, выглядит ли кирпич как старинный/ручной работы (неровные края, вмятины) или как индустриальный.
4. **Цветовая гамма:** (основной цвет, оттенки/нюансы, наличие подпалин или нагара, контрастность, равномерность цвета).
5. **Визуальный стиль:** (современный, лофт, состаренный/антик, классический, рустикальный, индустриальный).
6. **Эмоциональное восприятие:** (теплый/холодный, строгий/уютный, массивный/легкий).

Верни результат в формате JSON:
{
    "texture_description": "подробное описание фактуры...",
    "smoothness_score": 5, // Число 1-10
    "is_hand_molded_look": true, // true/false
    "hand_molded_details": "описание признаков ручной формовки...",
    "color_analysis": "анализ цвета...",
    "style_tags": ["лофт", "состаренный", ...],
    "visual_features": "дополнительные визуальные особенности"
}
"""

def get_image_data(url: str) -> bytes:
    """Скачивание изображения или чтение локального файла"""
    if url.startswith("http"):
        # В реальном проекте лучше использовать локальные файлы, если они есть
        # Здесь для упрощения качаем, но лучше брать из downloads/{slug}
        return requests.get(url).content
    else:
        with open(url, "rb") as f:
            return f.read()

def analyze_textures(max_products: int = None, resume_from: int = 0):
    catalog_path = DATA_DIR / "processed" / "full_catalog.json"
    output_path = DATA_DIR / "processed" / "texture_analysis.json"
    
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    
    if max_products:
        catalog = catalog[:max_products]
    
    # Загружаем существующие результаты
    results = {}
    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            results = json.load(f)
            
    console.print(f"[bold blue]Запуск анализа текстур для {len(catalog)} продуктов[/bold blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Анализ текстур...", total=len(catalog) - resume_from)
        
        for i, product in enumerate(catalog[resume_from:], start=resume_from):
            slug = product["slug"]
            progress.update(task, description=f"[cyan]{i+1}/{len(catalog)}: {slug}")
            
            # Форсируем переанализ, если есть новые текстуры, или если флаг --force
            # (Логику флага можно добавить, но пока просто проверяем, было ли это анализ низкого качества)
            # В данном контексте мы ХОТИМ перезаписать данные, если они были сделаны по плохим фото.
            # Но чтобы не тратить квоту зря, проверим.
            pass

            
            # Ищем лучшее изображение (из распакованных текстур)
            textures_dir = DATA_DIR / "downloads" / slug / "textures"
            img_path = None
            
            if textures_dir.exists():
                images = list(textures_dir.glob("*.jpg"))
                if images:
                    # Приоритет: WF, потом 01
                    images.sort(key=lambda p: (
                        0 if "WF" in p.name and "50mm" not in p.name else 1, 
                        0 if "_01_" in p.name else 1,
                        p.name
                    ))
                    img_path = images[0]
            
            # Если нет текстур, ишем скриншот-превью
            if not img_path:
                 img_files = list((DATA_DIR / "downloads" / slug).glob("*.jpg")) + \
                             list((DATA_DIR / "downloads" / slug).glob("*.png"))
                 if img_files:
                     img_path = img_files[0]
            
            local_img_path = None # Legacy variable, ensuring compatibility
            image_url = product.get("main_image")

            img_data = None
            if img_path:
                with open(img_path, "rb") as f:
                    img_data = f.read()
            elif image_url:
                try:
                    img_data = requests.get(image_url).content
                except:
                    pass
            
            if not img_data:
                console.print(f"\n[red]Нет изображения для {slug}[/red]")
                progress.advance(task)
                continue
                
            try:
                # Запрос к Gemini Vision
                content = [
                    TEXTURE_PROMPT,
                    {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(img_data).decode()
                    }
                ]
                
                response = model.generate_content(content)
                text = response.text
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                
                analysis = json.loads(text.strip())
                results[slug] = analysis
                
                # Сохраняем промежуточный результат
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                console.print(f"\n[red]Ошибка анализа {slug}: {e}[/red]")
            
            time.sleep(2) # Пауза для API
            progress.advance(task)

    console.print(f"\n[green]Анализ завершен! Сохранено в {output_path}[/green]")

if __name__ == "__main__":
    analyze_textures() # Все продукты
