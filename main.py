#!/usr/bin/env python3
"""
Vandersanden Scraper - Точка входа
"""

import asyncio
from functools import wraps
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from config.settings import VandersandenConfig, PROCESSED_DATA_DIR
from src.scraper.products import VandersandenProductScraper
from src.processors.cleaner import DataCleaner
from src.processors.exporter import DataExporter


console = Console()


def async_command(f):
    """Декоратор для async click команд"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Vandersanden Scraper - инструмент для сбора данных о продуктах"""
    pass


@cli.command()
@click.option(
    "--category", "-c",
    default="facade_bricks",
    type=click.Choice(["facade_bricks", "pavers", "facade_panels"]),
    help="Категория продуктов для скраппинга"
)
@click.option(
    "--output", "-o",
    default="products",
    help="Имя выходного файла (без расширения)"
)
@click.option(
    "--format", "-f",
    default="json",
    type=click.Choice(["json", "csv", "excel"]),
    help="Формат экспорта"
)
@click.option(
    "--limit", "-l",
    default=None,
    type=int,
    help="Ограничить количество продуктов (для тестирования)"
)
@async_command
async def scrape(category: str, output: str, format: str, limit: int):
    """Скраппинг продуктов Vandersanden"""
    
    console.print(f"\n[bold blue]🧱 Vandersanden Scraper[/bold blue]")
    console.print(f"Category: [cyan]{category}[/cyan]")
    console.print(f"Output: [cyan]{output}.{format}[/cyan]\n")
    
    async with VandersandenProductScraper(category=category) as scraper:
        # Получаем ссылки
        links = await scraper.get_product_links()
        
        if limit:
            links = links[:limit]
            console.print(f"[yellow]Limited to {limit} products[/yellow]\n")
        
        # Скраппим продукты
        products = await scraper.scrape_batch(links)
    
    # Очищаем данные
    products = DataCleaner.clean_products(products)
    products = DataCleaner.deduplicate(products)
    products = DataCleaner.filter_valid(products)
    
    # Экспортируем
    exporter = DataExporter()
    output_path = exporter.export(products, output, format)
    
    # Показываем сводку
    _show_summary(products)
    
    console.print(f"\n[bold green]✓ Done![/bold green] Saved to: {output_path}")


@cli.command()
@click.argument("url")
@click.option("--output", "-o", default=None, help="Файл для сохранения")
@async_command
async def scrape_one(url: str, output: str):
    """Скраппинг одного продукта по URL"""
    
    console.print(f"\n[bold blue]🧱 Scraping single product[/bold blue]")
    console.print(f"URL: [cyan]{url}[/cyan]\n")
    
    async with VandersandenProductScraper() as scraper:
        product = await scraper.scrape(url)
    
    if product:
        product = DataCleaner.clean_product(product)
        
        # Показываем информацию
        console.print(f"[green]Name:[/green] {product.name}")
        console.print(f"[green]Article:[/green] {product.article}")
        console.print(f"[green]Texture:[/green] {product.texture}")
        console.print(f"[green]Formats:[/green] {len(product.formats)}")
        console.print(f"[green]Projects:[/green] {len(product.projects)}")
        
        if output:
            exporter = DataExporter()
            exporter.export([product], output, "json")
    else:
        console.print("[red]Failed to scrape product[/red]")


@cli.command()
@click.argument("url")
@click.option("--output", "-o", default=None, help="Файл для сохранения")
@click.option("--headless/--no-headless", default=True, help="Запуск браузера в фоне")
@async_command
async def browser_scrape(url: str, output: str, headless: bool):
    """Скраппинг с браузером (для табов швы/форматы)"""
    from src.scraper.browser_scraper import BrowserProductScraper
    import json
    
    console.print(f"\n[bold blue]🧱 Browser scraping (with tabs)[/bold blue]")
    console.print(f"URL: [cyan]{url}[/cyan]")
    console.print(f"Headless: [cyan]{headless}[/cyan]\n")
    
    async with BrowserProductScraper(headless=headless) as scraper:
        product_data = await scraper.scrape_product(url)
    
    if product_data:
        # Показываем информацию
        console.print(f"[green]Name:[/green] {product_data.get('name')}")
        console.print(f"[green]Article:[/green] {product_data.get('article')}")
        console.print(f"[green]Texture:[/green] {product_data.get('texture')}")
        
        # Швы
        joints = product_data.get('joints', [])
        console.print(f"\n[bold yellow]Швы ({len(joints)}):[/bold yellow]")
        for j in joints:
            console.print(f"  • {j['name']}")
        
        # Форматы
        formats = product_data.get('available_formats', [])
        console.print(f"\n[bold yellow]Доступные форматы ({len(formats)}):[/bold yellow]")
        for f in formats:
            dims = f.get('dimensions') or 'N/A'
            weight = f.get('weight_kg') or 'N/A'
            console.print(f"  • {f['name']}: {dims}, {weight} кг")
        
        # Сохраняем
        if output:
            output_path = PROCESSED_DATA_DIR / f"{output}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(product_data, f, ensure_ascii=False, indent=2)
            console.print(f"\n[bold green]✓ Saved to:[/bold green] {output_path}")
    else:
        console.print("[red]Failed to scrape product[/red]")


