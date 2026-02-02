const fs = require('fs');
const path = require('path');

function parseEnv(filePath) {
  if (!fs.existsSync(filePath)) {
    return {};
  }
  
  const content = fs.readFileSync(filePath, 'utf-8');
  const env = {};
  
  content.split('\n').forEach(line => {
    line = line.trim();
    if (!line || line.startsWith('#')) return;
    
    const index = line.indexOf('=');
    if (index === -1) return;
    
    const key = line.substring(0, index).trim();
    let value = line.substring(index + 1).trim();
    value = value.replace(/^["'`](.*)["'`]$/, '$1');
    if (key && /^[A-Z0-9_]+$/i.test(key)) {
      env[key] = value;
    }
  });
  
  return env;
}

const envPath = path.join(__dirname, '.env');
const rootEnv = parseEnv(envPath);

module.exports = {
  apps: [
    {
      name: 'design-backend',
      script: './venv/bin/python3',
      args: '-m uvicorn src.api.server:app --host 127.0.0.1 --port 8001',
      cwd: __dirname,
      env: {
        PYTHONPATH: '.',
        NODE_ENV: 'production',
        ...rootEnv
      },
      kill_timeout: 5000,
    },
    {
      name: 'design-frontend',
      script: 'npm',
      args: 'start',
      cwd: path.join(__dirname, 'furniture-catalog'),
      env: {
        NODE_ENV: 'production',
        PORT: 3002,
        ...rootEnv
      }
    }
  ]
};
