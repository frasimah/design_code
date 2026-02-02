#!/bin/bash

# Путь к проекту на сервере
PROJECT_PATH="/var/www/design_code"

echo "Starting deployment in $PROJECT_PATH..."

cd $PROJECT_PATH || { echo "Directory $PROJECT_PATH not found"; exit 1; }

# 1. Получаем последние изменения из Git
echo "Pulling latest changes from git..."
git pull origin main

# 2. Обновляем Python зависимости (бэкенд)
echo "Updating Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# 3. Сборка фронтенда (Next.js)
echo "Building frontend..."
cd furniture-catalog
# Убеждаемся, что есть ссылка на .env для сборки
ln -sf ../.env .env.local
npm install
npm run build
cd ..

# 4. Перезапуск процессов через PM2
echo "🔄 Restarting PM2 processes..."
# --update-env заставит PM2 перечитать переменные из ecosystem.config.js (и нашего .env)
pm2 restart ecosystem.config.js --update-env

echo "✅ Deployment finished successfully!"
