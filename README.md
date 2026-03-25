# PRO возможности Bot

Готовый Telegram-бот на `Python 3.12 + aiogram 3.x` с архитектурой из сервисов:

- `bot` — Telegram long polling бот
- `web` — FastAPI для промежуточной страницы оплаты и callback
- `db` — PostgreSQL
- `redis` — Redis (FSM)

## Стек

- Python 3.12
- aiogram 3.x
- PostgreSQL + async SQLAlchemy 2.0
- Redis storage для FSM
- Alembic миграции
- FastAPI + Uvicorn
- Docker + docker-compose

## Подготовка

1. Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

2. Заполните переменные в `.env`:

- `BOT_TOKEN`
- `BOT_USERNAME`
- `DEFAULT_MENTOR_NAME`, `DEFAULT_MENTOR_USERNAME`
- `COMMUNITY_CHAT_URL` (ссылка на ваш чат, например `https://t.me/your_chat`)
- `ADMIN_IDS` (список Telegram ID админов через запятую, например `12345,67890`)
- `ADMIN_WEB_TOKEN` (токен для web-админки; если пустой, доступ к `/admin` открыт)
- параметры БД и Redis
- `WEB_BASE_URL`
- `YOOMONEY_RECEIVER`, `YOOMONEY_LABEL_SECRET`, `YOOMONEY_SUCCESS_URL`, `YOOMONEY_FAIL_URL`

## Запуск через Docker Compose

```bash
docker compose up --build
```

При старте автоматически запускается сервис `migrator` (`alembic upgrade head`), и только после этого поднимаются `bot` и `web`.

Сервисы:

- Web: `http://localhost:8000`
- Health web: `http://localhost:8000/health`
- Admin web: `http://localhost:8000/admin` (или `http://localhost:8000/admin?token=...`)
  - На странице `/admin` теперь есть блок `Редактирование текстов` — можно менять тексты бота и web-экранов без правки кода.

## Миграции

Применить миграции:

```bash
docker compose run --rm migrator
```

Создать новую миграцию (если нужно):

```bash
docker compose run --rm bot alembic revision --autogenerate -m "message"
```

## Команды Telegram

- `/start` — запуск
- `/cabinet` — личный кабинет
- `/priglasil` — кто пригласил
- `/admin` — админ-панель

Команды `/start`, `/cabinet`, `/priglasil` автоматически публикуются в меню бота при старте.

## Что реализовано

- `/start` + deep link `link_<referral_code>`
- логика пригласившего наставника в приветствии
- личный кабинет с 6 кнопками (без раздела "Добавьте свою ссылку")
- подписка: остаток дней, продление на `+30` дней, оплата `199 RUB`
- промежуточная web-страница "Переход к оплате"
- callback/return по оплате через web-сервис
- реферальная ссылка формата `https://t.me/{BOT_USERNAME}?start=link_{referral_code}`
- `/priglasil`
- 4 слота фото профиля
- сохранение информации о себе
- список подписчиков (c разбиением длинных сообщений)
- FSM-воронка рассылки: `text`, `text+photo`, `text+video`
- логирование рассылок в `broadcasts` и `broadcast_logs`

## Структура

```text
.
├─ docker-compose.yml
├─ Dockerfile.bot
├─ Dockerfile.web
├─ .env.example
├─ requirements.txt
├─ README.md
├─ alembic.ini
├─ alembic/
│  ├─ env.py
│  ├─ script.py.mako
│  └─ versions/
│     └─ 20260323_0001_initial.py
└─ app/
   ├─ bot.py
   ├─ web.py
   ├─ config.py
   ├─ db/
   ├─ handlers/
   ├─ keyboards/
   ├─ services/
   ├─ states/
   ├─ utils/
   └─ assets/
```
