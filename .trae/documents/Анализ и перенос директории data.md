# План полной очистки проекта от локальных привязок

## 1. Остановка процессов
- Остановить выполнение команд в терминалах 6 (Next.js) и 7 (FastAPI).

## 2. Удаление хардкода из фронтенда
- В файлах [lib/api.ts](file:///Volumes/external/work/design_code/furniture-catalog/lib/api.ts), [chat-widget/api.ts](file:///Volumes/external/work/design_code/furniture-catalog/components/chat-widget/api.ts), [project-detail-view.tsx](file:///Volumes/external/work/design_code/furniture-catalog/components/project-detail-view.tsx) и [url-input-modal.tsx](file:///Volumes/external/work/design_code/furniture-catalog/components/url-input-modal.tsx) заменить логику `process.env.NEXT_PUBLIC_API_URL || 'localhost...'` на строгую проверку наличия переменной.

## 3. Исправление CORS на бэкенде
- В [server.py](file:///Volumes/external/work/design_code/src/api/server.py) очистить список `allow_origins` от всех упоминаний `localhost` и `127.0.0.1`.

## 4. Очистка документации
- Убрать упоминания локальных портов и адресов из основного [README.md](file:///Volumes/external/work/design_code/README.md) и [README.md](file:///Volumes/external/work/design_code/furniture-catalog/README.md) фронтенда.

## 5. Проверка
- Убедиться, что после удаления хардкода проект корректно собирается и требует настройки `.env` для работы.
