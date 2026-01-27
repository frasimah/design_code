# Инструкция по установке Lick Brick

## Системные требования (Сервер)
*   **ОС**: Ubuntu 20.04 / 22.04 LTS (рекомендуется)
*   **CPU**: Минимум 2 vCPU
*   **RAM**: Минимум 4 ГБ (Рекомендуется 8 ГБ для сборки фронтенда)
*   **Диск**: 20 ГБ свободного места (SSD)
*   **Порты**: 8000 (API), 3000 (Frontend), доступ в интернет (для API Google Gemini)

## Требования ПО
- **Python 3.10+**
- **Node.js 18+** & **npm**
- **Git**

## 1. Клонирование репозитория
```bash
git clone <repository_url>
cd lick_brick
```

## 2. Настройка бэкенда (Backend)
Создайте виртуальное окружение и установите зависимости:
```bash
python3 -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Настройка фронтенда (Frontend)
Установите зависимости Node.js:
```bash
cd brick-catalog
npm install
cd ..
```

## 4. Импорт контента
Контент (база данных каталога и AI-индексы) **не** хранится в Git. Вы должны загрузить пакет контента отдельно.

1.  Получите последний архив `lick_brick_content_YYYYMMDD_HHMMSS.zip` у администратора.
2.  Поместите его в корневую директорию проекта (`lick_brick/`).
3.  Распакуйте архив:
    ```bash
    unzip lick_brick_content_*.zip
    ```
    *Убедитесь, что папка `data/` появилась в корне проекта.*

## 5. Конфигурация
Создайте файл `.env` в корневой директории (скопируйте из примера):
```bash
cp .env.example .env
```
Отредактируйте `.env` и добавьте ваши ключи:
```
GEMINI_API_KEY=ваш_ключ_здесь
# Если нужен прокси (SOCKS5/HTTP):
GEMINI_PROXY_URL=socks5://login:password@ip:port
```

## 6. Запуск приложения
### Вариант А: Разработка (Два терминала)
**Терминал 1 (Бэкенд):**
```bash
source venv/bin/activate
uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000
```

**Терминал 2 (Фронтенд):**
```bash
cd brick-catalog
npm run dev
```
Фронтенд будет доступен по адресу `http://localhost:3000`.
### Вариант Б: Продакшн (Рекомендуется PM2)
Мы рекомендуем использовать PM2 для управления процессами:
```bash
# Запуск бэкенда
pm2 start "uvicorn src.api.server:app --host 0.0.0.0 --port 8000" --name lick-backend

# Сборка и запуск фронтенда
cd brick-catalog
npm run build
pm2 start "npm start" --name lick-frontend
```

## Прокси и Pip
Если ваш сервер не имеет прямого доступа в интернет и требует SOCKS-прокси даже для установки пакетов (`pip install`), вам необходимо настроить прокси **в терминале** перед установкой:

```bash
export HTTP_PROXY=socks5://user:pass@host:port
export HTTPS_PROXY=socks5://user:pass@host:port
pip install -r requirements.txt
```

Настройка в `.env` (описанная выше) влияет только на работу самого приложения (ИИ, запросы), но не на установку библиотек. Мы добавили библиотеку `pysocks`, чтобы приложение корректно работало через SOCKS.