@cli.command()
@click.argument("url")
@click.option("--output", "-o", default=None, help="Файл для сохранения")
@click.option("--headless/--no-headless", default=True, help="Запуск браузера в фоне")
@async_command
async def gemini_scrape(url: str, output: str, headless: bool):
    """Скраппинг с Gemini Vision AI (анализ скриншотов)"""
    from src.scraper.gemini_scraper import GeminiProductScraper
    import json
    
    console.print(f"\n[bold magenta]🤖 Gemini Vision AI scraping[/bold magenta]")
    console.print(f"URL: [cyan]{url}[/cyan]")
    console.print(f"Headless: [cyan]{headless}[/cyan]\n")
    
    try:
        async with GeminiProductScraper(headless=headless) as scraper:
            product_data = await scraper.scrape_product(url)
        
        if product_data:
            # Показываем информацию
            console.print(f"\n[bold green]✓ Product scraped successfully[/bold green]")
            console.print(f"[green]Name:[/green] {product_data.get('name')}")
            console.print(f"[green]Article:[/green] {product_data.get('article')}")
            console.print(f"[green]Texture:[/green] {product_data.get('texture')}")
            
            # Швы
            joints = product_data.get('joints', [])
            console.print(f"\n[bold yellow]Швы ({len(joints)}):[/bold yellow]")
            for j in joints:
                name = j.get('name') if isinstance(j, dict) else j
                console.print(f"  • {name}")
            
            # Форматы
            formats = product_data.get('available_formats', [])
            console.print(f"\n[bold yellow]Доступные форматы ({len(formats)}):[/bold yellow]")
            for f in formats:
                if isinstance(f, dict):
                    name = f.get('name', 'N/A')
                    dims = f.get('dimensions') or 'N/A'
                    weight = f.get('weight_kg') or 'N/A'
                    console.print(f"  • {name}: {dims}, {weight} кг")
                else:
                    console.print(f"  • {f}")
            
            # Сохраняем
            if output:
                output_path = PROCESSED_DATA_DIR / f"{output}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(product_data, f, ensure_ascii=False, indent=2)
                console.print(f"\n[bold green]✓ Saved to:[/bold green] {output_path}")
        else:
            console.print("[red]Failed to scrape product[/red]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise


@cli.command()
@click.argument("url")
@click.option("--output", "-o", default=None, help="Файл для сохранения")
@click.option("--headless/--no-headless", default=True, help="Запуск браузера в фоне")
@click.option("--no-gemini", is_flag=True, help="Отключить Gemini обогащение")
@async_command
async def robust_scrape(url: str, output: str, headless: bool, no_gemini: bool):
    """Robust скраппинг (100% извлечение данных с прокруткой карусели)"""
    from src.scraper.robust_scraper import RobustProductScraper
    import json
    
    console.print(f"\n[bold green]🔄 Robust scraping (100% extraction)[/bold green]")
    console.print(f"URL: [cyan]{url}[/cyan]")
    console.print(f"Headless: [cyan]{headless}[/cyan]")
    console.print(f"Gemini enrichment: [cyan]{not no_gemini}[/cyan]\n")
    
    try:
        async with RobustProductScraper(headless=headless, use_gemini=not no_gemini) as scraper:
            product_data = await scraper.scrape_product(url)
        
        if product_data:
            console.print(f"\n[bold green]✓ Product scraped successfully[/bold green]")
            console.print(f"[green]Name:[/green] {product_data.get('name')}")
            console.print(f"[green]Article:[/green] {product_data.get('article')}")
            console.print(f"[green]Texture:[/green] {product_data.get('texture')}")
            
            # Швы
            joints = product_data.get('joints', [])
            console.print(f"\n[bold yellow]Швы ({len(joints)}):[/bold yellow]")
            for j in joints:
                name = j.get('name') if isinstance(j, dict) else j
                console.print(f"  • {name}")
            
            # Форматы
            formats = product_data.get('available_formats', [])
            console.print(f"\n[bold yellow]Доступные форматы ({len(formats)}):[/bold yellow]")
            for f in formats:
                if isinstance(f, dict):
                    name = f.get('name', 'N/A')
                    dims = f.get('dimensions') or 'N/A'
                    weight = f.get('weight_kg') or 'N/A'
                    console.print(f"  • {name}: {dims}, {weight} кг")
            
            # Сохраняем
            if output:
                output_path = PROCESSED_DATA_DIR / f"{output}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(product_data, f, ensure_ascii=False, indent=2)
                console.print(f"\n[bold green]✓ Saved to:[/bold green] {output_path}")
        else:
            console.print("[red]Failed to scrape product[/red]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise


@cli.command()
def categories():
    """Показать доступные категории"""
    
    table = Table(title="Available Categories")
    table.add_column("Key", style="cyan")
    table.add_column("Slug", style="green")
    table.add_column("URL", style="blue")
    
    for key, slug in VandersandenConfig.CATEGORIES.items():
        url = VandersandenConfig.get_category_url(key)
        table.add_row(key, slug, url)
    
    console.print(table)


def _show_summary(products):
    """Показать сводку по продуктам"""
    
    table = Table(title=f"Scraped Products ({len(products)} total)")
    table.add_column("Article", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Formats", justify="right")
    table.add_column("Color", style="yellow")
    
    for p in products[:10]:  # Показываем первые 10
        color = p.color.base_color if p.color else "-"
        table.add_row(
            p.article,
            p.name[:30],
            str(len(p.formats)),
            color
        )
    
    if len(products) > 10:
        table.add_row("...", f"and {len(products) - 10} more", "", "")
    
    console.print(table)


def main():
    """Точка входа"""
    cli()


if __name__ == "__main__":
    main()
