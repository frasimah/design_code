#!/bin/bash

set -euo pipefail

# Путь к проекту на сервере
PROJECT_PATH="/var/www/design_code"

echo "Starting deployment in $PROJECT_PATH..."

cd "$PROJECT_PATH" || { echo "Directory $PROJECT_PATH not found"; exit 1; }

# --- Load .env (for TELEGRAM_*, etc.) ---
if [ -f ".env" ]; then
  set -a
  source ".env"
  set +a
fi

# --- Telegram helper ---
send_telegram() {
  local MESSAGE="$1"

  # Если переменных нет — просто молча не шлём, чтобы деплой не падал из-за уведомлений
  if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
    echo "⚠ Telegram env not set (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID). Skipping notification."
    return 0
  fi

  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    --data-urlencode text="$MESSAGE" > /dev/null || true
}

HOST="$(hostname)"
CURRENT_STEP="init"
START_TS="$(date +%s)"

# Если что-то упало — отправляем уведомление и выходим с ошибкой
trap 'send_telegram "❌ Deploy FAILED\nServer: ${HOST}\nPath: ${PROJECT_PATH}\nStep: ${CURRENT_STEP}"; exit 1' ERR

# --- Ensure Node 20 via NVM (critical for non-interactive SSH sessions) ---
CURRENT_STEP="nvm use 20"
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
else
  echo "❌ nvm not found at $NVM_DIR/nvm.sh"
  exit 1
fi

nvm use 20 > /dev/null

echo "Node: $(node -v)"
echo "NPM:  $(npm -v)"

# 1. Получаем последние изменения из Git
CURRENT_STEP="git pull"
echo "Pulling latest changes from git..."
git pull origin main

COMMIT_HASH="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
COMMIT_MSG="$(git log -1 --pretty=%s 2>/dev/null || echo "unknown")"

# 2. Обновляем Python зависимости (бэкенд)
CURRENT_STEP="pip install -r requirements.txt"
echo "Updating Python dependencies..."
# shellcheck disable=SC1091
source venv/bin/activate
pip install -r requirements.txt

# 3. Сборка фронтенда (Next.js)
CURRENT_STEP="frontend build"
echo "Building frontend..."
cd furniture-catalog

# Убеждаемся, что есть ссылка на .env для сборки
ln -sf ../.env .env.local

npm install
npm run build

cd ..

# 4. Перезапуск процессов через PM2
CURRENT_STEP="pm2 restart"
echo "🔄 Restarting PM2 processes..."
# --update-env заставит PM2 перечитать переменные из ecosystem.config.js (и нашего .env)
pm2 restart ecosystem.config.js --update-env

END_TS="$(date +%s)"
DURATION="$((END_TS - START_TS))"

send_telegram "✅ Deploy SUCCESS\nServer: ${HOST}\nPath: ${PROJECT_PATH}\nTime: ${DURATION}s\nCommit: ${COMMIT_HASH}\nMsg: ${COMMIT_MSG}"

echo "✅ Deployment finished successfully!"
