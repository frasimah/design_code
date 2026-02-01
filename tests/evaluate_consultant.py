"""
Скрипт для оценки качества ответов AI-консультанта
"""
import sys
import time
from pathlib import Path

TEST_CASES = [
    {
        "id": 1,
        "query": "Пористый кирпич с фактурой имитирующей ручную формовку",
        "description": "Тест на понимание текстур формовки"
    },
    {
        "id": 2,
        "query": "Порекомендуй белый кирпич для фасада",
        "description": "Поиск по цвету"
    },
    {
        "id": 3,
        "query": "Максимально технологичный современный кирпич для стиля хай-тек",
        "description": "Поиск по стилю (хай-тек) и абстрактным понятиям"
    },
    {
        "id": 4,
        "query": "Найди мне черный кирпич",
        "description": "Простой поиск по цвету"
    },
    {
        "id": 5,
        "query": "Кирпич для южного жаркого климата",
        "description": "Понимание климатических условий (теплопроводность, перегрев)"
    },
    {
        "id": 6,
        "query": "Интерьерный кирпич с яркой выразительной фактурой",
        "description": "Интерьерное применение и эстетика"
    },
    {
        "id": 7,
        "query": "Кирпич для здания вблизи автострады, где много пыли и грязи",
        "description": "Практичность, самоочищение, плотность"
    }
]

def run_evaluation():
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    from rich.console import Console
    from src.ai.consultant import BrickConsultant

    console = Console()
    console.print("[bold blue]Запуск оценки AI-консультанта...[/bold blue]\n")
    
    start_init = time.time()
    consultant = BrickConsultant()
    console.print(f"[green]Инициализация: {time.time() - start_init:.2f} сек[/green]\n")
    
    results = []
    
    for test in TEST_CASES:
        console.print(f"[bold cyan]Тест {test['id']}: {test['description']}[/bold cyan]")
        console.print(f"Запрос: [italic]'{test['query']}'[/italic]")
        
        start = time.time()
        response = consultant.answer(test['query'])
        duration = time.time() - start
        
        console.print(f"Ответ ({duration:.2f} сек):")
        console.print(f"[white]{response}[/white]")
        console.print("-" * 50 + "\n")
        
        results.append({
            "test": test,
            "response": response,
            "duration": duration
        })

if __name__ == "__main__":
    run_evaluation()
