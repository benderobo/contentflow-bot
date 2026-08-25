# ContentFlow Bot

Автоматическая система управления контентом для Telegram-каналов. Полный пайплайн: парсинг контента → анализ → AI-рерайт → редактирование → модерация → планирование → публикация.

## 🚀 Быстрый старт

### Предварительные требования

- Docker & Docker Compose
- Python 3.12+ (для локальной разработки)
- Telegram Bot Token (от @BotFather)
- API ключ AI-провайдера (OpenRouter, OpenAI, Anthropic или Ollama)

### 1. Клонирование репозитория

```bash
git clone https://github.com/benderobo/contentflow.git
cd contentflow
```

### 2. Конфигурация

```bash
cp .env.example .env
```

Отредактируйте `.env` с вашими параметрами:

```env
BOT_TOKEN=your_telegram_bot_token
OPENROUTER_API_KEY=your_openrouter_key
DATABASE_URL=postgresql://contentflow:contentflow@postgres:5432/contentflow
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key-here
ADMIN_TELEGRAM_IDS=123456789
```

### 3. Запуск с Docker

```bash
docker compose up -d
```

Сервисы запустятся:
- **Bot**: Telegram-бот (polling)
- **API**: REST API на http://localhost:8000
- **Database**: PostgreSQL
- **Cache**: Redis
- **Workers**: Celery workers для фоновых задач
- **Scheduler**: Планировщик публикаций
- **Web**: Dashboard на http://localhost:3000

### 4. Первый запуск

1. Откройте Telegram-бота: `@your_bot_username`
2. Отправьте `/start`
3. Добавьте источник контента
4. Настройте Telegram-канал назначения
5. Выберите AI-провайдера
6. Запустите парсинг

## 📋 Структура проекта

```
contentflow/
├── bot/                    # Telegram bot handlers
├── api/                   # REST API (FastAPI)
├── core/                  # Конфигурация и БД
├── models/                # SQLAlchemy модели
├── services/              # Парсер, AI, дедупликация
├── workers/               # Celery tasks и планировщик
├── web/                   # React dashboard
├── migrations/            # Alembic миграции
├── docker/                # Dockerfiles
├── tests/                 # Тесты
└── docker-compose.yml
```

## 🔌 Источники контента

### RSS / Atom Feeds
```
Тип: rss
URL: https://example.com/feed.xml
```

### Telegram-каналы
```
Тип: telegram
Username или ID: @channel_name
```

### Веб-сайты
```
Тип: website
URL: https://example.com
```

## 🤖 AI-провайдеры

### OpenRouter (рекомендуется)
```env
AI_PROVIDER=openrouter
AI_MODEL=openrouter/auto
OPENROUTER_API_KEY=sk-or-...
```

### OpenAI
```env
AI_PROVIDER=openai
AI_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=sk-...
```

### Anthropic
```env
AI_PROVIDER=anthropic
AI_MODEL=claude-3-sonnet-20240229
ANTHROPIC_API_KEY=sk-ant-...
```

### Ollama (локально)
```env
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

## 📡 Telegram-интерфейс

### Главное меню

- **📥 Источники** - Управление источниками контента
- **📝 Посты** - Просмотр и редактирование постов
- **🤖 AI** - Настройка AI-провайдера
- **📅 Планировщик** - Расписание публикаций
- **📢 Каналы** - Управление Telegram-каналами
- **📊 Статистика** - Аналитика
- **⚙️ Настройки** - Конфигурация

## 🔄 Пайплайн обработки

```
Источник
    ↓
Парсер (RSS, Website, Telegram)
    ↓
Нормализация контента
    ↓
Проверка на дубликаты
    ↓
AI-анализ (категория, важность, кликбейт)
    ↓
Создание черновика
    ↓
AI-рерайт (на выбор)
    ↓
Редактирование в Web App
    ↓
Проверка модератором
    ↓
Добавление в очередь
    ↓
Планировщик
    ↓
Публикация в Telegram
    ↓
