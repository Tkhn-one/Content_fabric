# Content Factory — техническая архитектура

> Техническое описание продукта. Бизнес-план и тарифы — в `docs/PLAN.md`.
> Стек выбран под требования: продаваемый self-hosted продукт, установка в 1 команду,
> модульность провайдеров, защита лицензией.

---

## 1. Обзор

```
┌─────────────────────────────────────────────────────────────┐
│  Браузер заказчика (панель управления)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS (Caddy/nginx в compose)
┌──────────────────────────▼──────────────────────────────────┐
│  FastAPI (Python 3.12)                                       │
│  ├── REST API  (панель, настройки, журнал)                  │
│  ├── APScheduler (таймер: N видео/день)                     │
│  ├── Воркер пайплайна (очередь заданий, retry)              │
│  ├── Лицензия (Ed25519-проверка)                            │
│  └── Провайдеры (LLM / TTS / Аватар / Сток / Музыка / Постинг)│
└──────────────┬─────────────────────┬────────────────────────┘
               │                     │
        ┌──────▼──────┐       ┌──────▼──────┐
        │ SQLite      │       │ Хранилище   │
        │ (или PG)    │       │ media/      │
        │ + Fernet    │       │ (готовые    │
        │ шифрование  │       │  ролики)    │
        │ ключей      │       │             │
        └─────────────┘       └─────────────┘
               │
               │ вызовы по HTTPS (ключи заказчика)
        ┌──────▼──────────────────────────────────────────────┐
        │ YouTube │ TikTok │ VK │ TG │ Reels │ LLM │ TTS │    │
        │ Drive │ Sheets │ Pexels │ HeyGen/D-ID │ ffmpeg      │
        └─────────────────────────────────────────────────────┘
```

**Принципы:**
- Каждый внешний сервис — **провайдер-адаптер** с единым интерфейсом (меняется в настройках, без правки кода).
- Все ключи хранятся зашифрованными (Fernet, мастер-ключ в `.env`).
- Пайплайн — конечный автомат: каждый шаг сохраняется в БД, при падении — retry с экспоненциальной задержкой.
- Всё, кроме рендера, — асинхронное; рендер — отдельный процесс ffmpeg (не блокирует API).

---

## 2. Стек

| Слой | Технология | Почему |
|---|---|---|
| Backend | Python 3.12 + **FastAPI** + Uvicorn | Быстро, асинхронно, отличный набор для AI/ffmpeg |
| Планировщик | **APScheduler** (cron-подобно: дни, время, N/день) | Встроен в процесс, UI-настройка расписаний |
| Очередь заданий | Встроенный воркер (asyncio-пул + таблица `jobs`) | Для single-node self-hosted хватает; без Redis-зависимости |
| БД | **SQLite** (по умолчанию) / Postgres (опция для агентств) | Простота установки, бекап = копия файла |
| ORM/миграции | SQLAlchemy 2 + Alembic | Надёжность |
| Шифрование ключей | `cryptography` (Fernet) | Ключи заказчика в безопасности |
| Frontend | **React + Vite + Tailwind** + Recharts | Современный UI, графики аналитики; продаёт продукт |
| Рендер видео | **ffmpeg** (CLI) + moviepy (оркестрация) | ffmpeg — стандарт, быстрее и надёжнее чистой moviepy |
| Субтитры | Кинетические (ASS-подобные) — свой модуль анимации слов | TikTok-стиль, 5+ стилей |
| Лицензии | Ed25519 (подпись) + ключевая панель | Нельзя подделать, офлайн-проверка |
| Развёртывание | **docker-compose** + Caddy (авто-HTTPS) | Установка в 1 команду |

---

## 3. Структура репозитория

