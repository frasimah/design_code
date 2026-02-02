# 📦 Инструкция по установке Design Code Panel

> **Версия**: 1.0  
> **Дата обновления**: Февраль 2026

---

## 📋 Содержание

1. [Системные требования](#-системные-требования)
2. [Быстрый старт](#-быстрый-старт)
3. [Подробная установка](#-подробная-установка)
4. [Конфигурация](#-конфигурация)
5. [Импорт контента](#-импорт-контента)
6. [Запуск в режиме разработки](#-запуск-в-режиме-разработки)
7. [Продакшн-деплой](#-продакшн-деплой)
8. [Настройка Nginx](#-настройка-nginx)
9. [Устранение неполадок](#-устранение-неполадок)

---

## 💻 Системные требования

### Минимальные требования (Сервер)

| Параметр | Значение |
|----------|----------|
| **ОС** | Ubuntu 20.04 / 22.04 LTS |
| **CPU** | 2 vCPU |
| **RAM** | 4 ГБ (8 ГБ для сборки) |
| **Диск** | 20 ГБ SSD |

### Открытые порты

| Порт | Назначение |
|------|------------|
| `8001` | FastAPI Backend (изменено с 8000) |
| `3001` | Next.js Frontend (изменено с 3000) |
| `80/443` | Nginx (для продакшна) |

### Необходимое ПО

- **Python** 3.10+
- **Node.js** 18+ с npm
- **Git**

---

## 🚀 Быстрый старт (Production с PM2)

```bash
# 1. Клонирование репозитория
git clone https://github.com/frasimah/design_code.git
cd design_code

# 2. Настройка Бэкенда
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Настройка Фронтенда
cd furniture-catalog
npm install
# Сборка с указанием URL API
NEXT_PUBLIC_API_URL=https://domain.com npm run build
cd ..

# 4. Конфигурация
cp .env.example .env
# Отредактируйте .env и добавьте GEMINI_API_KEY и другие креды

# 5. Запуск через PM2
sudo npm install -g pm2
pm2 start ecosystem.config.js
pm2 save
```

---

## 🏭 Управление через PM2

Для удобства управления всеми частями проекта используется файл `ecosystem.config.js`.

```bash
pm2 status          # Посмотреть статус всех процессов
pm2 logs            # Просмотр логов в реальном времени
pm2 restart all     # Перезагрузить проект
pm2 stop all        # Остановить проект
```

### Настройка автозапуска при перезагрузке сервера:
```bash
pm2 startup
# Выполните команду, которую предложит PM2
pm2 save
```

---

## 🔧 Запуск в режиме разработки (Manual)

Если вам нужно запустить проект вручную для отладки:

### Терминал 1 — Бэкенд
```bash
source venv/bin/activate
uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8001
```

### Терминал 2 — Фронтенд
```bash
cd furniture-catalog
npm run dev
```

### Вариант Б: Systemd

#### Бэкенд (`/etc/systemd/system/design-backend.service`)

```ini
[Unit]
Description=Design Code Backend API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/design_code
Environment="PATH=/opt/design_code/venv/bin"
EnvironmentFile=/opt/design_code/.env
ExecStart=/opt/design_code/venv/bin/uvicorn src.api.server:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### Фронтенд (`/etc/systemd/system/design-frontend.service`)

```ini
[Unit]
Description=Design Code Frontend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/design_code/furniture-catalog
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Активация:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable design-backend design-frontend
sudo systemctl start design-backend design-frontend
```

---

## 🌐 Настройка Nginx

### Конфигурация (`/etc/nginx/sites-available/design_code`)

```nginx
server {
    listen 80;
    server_name panel.de-co-de.ru;

    # Frontend (Next.js)
    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Увеличенные таймауты для AI запросов
        proxy_read_timeout 120s;
        proxy_connect_timeout 60s;
    }

    # Статические файлы (uploads)
    location /uploads/ {
        alias /opt/design_code/data/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

**Активация:**
```bash
sudo ln -s /etc/nginx/sites-available/design_code /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL с Certbot (опционально)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d panel.de-co-de.ru
```

---

## 🔍 Устранение неполадок

### Ошибка: "Module not found"

```bash
# Убедитесь, что виртуальное окружение активировано
source venv/bin/activate
pip install -r requirements.txt
```

### Ошибка: "GEMINI_API_KEY not set"

```bash
# Проверьте наличие .env файла
cat .env | grep GEMINI
```

### Фронтенд не запускается

```bash
cd furniture-catalog
rm -rf node_modules .next
npm install
npm run build
```

### Проверка логов

```bash
# PM2
pm2 logs design-backend --lines 100

# Systemd
sudo journalctl -u design-backend -f
```

### Проверка портов

```bash
sudo netstat -tlnp | grep -E '(3001|8001)'
```

---

## 📞 Контакты

При возникновении проблем обращайтесь к разработчику.

---

*Документ создан автоматически* | *Design Code Panel v1.0*
