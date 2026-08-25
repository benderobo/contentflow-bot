# ContentFlow Bot - Architecture

## 📐 Система архитектуры

```
┌─────────────────────────────────────────────────────────────────┐
│                      TELEGRAM USERS                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │        TELEGRAM BOT (aiogram)         │
        │  - Handlers (menu, posts, channels)  │
        │  - Inline keyboards                   │
        │  - State management                   │
        └──────────┬───────────────────────────┘
                   │
                   ├─────────────────────────────┐
                   │                             │
                   ▼                             ▼
        ┌──────────────────────┐      ┌──────────────────────┐
        │   REST API (FastAPI) │      │   Web Dashboard      │
        │  - Authentication    │      │   (React + TypeScript)
        │  - CRUD operations   │      │  - Post editor       │
        │  - WebSocket support │      │  - Analytics         │
        └──────────┬───────────┘      │  - Settings          │
                   │                  └──────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │    PostgreSQL DB     │
        │  - Users             │
        │  - Sources           │
        │  - Posts             │
        │  - Channels          │
        │  - AI metadata       │
        │  - Audit logs        │
        └──────────┬───────────┘
                   │
        ┌──────────┴───────────┐
        │                      │
        ▼                      ▼
    ┌─────────────┐    ┌──────────────────┐
    │    Redis    │    │  Task Queue      │
    │  - Cache    │    │  (Celery)        │
    │  - Sessions │    │  - Parser tasks  │
    │  - Locks    │    │  - AI tasks      │
    └─────────────┘    │  - Publish tasks │
                       └──────────┬───────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
              ┌────────────┐ ┌─────────┐ ┌────────────┐
              │   Parser   │ │ AI      │ │ Publisher  │
              │  Workers   │ │ Workers │ │  Workers   │
              │            │ │         │ │            │
              │ RSS/Web    │ │ Rewrite │ │ Telegram   │
              │ Parsers    │ │ Analysis│ │ Publishing │
              └────────────┘ └─────────┘ └────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │   External Services      │
                    │                          │
                    │ - OpenAI (ChatGPT)       │
                    │ - OpenRouter             │
                    │ - Anthropic (Claude)     │
                    │ - Ollama (Local)         │
                    │                          │
                    │ - Telegram Bot API       │
                    │ - RSS Feeds              │
                    │ - Web Scraping APIs      │
                    └──────────────────────────┘
```

## 🏗️ Компоненты системы

### 1. Telegram Bot (`bot/`)

**Назначение:** Основной интерфейс пользователя через Telegram.

**Компоненты:**
- `main.py` - Инициализация и запуск бота
- `handlers.py` - Обработчики команд и callback-запросов
- `states.py` - Состояния для FSM
- `keyboards.py` - Инлайн клавиатуры

**Технологии:**
- aiogram 3.x для работы с Telegram Bot API
- Async/await для асинхронной обработки
- State Management для управления потоком пользователя

### 2. REST API (`api/`)

**Назначение:** Программный интерфейс для управления контентом.

**Структура:**
```
api/
├── main.py                # FastAPI приложение
└── routes/
    ├── sources.py         # Управление источниками
    ├── posts.py           # Управление постами
    ├── channels.py        # Управление каналами
    ├── ai.py              # AI операции
    └── stats.py           # Статистика
```

**Endpoints:**
- `GET /api/sources` - Список источников
- `POST /api/posts/{id}/rewrite` - AI переписка
- `POST /api/posts/{id}/publish` - Публикация
- `GET /api/stats/dashboard` - Статистика

### 3. База данных (`models/`, `core/database.py`)

**PostgreSQL схема:**