```
Content_fabric/
├─ backend/
│  ├─ app/
│  │  ├─ main.py                 # FastAPI app, lifespan, роутеры
│  │  ├─ core/
│  │  │  ├─ config.py            # pydantic-settings (.env)
│  │  │  ├─ db.py                # engine/session
│  │  │  ├─ security.py          # JWT-авторизация, Fernet-шифрование ключей
│  │  │  └─ license.py           # проверка Ed25519-подписи, маска функций
│  │  ├─ models/                 # SQLAlchemy
│  │  │  ├─ user.py
│  │  │  ├─ topic.py             # темы/ниши заказчика
│  │  │  ├─ job.py               # задания пайплайна (state machine)
│  │  │  ├─ publish_log.py       # журнал публикаций
│  │  │  └─ provider_settings.py # зашифрованные ключи провайдеров
│  │  ├─ api/                    # REST: /auth /topics /jobs /publish /settings /stats
│  │  ├─ pipeline/
│  │  │  ├─ engine.py            # запуск шагов, retry, статусы
│  │  │  ├─ steps/
│  │  │  │  ├─ research.py       # идеи и конкуренты
│  │  │  │  ├─ script.py         # сценарий по шаблонам
│  │  │  │  ├─ voiceover.py
│  │  │  │  ├─ render.py         # ffmpeg-сборка
│  │  │  │  └─ publish.py
│  │  │  └─ templates/           # шаблоны сценариев (факты, топ-5, история, Q&A)
│  │  ├─ providers/              # абстракции + адаптеры
│  │  │  ├─ llm/                 # openai, anthropic, gemini, yandexgpt, gigachat
│  │  │  ├─ tts/                 # elevenlabs, openai_tts, edge_tts, yandex
│  │  │  ├─ avatar/              # heygen, did
│  │  │  ├─ stock/               # pexels, pixabay
│  │  │  ├─ music/               # библиотека royalty-free + загрузка своих треков
│  │  │  └─ publish/             # youtube, tiktok, telegram, vk, instagram
│  │  ├─ services/
│  │  │  ├─ sheets.py            # журнал в Google Sheets
│  │  │  ├─ drive.py             # архив в Google Drive
│  │  │  └─ analytics.py         # статистика каналов
│  │  └─ scheduler/              # APScheduler-джобы (расписания тем)
│  ├─ alembic/                   # миграции
│  └─ tests/                     # pytest (юнит на провайдеров, e2e на пайплайн с моками)
├─ frontend/                     # React + Vite + Tailwind (SPA)
├─ tools/
│  └─ keygen/                    # CLI генерации лицензий (только у продавца)
├─ docs/
│  ├─ PLAN.md
│  └─ ARCHITECTURE.md
├─ deploy/
│  ├─ docker-compose.yml
│  ├─ Caddyfile
│  └─ .env.example
└─ README.md
```

---

## 4. Модель данных (основное)

- **User** — администратор (1 юзер в Basic/Pro, unlimited — до 3 операторов).
- **Topic** — тема: название, ниша, язык, тон, шаблон сценария, расписание (cron), число видео/день, платформы.
- **Job** — задание пайплайна: `topic_id`, статус, шаг, payload (сценарий, пути к медиа), ошибки, retry_count, результат (ссылки публикаций).
- **PublishLog** — одна строка на публикацию: платформа, video_id, URL, статус, время, статистика (после импорта).
- **ProviderSettings** — зашифрованный ключ/токен + выбранный провайдер по типам (llm, tts, avatar, stock, publish).

**Статусы Job:** `queued → research → script → review → voiceover → render → publish → done`
плюс `failed` (с причиной и кнопкой «повторить»).

**Планировщик:** на каждую Topic — cron-выражение «N раз в день в заданные часы»;
создание Job ставится в очередь. Ручной режим — кнопка «Сгенерировать сейчас».

---

## 5. Интерфейсы провайдеров (контракты)

```python
# providers/llm/base.py
class LLMProvider(ABC):
    async def generate_script(self, prompt: str, template: ScriptTemplate) -> Script: ...
    async def generate_ideas(self, topic: str, competitors: list[str]) -> list[Idea]: ...
    async def generate_hashtags(self, script: Script, platform: Platform) -> list[str]: ...

# providers/tts/base.py
class TTSProvider(ABC):
    async def synthesize(self, text: str, voice: VoiceRef, lang: str) -> Path: ...
    async def list_voices(self) -> list[VoiceRef]: ...

# providers/avatar/base.py
class AvatarProvider(ABC):
    async def render(self, script: Script, avatar: AvatarRef) -> Path: ...  # готовый ролик с аватаром

# providers/stock/base.py
class StockProvider(ABC):
    async def search(self, query: str, n: int, orientation: str = "vertical") -> list[ClipRef]: ...

# providers/publish/base.py
class PublishProvider(ABC):
    async def publish(self, video: Path, meta: PublishMeta) -> PublishResult: ...
    async def get_stats(self, video_id: str) -> Stats: ...
```

