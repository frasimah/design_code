# 🚀 Инструкция по развертыванию на сервере (panel.de-co-de.ru)

Эта инструкция предназначена для чистого развертывания проекта на Ubuntu сервере с использованием PM2 и Nginx.

---
 
## 1. Подготовка сервера 
Выполните один раз для установки базового ПО:
```bash
sudo apt update
sudo apt install git python3-pip python3-venv nodejs npm nginx -y
sudo npm install -g pm2
```

## 2. Клонирование проекта
Создайте папку и склонируйте репозиторий:
```bash
sudo mkdir -p /var/www/design_code
sudo chown $USER:$USER /var/www/design_code
cd /var/www/design_code
git clone https://github.com/frasimah/design_code.git .
```

## 3. Настройка Бэкенда (Python)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Настройка Фронтенда (Next.js)
```bash
cd furniture-catalog
# Создаем ссылку на общий .env, чтобы Next.js подтянул переменные при сборке
ln -sf ../.env .env.local
npm install
npm run build
cd ..
```

## 5. Конфигурация (.env)
Создайте файл настроек:
```bash
cp .env.example .env
nano .env
```
**Обязательно заполните:**
- `NEXTAUTH_URL=https://panel.de-co-de.ru`
- `NEXT_PUBLIC_API_URL=https://panel.de-co-de.ru`
- `GEMINI_API_KEY=...`
- `NEXTAUTH_SECRET=...` (сгенерируйте любую длинную строку)

## 6. Запуск через PM2
Запустите оба сервиса одной командой (из-под вашего текущего пользователя):
```bash
pm2 delete all # Очистить старые процессы, если были
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

---

## 7. Настройка прав (для Nginx и загрузок)
Чтобы Nginx мог раздавать картинки из папки `data/uploads`, дайте ему права доступа:
```bash
sudo chown -R $USER:www-data /var/www/design_code
sudo chmod -R 755 /var/www/design_code
# Если бэкенд будет сохранять новые файлы:
sudo chmod -R 775 /var/www/design_code/data
```
```nginx
server {
    listen 80;
    server_name panel.de-co-de.ru;

    # NextAuth.js (ВАЖНО: должно быть выше общего /api/)
    location /api/auth/ {
        proxy_pass http://127.0.0.1:3002;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Static uploads
    location /uploads/ {
        alias /var/www/design_code/data/uploads/;
    }
}
```
Активируйте конфиг:
```bash
sudo ln -s /etc/nginx/sites-available/design_code /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 8. Настройка SSL (HTTPS)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d panel.de-co-de.ru
```

---

## 🔄 Как обновлять проект
```bash
git pull
# Если менялся бэкенд:
pm2 restart design-backend

# Если менялся фронтенд:
cd furniture-catalog
npm install
NEXT_PUBLIC_API_URL=https://panel.de-co-de.ru npm run build
pm2 restart design-frontend
```

## 🔄 Автоматизация деплоя (CI/CD)

В проекте настроен GitHub Action для автоматического деплоя при пуше в ветку `main`.

### Настройка GitHub Secrets

Чтобы автоматизация работала, добавьте в настройках вашего репозитория (Settings -> Secrets and variables -> Actions) следующие секреты:

1.  **`SERVER_HOST`**: IP адрес вашего сервера (`176.53.162.229`).
2.  **`SERVER_USER`**: Пользователь для SSH (`root` или ваш пользователь).
3.  **`SSH_PRIVATE_KEY`**: Приватный SSH ключ. Публичный ключ должен быть добавлен в `~/.ssh/authorized_keys` на сервере.

### Скрипт деплоя

Сам процесс сборки и перезапуска описан в файле [deploy.sh](file:///Volumes/external/work/design_code/deploy.sh). Он выполняет:
- `git pull`
- Установку Python зависимостей
- Сборку Next.js фронтенда
- Перезапуск процессов через PM2 с обновлением окружения.

---

## 📊 Полезные команды
- `pm2 status` — состояние процессов
- `pm2 logs` — просмотр логов
- `pm2 restart all` — полная перезагрузка
