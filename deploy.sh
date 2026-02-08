#!/bin/bash
set -euo pipefail

# Путь к проекту на сервере
PROJECT_PATH="/var/www/design_code"
BRANCH="main"
PROJECT_NAME="design_code"

echo "Starting deployment in $PROJECT_PATH..."
cd "$PROJECT_PATH" || { echo "Directory $PROJECT_PATH not found"; exit 1; }

# --- Load .env (for TELEGRAM_*, etc.) ---
if [ -f ".env" ]; then
  set -a
  source ".env"
  set +a
fi

HOST="$(hostname)"
CURRENT_STEP="init"
START_TS="$(date +%s)"

send_telegram() {
  local MESSAGE="$1"

  if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
    echo "⚠ Telegram env not set (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID). Skipping notification."
    return 0
  fi

  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${MESSAGE}" \
    --data-urlencode "parse_mode=HTML" \
    > /dev/null || true
}

# Если что-то упало — отправляем уведомление и выходим с ошибкой
trap 'send_telegram "❌ <b>Deploy FAILED</b>

Project: <code>'"${PROJECT_NAME}"'</code>
Branch: <code>'"${BRANCH}"'</code>
Server: <code>'"${HOST}"'</code>
Path: <code>'"${PROJECT_PATH}"'</code>
Step: <code>'"${CURRENT_STEP}"'</code>"; exit 1' ERR

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

# 1) Жёстко синкаем код с origin/main (без конфликтов из-за локальных изменений)
CURRENT_STEP="git sync"
echo "Syncing code with origin/${BRANCH}..."
git fetch origin
git reset --hard "origin/${BRANCH}"
git clean -fd

COMMIT_HASH="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
COMMIT_MSG="$(git log -1 --pretty=%s 2>/dev/null || echo "unknown")"

# 2) Обновляем Python зависимости (бэкенд)
CURRENT_STEP="pip install -r requirements.txt"
echo "Updating Python dependencies..."
# shellcheck disable=SC1091
source venv/bin/activate
pip install -r requirements.txt

# 2.1) Re-index product catalog (required for new embedding model)
CURRENT_STEP="re-index catalog"
echo "Re-indexing product catalog..."
python3 src/ai/embeddings.py --force

# 3) Сборка фронтенда (Next.js)
CURRENT_STEP="frontend build"
echo "Building frontend..."
cd furniture-catalog

# Убеждаемся, что есть ссылка на .env для сборки
ln -sf ../.env .env.local

# В проде/CI правильно использовать npm ci (не меняет package-lock)
npm ci
npm run build

cd ..

# 4) Перезапуск процессов через PM2
CURRENT_STEP="pm2 restart"
echo "🔄 Restarting PM2 processes..."
pm2 restart ecosystem.config.js --update-env

END_TS="$(date +%s)"
DURATION="$((END_TS - START_TS))"

send_telegram "✅ <b>Deploy SUCCESS</b>

Project: <code>${PROJECT_NAME}</code>
Branch: <code>${BRANCH}</code>
Server: <code>${HOST}</code>
Path: <code>${PROJECT_PATH}</code>
Time: ${DURATION}s
Commit: <code>${COMMIT_HASH}</code>

Msg: ${COMMIT_MSG}"

echo "✅ Deployment finished successfully!"