Реализации: `YoutubeProvider` (OAuth refresh-token), `TikTokProvider` (OAuth + загрузка частями),
`TelegramProvider`, `VKProvider`, `InstagramProvider`. В панели — экран «Подключения» с мастером OAuth
и проверкой ключа (тестовый вызов).

---

## 6. Рендер видео (шаг 5–6)

1. Озвучка → аудиофайл + таймкоды слов (у ElevenLabs/edge-tts есть выравнивание).
2. Выбор кадров: сток по ключевым словам каждого блока сценария ИЛИ ролик аватара (HeyGen/D-ID).
3. ffmpeg-цепочка: кадры → обрезка под 9:16 → склейка по таймкодам → кинетические субтитры
   (слова подсвечиваются синхронно с речью) → фоновая музыка с ducking (sidechain) → логотип/водяной знак.
4. Проверка: длительность ≤ 60 сек, разрешение 1080×1920, битрейт. Авто-пересборка при ошибке.
5. Готовый файл → `media/videos/{job_id}.mp4` + превью в очереди модерации.

---

## 7. Публикация и журнал

- **YouTube Shorts:** OAuth (клиент заказчика) → `videos.insert` (shorts-параметры: #Shorts,
  вертикаль) → описание из шаблона + авто-хештеги → необязательный тайминг «опубликовать в HH:MM».
- **TikTok:** OAuth → `video.upload` + `video.publish` (токен обновляется каждые 24 ч — встроено).
- **VK:** токен сообщества → `video.save` → загрузка → публикация на стену.
- **Telegram:** Bot API → `sendVideo` (канал/чат).
- **Instagram Reels:** Graph API → `media` (container) → `publish` (Business/Creator-аккаунт).
- После публикации: строка в **Google Sheets** (дата, тема, заголовок, платформы, URL, статус),
  копия ролика в **Google Drive** (папка по теме).

---

## 8. Лицензирование

- Ключ = `base64(version + payload) + Ed25519-подпись`; payload: тариф, маска функций,
  число каналов, срок поддержки, id заказчика.
- Проверка при старте + в панели (офлайн, без нашего сервера). Невалидный ключ → UI показывает
  ограниченный режим (демо: 3 ролика, водяной знак).
- `tools/keygen` (CLI у продавца) генерирует ключи по тарифу.
- **Unlimited:** в панели есть вкладка «Лицензии» — перепродавец генерирует ключи для своих
  клиентов (та же подпись, продавец передаёт перепродавцу пару ключей или конфиг keygen).
- White-label: тема/лого меняются через настройки (без правки кода).

---

## 9. Безопасность

- Все ключи провайдеров — Fernet-шифрование (мастер-ключ только в `.env`, вне БД).
- JWT-авторизация (access + refresh), смена пароля, rate-limit на `/auth`.
- HTTPS по умолчанию (Caddy в compose), порты наружу — только 80/443.
- Журнал аудита: кто и когда запускал задания, менял настройки, публиковал.
- ffmpeg-команды собираются только из внутренних данных (нет пользовательского shell).

---

## 10. Развёртывание

```bash
git clone <repo> && cd Content_fabric/deploy
cp .env.example .env          # мастер-ключ, админ-пароль, флаги тарифа
docker compose up -d          # app + caddy (+ postgres опционально)
# → http://server:80 → мастер первого запуска: админ, ключ лицензии, подключение API
```

- Медиа и SQLite — в docker volume; бекап = `docker compose exec app tar` папки данных.
- Обновление: `git pull && docker compose up -d --build` (миграции Alembic автоматически).

---

## 11. Тестирование

- Юнит: провайдеры (моки HTTP), шаблоны сценариев, лицензии.
- Интеграционные: пайплайн на 10-секундном ролике (edge-tts + Pexels + ffmpeg), публикация — мок.
- E2E (опционально, перед релизом): реальный аккаунт YouTube-песочницы.
- Golden-файлы: субтитры/сборка — сравнение с эталоном.