```sql
-- Пользователи
users (id, telegram_id, username, is_admin, is_active)

-- Источники контента
sources (id, user_id, name, type, url, enabled, parse_interval, last_check)

-- Материалы из источников
source_items (id, source_id, original_url, content_hash, is_duplicate)

-- Посты (готовые к публикации)
posts (id, user_id, source_item_id, title, body, status, scheduled_at)

-- Медиа к постам
post_media (id, post_id, media_type, file_path, original_url)

-- Telegram-каналы
channels (id, user_id, name, telegram_id, enabled, schedule)

-- Очередь публикаций
publish_jobs (id, post_id, channel_id, scheduled_at, status)

-- AI шаблоны
ai_prompts (id, user_id, name, system_prompt, user_prompt, model)

-- История AI запросов
ai_requests (id, user_id, post_id, request_type, input_tokens, output_tokens, cost)

-- Статистика использования AI
ai_usage (id, user_id, date, model, requests, tokens, cost)

-- Индексы на часто запрашиваемые поля
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_scheduled_at ON posts(scheduled_at);
CREATE INDEX idx_source_items_hash ON source_items(content_hash);
CREATE INDEX idx_publish_jobs_scheduled ON publish_jobs(scheduled_at, status);
```

### 4. Background Workers (`workers/`)

**Celery задачи:**

```python
# Parser Worker
@celery.task
async def parse_source(source_id):
    # Получить конфиг источника
    # Запустить парсер (RSS, Website, Telegram)
    # Нормализовать контент
    # Проверить на дубликаты
    # Сохранить source_items

# AI Worker
@celery.task
async def analyze_content(source_item_id):
    # Получить материал
    # Отправить в LLM
    # Распарсить результат
    # Сохранить анализ в post

@celery.task
async def rewrite_post(post_id, prompt_id):
    # Получить пост и шаблон
    # Вызвать LLM с custom prompt
    # Сохранить новый текст

# Publisher Worker
@celery.task
async def publish_post(post_id, channel_id):
    # Получить пост и канал
    # Форматировать для Telegram
    # Отправить в канал
    # Обновить статус
    # Записать метрики
```

**Очередь Celery:**
- Connection: Redis
- Concurrency: 4 workers
- Retry: exponential backoff
- Dead-letter queue: для ошибок

### 5. Планировщик (`workers/scheduler.py`)

**Функции:**
- Проверка очереди публикаций каждые 60 сек
- Отправка готовых к публикации постов в очередь
- Мониторинг статуса публикации
- Обработка ошибок и повторные попытки

### 6. Сервисы (`services/`)

#### Parser (`services/parser.py`)

```python
class BaseParser:
    async def parse(config) -> list[Item]

class RSSParser(BaseParser):
    # Парсинг RSS/Atom фидов

class WebsiteParser(BaseParser):
    # Парсинг HTML-страниц
    # BeautifulSoup для извлечения контента

class ParserFactory:
    # Выбор парсера по типу источника
```

#### Deduplication (`services/deduplication.py`)

```python
class DeduplicationService:
    @staticmethod
    def hash_content(text) -> str
        # SHA-256 хеш контента

    @staticmethod
    def similarity_score(text1, text2) -> float
        # Cosine similarity

    @classmethod
    def is_duplicate(text, other_text, threshold) -> bool
        # Проверка на дубликат
```

#### AI (`services/ai.py`)

```python
class LLMProvider(ABC):
    async def analyze(text, prompt)
    async def rewrite(text, prompt)

class OpenAIProvider(LLMProvider)
class AnthropicProvider(LLMProvider)
class OllamaProvider(LLMProvider)
class OpenRouterProvider(LLMProvider)

class AIService:
    async def analyze_content(text)
    async def rewrite_content(text, style)
    async def generate_summary(text)
```

## 🔄 Потоки обработки

### Поток парсинга

```
1. Trigger: Пользователь нажимает "Запустить парсинг"
2. Bot → API → Queue (parse_source task)
3. Parser Worker:
   - Получает конфиг источника
   - Запускает парсер (RSS/Web/Telegram)
   - Нормализует контент
   - Проверяет canonical URL
   - Генерирует хеш контента
4. Deduplication:
   - Проверка по URL (exact match)
   - Проверка по хешу
   - Similarity check
5. Database:
   - Создает SourceItem запись
   - Устанавливает is_duplicate флаг
6. Trigger для AI анализа
```

