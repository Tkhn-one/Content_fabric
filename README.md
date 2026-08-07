# Content_fabric

Автоматическая фабрика вертикальных видео (YouTube Shorts / TikTok / Reels / VK Clips / Telegram)
на заданную тему: идеи и конкуренты → сценарий → озвучка/аватар → монтаж → публикация по расписанию
или вручную → журнал в Google Sheets + архив в Google Drive.

Self-hosted продукт для продажи по лицензии (Kwork): Docker, свои API-ключи заказчика, 3 тарифа
(Basic / Pro / Unlimited), white-label.

## Документы

- [План продукта (тарифы, идеи, дорожная карта)](docs/PLAN.md)
- [Техническая архитектура (стек, структура, контракты)](docs/ARCHITECTURE.md)

## Статус

**Этап 0 (скелет) — завершён** ✅
- FastAPI + React (SPA) + SQLite, авторизация (JWT), первый администратор
- Темы с cron-расписанием и планировщиком (APScheduler), ручной режим «сгенерировать сейчас»
- Пайплайн: идеи → сценарий → озвучка → рендер → модерация → публикация → журнал
  (шаги озвучки/рендера/публикации — заглушки, подключаются на этапах 1–3)
- Мастер подключения API-провайдеров (ключи шифруются Fernet), каталог провайдеров
- Лицензирование Ed25519 (keygen-утилита в `tools/keygen`)
- Smoke-тесты (`backend/tests`) — 2 passed

**Следующий этап:** реальный фейслесс-пайплайн (сток-кадры Pexels, озвучка edge-tts,
кинетические субтитры, ffmpeg-монтаж) — см. `docs/PLAN.md`.

## Запуск (dev)

```bash
# backend
cd backend
python -m venv ../.venv && ../.venv/bin/pip install -r requirements.txt
CF_SECRET_KEY=dev-secret ../.venv/bin/uvicorn app.main:app --port 8000   # → http://localhost:8000

# frontend (в отдельном терминале)
cd frontend && npm install && npm run dev                                 # → http://localhost:5173
```

## Запуск (production, docker)

```bash
cd deploy
cp .env.example .env        # заполнить CF_SECRET_KEY и т.д.
docker compose up -d --build
# → http://server (Caddy раздаёт панель + API + HTTPS)
```
