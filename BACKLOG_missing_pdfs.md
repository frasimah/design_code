# Бэклог: Продукты без скачанных PDF

Дата: 2026-01-25

## Продукты без PDF файлов (3 шт) 1

| Slug | URL | Причина |
|------|-----|---------|
| greifswald | https://www.vandersanden.com/ru-ru/products-and-solutions/greifswald | PDF не скачаны при парсинге |
| nevado-dark | https://www.vandersanden.com/ru-ru/products-and-solutions/nevado-dark | PDF не скачаны при парсинге |
| oud-blanckaert | https://www.vandersanden.com/ru-ru/products-and-solutions/oud-blanckaert | PDF не скачаны при парсинге |

## Как исправить

1. Повторно скачать продукты с помощью robust-scraper:
```bash
python3 main.py robust-scrape https://www.vandersanden.com/ru-ru/products-and-solutions/greifswald
python3 main.py robust-scrape https://www.vandersanden.com/ru-ru/products-and-solutions/nevado-dark
python3 main.py robust-scrape https://www.vandersanden.com/ru-ru/products-and-solutions/oud-blanckaert
```

2. Запустить парсинг PDF:
```bash
python3 parse_remaining.py
```

3. Обновить связи в каталоге:
```bash
python3 scripts/link_pdfs.py
```