### Поток AI обработки

```
1. Source Item → Queue (analyze_content task)
2. AI Worker:
   - Получает материал
   - Отправляет в LLM (analyze prompt)
   - Парсит JSON ответ
   - Сохраняет анализ
3. Создание Post:
   - Статус: DRAFT
   - Содержимое: исходный контент
   - AI Analysis: результаты анализа
4. Bot уведомляет пользователя
```

### Поток редактирования

```
1. User нажимает "Переписать"
2. Bot → API → Queue (rewrite_post task)
3. AI Worker:
   - Получает пост и шаблон промпта
   - Отправляет в LLM
   - Сохраняет результат
4. Bot показывает предпросмотр
5. User может еще раз переписать или одобрить
```

### Поток публикации

```
1. User нажимает "Опубликовать" или "Запланировать"
2. Если сейчас → Queue (publish_post)
3. Если запланировать → Publish Job в БД
4. Scheduler проверяет очередь каждые 60 сек
5. Если время → Queue (publish_post)
6. Publisher Worker:
   - Получает пост и канал
   - Форматирует для Telegram
   - Загружает медиа
   - Отправляет сообщение
   - Обновляет статус на PUBLISHED
   - Записывает метрики
```

## 🔐 Безопасность

### Authentication & Authorization

- **Telegram**: Валидация через bot token
- **Whitelist**: Admin IDs в переменных окружения
- **API**: JWT токены (опционально)
- **Database**: SQL параметризованные запросы

### Data Protection

- **API Keys**: Только в environment variables
- **Passwords**: bcrypt хеширование
- **Secrets**: Не логировать sensitive данные
- **HTTPS**: Обязателен в production

### Rate Limiting

- Telegram API rate limit: 30 req/sec
- Parser concurrency limit: 10 одновременно
- AI request timeout: 30 сек
- Database connection pooling: 20-30 connections

## 📊 Масштабируемость

### Горизонтальное масштабирование

```
# Несколько worker инстансов
docker compose up -d --scale worker=4

# Несколько parser инстансов
docker compose up -d --scale parser-worker=2
```

### Оптимизация производительности

- **Database**: Индексы на часто используемых полях
- **Cache**: Redis для сессий и lock'ов
- **Queue**: Celery с оптимальным размером пула
- **Async**: Везде где возможно async/await

## 🚀 Развертывание

### Development

```bash
docker compose up
# или локально
python -m bot.main &
python -m uvicorn api.main:app --reload &
celery -A workers.tasks worker &
python -m workers.scheduler &
```

### Production

```bash
# На VPS
docker compose -f docker-compose.yml up -d
# + Nginx reverse proxy
# + SSL сертификат (Let's Encrypt)
# + Monitoring (Prometheus/Grafana)
# + Logging (ELK Stack)
```

## 📝 Логирование

**Structured logging с JSON:**

```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "level": "info",
  "service": "parser-worker",
  "event": "parse_complete",
  "source_id": 42,
  "items_found": 15,
  "duration_ms": 2340
}
```

**Уровни:**
- DEBUG: детальная информация для отладки
- INFO: важные события
- WARNING: потенциальные проблемы
- ERROR: ошибки
- CRITICAL: критические ошибки

## 🧪 Тестирование

### Unit Tests
- Парсеры (`test_parser.py`)
- Дедупликация (`test_deduplication.py`)
- AI интеграция (`test_ai.py`)

### Integration Tests
- Source → Parser → DB
- Post → AI → Update
- Publish Job → Queue → Telegram

### E2E Tests
- Полный цикл: Source → Publish → Verify

---

**Архитектура позволяет:**
- ✅ Масштабировать независимо
- ✅ Заменять компоненты
- ✅ Добавлять новые источники
- ✅ Поддерживать несколько AI провайдеров
- ✅ Обрабатывать большие объемы контента
