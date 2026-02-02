#!/bin/bash
set -euo pipefail

PROJECT_PATH="/var/www/design_code"

echo "Starting deployment in $PROJECT_PATH..."
cd "$PROJECT_PATH" || { echo "Directory $PROJECT_PATH not found"; exit 1; }

# Load .env (TELEGRAM_*)
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

trap 'send_telegram "❌ <b>Deploy FAILED</b>

Server: <code>${HOST}</code>
Path: <code>${PROJECT_PATH}</code>
Step: <code>${CURRENT_STEP}</code>"; exit 1' ERR

# Ensure Node 20 via NVM (important for non-interactive SSH)
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

# 1) Git sync (оставил pull как у тебя; если хочешь — заменим на reset --hard)
CURRENT_STEP="git pull"
echo "Pulling latest changes from git..."
git pull origin main

COMMIT_HASH="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
COMMIT_MSG="$(git log -1 --pretty=%s 2>/dev/null || echo "unknown")"

# 2) Python deps
CURRENT_STEP="pip install"
echo "Updating Python dependencies..."
# shellcheck disable=SC1091
source venv/bin/activate
pip install -r requirements.txt

# 3) Frontend build
CURRENT_STEP="frontend build"
echo "Building frontend..."
cd furniture-catalog
ln -sf ../.env .env.local

# Лучше для CI/прода: npm ci (не меняет package-lock), но оставляю install как у тебя
npm install
npm run build
cd ..

# 4) PM2 restart
CURRENT_STEP="pm2 restart"
echo "🔄 Restarting PM2 processes..."
pm2 restart ecosystem.config.js --update-env

END_TS="$(date +%s)"
DURATION="$((END_TS - START_TS))"

send_telegram "✅ <b>Deploy SUCCESS</b>

Server: <code>${HOST}</code>
Path: <code>${PROJECT_PATH}</code>
Time: ${DURATION}s
Commit: <code>${COMMIT_HASH}</code>

Msg: ${COMMIT_MSG}"

echo "✅ Deployment finished successfully!"