Статистика
```

## 📊 Статусы поста

- **NEW** - Новый материал из источника
- **PROCESSING** - Обрабатывается парсером
- **DRAFT** - Черновик готов к редактированию
- **NEEDS_REVIEW** - Ожидает модерации
- **APPROVED** - Одобрен для публикации
- **SCHEDULED** - Добавлен в очередь
- **PUBLISHED** - Опубликован
- **REJECTED** - Отклонен
- **FAILED** - Ошибка при обработке

## 🔐 Безопасность

- ✅ API ключи только в environment variables
- ✅ JWT аутентификация для API
- ✅ Rate limiting на Telegram-бот
- ✅ Валидация входных данных
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ XSS protection (Telegram native)
- ✅ CSRF protection на Web App
- ✅ Whitelist Telegram user IDs
- ✅ Безопасное хранение паролей (bcrypt)

## 📦 API Endpoints

### Источники
```
GET    /api/sources                 # Список
GET    /api/sources/{id}            # Получить
POST   /api/sources                 # Создать
PATCH  /api/sources/{id}            # Обновить
DELETE /api/sources/{id}            # Удалить
```

### Посты
```
GET    /api/posts                   # Список
GET    /api/posts/{id}              # Получить
POST   /api/posts                   # Создать
PATCH  /api/posts/{id}              # Обновить
POST   /api/posts/{id}/rewrite      # AI переписать
POST   /api/posts/{id}/approve      # Одобрить
POST   /api/posts/{id}/publish      # Опубликовать
```

### Каналы
```
GET    /api/channels                # Список
POST   /api/channels                # Создать
GET    /api/channels/{id}           # Получить
PATCH  /api/channels/{id}           # Обновить
```

### AI
```
GET    /api/ai/usage                # Статистика
GET    /api/ai/requests             # История запросов
POST   /api/ai/analyze              # Анализ
POST   /api/ai/rewrite              # Переписать
```

### Статистика
```
GET    /api/stats/dashboard         # Dashboard
```

## 🔧 Управление Docker

### Просмотр логов
```bash
docker compose logs -f bot
docker compose logs -f api
docker compose logs -f worker
```

### Перезагрузка сервиса
```bash
docker compose restart bot
docker compose restart api
docker compose restart worker
```

### Остановка
```bash
docker compose down
```

## 🧪 Тестирование

### Запуск тестов
```bash
docker compose exec bot pytest tests/ -v
```

### Unit тесты
```bash
pytest tests/unit/ -v
```

### Integration тесты
```bash
pytest tests/integration/ -v
```

### С покрытием
```bash
pytest tests/ --cov=contentflow --cov-report=html
```

## 📚 База данных

### Миграции

```bash
# Создать новую миграцию
docker compose exec api alembic revision --autogenerate -m "description"

# Применить миграции
docker compose exec api alembic upgrade head

# Откатить последнюю
docker compose exec api alembic downgrade -1
```

### Основные таблицы

- `users` - Пользователи Telegram
- `sources` - Источники контента
- `source_items` - Материалы из источников
- `posts` - Постов в процессе / опубликованные
- `post_media` - Медиа к постам
- `channels` - Telegram-каналы
- `publish_jobs` - Очередь публикаций
- `ai_prompts` - Шаблоны AI промптов
- `ai_requests` - История AI запросов
- `ai_usage` - Статистика использования AI
- `categories` - Категории контента
- `audit_logs` - Логи действий

## 📝 Environment переменные

| Переменная | Описание | Пример |
|-----------|---------|--------|
| `BOT_TOKEN` | Telegram Bot Token | `123456:ABC...` |
| `DATABASE_URL` | PostgreSQL URL | `postgresql://...` |
| `REDIS_URL` | Redis URL | `redis://redis:6379/0` |
| `AI_PROVIDER` | AI провайдер | `openrouter` |
| `AI_MODEL` | Модель AI | `openrouter/auto` |
| `OPENROUTER_API_KEY` | OpenRouter ключ | `sk-or-...` |
| `SECRET_KEY` | JWT секретный ключ | `your-secret` |
| `ADMIN_TELEGRAM_IDS` | ID админов | `123456789,987654321` |
| `TIMEZONE` | Часовой пояс | `Europe/Moscow` |
| `DEBUG` | Debug режим | `false` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

## 🚀 Production развертывание

### На VPS с Nginx

1. **Клонируйте репозиторий**
   ```bash
   git clone https://github.com/benderobo/contentflow.git /opt/contentflow
   cd /opt/contentflow
   ```

2. **Создайте `.env`**
   ```bash
   cp .env.example .env
   # Отредактируйте .env
   ```

3. **Запустите Docker Compose**
   ```bash
   docker compose up -d
   ```

4. **Настройте Nginx**
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
   
       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
       }
   
       location /api/ {
           proxy_pass http://localhost:8000;
       }
   }
   ```

5. **SSL сертификат**
   ```bash
   certbot certonly --nginx -d yourdomain.com
   ```

## 🐛 Troubleshooting

### Bot не отвечает
```bash
docker compose logs bot | tail -50
```

### Ошибки БД
```bash
docker compose exec postgres psql -U contentflow -d contentflow
```

### Worker не обрабатывает задачи
```bash
docker compose restart worker
docker compose logs worker
```

## 📞 Поддержка

- GitHub Issues: https://github.com/benderobo/contentflow/issues
- Email: support@contentflow.bot

## 📄 Лицензия

MIT License - смотрите LICENSE файл

## 🙏 Благодарности

- aiogram - Telegram Bot API
- FastAPI - Web Framework
- Celery - Task Queue
- SQLAlchemy - ORM

---

**Создано с ❤️ для автоматизации контента в Telegram**
