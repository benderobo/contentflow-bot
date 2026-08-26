# ContentFlow Bot - ПОЛНЫЙ АУДИТ ПРОЕКТА

## СТАТУС: КРИТИЧЕСКИЙ - ПРОЕКТ НЕ ФУНКЦИОНАЛЕН

---

## 1. АРХИТЕКТУРА ПРОЕКТА

### Точки входа:
- **Bot**: `./bot/main.py` - Telegram bot (aiogram)
- **API**: `./api/main.py` - FastAPI REST API

### Основные компоненты:
```
├── bot/
│   ├── main.py (entrypoint)
│   ├── handlers.py (main handlers - 14KB, большой файл)
│   ├── auth.py (authentication)
│   ├── channel_handlers.py
│   ├── post_handlers.py
│   ├── source_handlers.py
│   ├── ai_handlers.py
│   ├── scheduler_handlers.py
│   └── stats_handlers.py
├── api/
│   ├── main.py (entrypoint)
│   ├── dependencies.py (auth)
│   └── routes/
│       ├── sources.py
│       ├── posts.py
│       ├── channels.py
│       ├── ai.py
│       └── stats.py
├── core/
│   ├── config.py (settings)
│   ├── database.py (async SQLAlchemy)
│   └── security.py (JWT, HMAC)
├── models/ (SQLAlchemy ORM)
├── services/ (business logic)
├── workers/ (Celery background tasks)
└── utils/
```

### Stack:
- **Bot Framework**: aiogram 3.x
- **Web Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy async
- **Task Queue**: Celery + Redis
- **Authentication**: JWT + HMAC
- **AI Providers**: OpenAI, Anthropic, Ollama

---

## 2. КРИТИЧЕСКИЕ ПРОБЛЕМЫ (P0)

### ❌ PARSERS - ПОЛНОСТЬЮ НЕ ФУНКЦИОНАЛЬНЫ

**File**: `services/parser.py`

```python
class ParserFactory:
    _parsers = {
        "rss": RSSParser,
        "website": WebsiteParser,
    }
    
    @classmethod
    def get_parser(cls, source_type: str) -> Optional[BaseParser]:
        parser_class = cls._parsers.get(source_type.lower())
        return parser_class() if parser_class else None
```

**Проблема**: Тип "telegram" не зарегистрирован, хотя UI предлагает его добавлять.

**RSSParser**:
```python
async def parse(self, config: Dict[str, Any]) -> list[Dict[str, Any]]:
    url = config.get("url")
    if not url or not self._validate_url(url):
        return []  # ⚠️ МОЛЧА ВОЗВРАЩАЕТ ПУСТО
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, ...) as resp:
                # ...
            return items
    except Exception as e:
        logger.error(f"RSS parse error: {e}")
        return []  # ⚠️ НЕ ЛОГИРУЕТ ВСЕ ОШИБКИ
```

**WebsiteParser**: Пустой return [] везде, настоящей реализации парсинга нет.

**Impact**: Источники добавляются в БД, но:
- RSS не парсится
- Веб-сайты не парсятся
- Telegram каналы вообще не поддерживаются
- У пользователя есть UI для добавления, но ничего не работает

---

### ❌ API ROUTES - НЕДОДЕЛАНЫ

**File**: `api/routes/ai.py`

```python
@router.post("/analyze")
async def analyze_content(user_id: int, text: str, db: AsyncSession = Depends(get_db)):
    """Analyze content using AI."""
    # TODO: Queue AI analysis task
    return {"message": "Analysis queued"}
```

```python
@router.post("/rewrite")
async def rewrite_content(user_id: int, text: str, style: str = "neutral", db: AsyncSession = Depends(get_db)):
    """Rewrite content using AI."""
    # TODO: Queue AI rewrite task
    return {"message": "Rewrite queued"}
```

**Impact**: AI endpoints возвращают fake responses без реальной обработки.

---

### ❌ SCHEDULER - НЕПРАВИЛЬНАЯ АРХИТЕКТУРА

**File**: `workers/scheduler.py`

```python
async def run_scheduler():
    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Find all pending jobs that are due
                result = await db.execute(
                    select(PublishJob).where(
                        PublishJob.status.in_(["pending", "failed"]),
                        PublishJob.scheduled_at <= datetime.utcnow(),
                        PublishJob.retry_count < PublishJob.max_retries
                    )
                )
                pending_jobs = result.scalars().all()

                for job in pending_jobs:
                    # Queue the publish task
                    publish_post.delay(job.post_id, job.channel_id)
```

**Проблема**: 
- Scheduler работает в памяти
- После перезагрузки контейнера очередь Celery теряется
- Нет гарантии, что задача выполнится

---

### ❌ TELEGRAM PUBLISHING - ВООБЩЕ НЕ РЕАЛИЗОВАНО

**File**: `workers/tasks.py`

```python
async def _publish_post_async(post_id: int, channel_id: int):
    """Async implementation of post publishing."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()

        if not post:
            return

        try:
            from aiogram import Bot

            bot = Bot(token=settings.bot_token)  # ⚠️ БОТ СОЗДАЕТСЯ КАЖДЫЙ РАЗ
            await bot.send_message(
                chat_id=channel.telegram_id,
                text=message_text,
                parse_mode="HTML"
            )
            # ...
        except Exception as e:
            logger.error(f"Error publishing post {post_id}: {e}")
```

**Проблемы**:
- Bot инстанс создается каждый раз
- Нет обработки ошибок (не отличает временные ошибки от постоянных)
- Нет retry mechanism
- Нет timeout handling
- Нет rate limit handling

---

### ❌ DATABASE - SCHEMA БЕЗ CONSTRAINTS

**Table**: `source_items`

```sql
CREATE TABLE source_items (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    original_url VARCHAR(2048) UNIQUE NOT NULL,
    -- ...
);
```

**Проблема**: 
- Нет UNIQUE constraint на content_hash
- Нет дублирования защиты при Race Condition
- Если два worker одновременно получают одинаковый материал - создадут две запись

**Table**: `posts`

```sql
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    source_item_id INTEGER REFERENCES source_items(id),
    rewrite_candidate VARCHAR,  -- ⚠️ ЧТО ЭТО?
    rewrite_original VARCHAR,   -- ⚠️ VARCHAR ДЛЯ БОЛЬШИХ ТЕКСТОВ?
    -- ...
);
```

---

### ❌ BOT HANDLERS - НЕПРАВИЛЬНЫЕ РОУТЕРЫ

**File**: `bot/main.py`

```python
async def main():
    # Create bot and dispatcher with FSM storage
    bot = Bot(token=settings.bot_token)
    storage = MemoryStorage()  # ⚠️ В ПАМЯТИ! ТЕРЯЕТСЯ ПРИ РЕСТАРТЕ
    dp = Dispatcher(storage=storage)

    # Register handlers
    register_handlers(dp)
    dp.include_router(channel_router)
    dp.include_router(post_router)
    dp.include_router(source_router)
    dp.include_router(ai_router)
    dp.include_router(scheduler_router)
    dp.include_router(stats_router)
```

**Проблема**: Используется `MemoryStorage()` вместо Redis. После рестарта все FSM states теряются.

---

## 3. ФУНКЦИОНАЛЬНОСТЬ - КАРТА СТАТУСА

| Раздел | Функция | Handler | Service | API | DB | Статус |
|--------|---------|---------|---------|-----|----|---------| 
| Источники | Добавить | ✅ | ✅ | ✅ | ✅ | ⚠️ API OK, парсер нет |
| Источники | Список | ✅ | ✅ | ✅ | ✅ | ✅ |
| Источники | Парсинг | ❌ | ❌ (return []) | ❌ (TODO) | N/A | ❌ СЛОМАНО |
| Посты | Создать | ✅ | ? | ✅ | ✅ | ⚠️ Зависит от источников |
| Посты | Редактировать | ✅ | ? | ? | ✅ | ❓ |
| Посты | Удалить | ✅ | ? | ❌ | ✅ | ❓ |
| AI | Переписать | ✅ | ✅ | ❌ (TODO) | ? | ❌ ТОЛЬКО UI |
| AI | Анализировать | ✅ | ✅ | ❌ (TODO) | ? | ❌ ТОЛЬКО UI |
| Планировщик | Запланировать | ✅ | ✅ | ✅ | ✅ | ⚠️ Но архитектура плохая |
| Планировщик | Выполнить | ✅ | ❌ | N/A | ✅ | ❌ PUBLISHING СЛОМАНО |
| Каналы | Добавить | ✅ | ✅ | ✅ | ✅ | ✅ |
| Каналы | Публикация | ❌ | ❌ | ❌ | ✅ | ❌ НЕ РАБОТАЕТ |
| Статистика | Просмотр | ✅ | ✅ | ✅ | ✅ | ✅ (fake data?) |

---

## 4. КОНКРЕТНЫЕ БАГИ

### 4.1 IDOR Vulnerabilities
✅ Исправлены: user_signature добавлена везде

### 4.2 SSRF Protection
✅ Реализована в `services/parser.py` через `validate_public_url()`

### 4.3 FSM Storage
❌ **MemoryStorage** - теряется при рестарте, должно быть Redis

### 4.4 Telegram Bot Instance
❌ **Создается каждый раз** в `workers/tasks.py`
- Должен быть singleton
- Должен быть переиспользуемым

### 4.5 Error Handling
❌ **Везде `return []` без логирования**
- RSS parser
- Website parser
- API endpoints

### 4.6 Race Conditions
❌ **Deduplication**
- Нет atomic check-insert в БД
- Два worker могут одновременно создать two source_items for same URL

### 4.7 Timezone Handling
❌ **scheduler_handlers.py** - использует `datetime.utcnow()` без timezone awareness
- Может привести к неправильному timing в разных timezones

### 4.8 Database Constraints
❌ Миграции не создают proper constraints на deduplication

---

## 5. НЕДОСТАЮЩИЕ ФУНКЦИИ (РЕАЛИЗОВАНЫ В КОДЕ, НО НЕ РАБОТАЮТ)

### Publishing Pipeline
```
Post Created
    ↓
AI Rewrite (TODO: не работает)
    ↓
Schedule (работает)
    ↓
Publish to Telegram (❌ Не работает)
    ↓
Update Statistics (❌ Fake data)
```

### Content Parsing Pipeline
```
Add Source (работает)
    ↓
Fetch (❌ return [] везде)
    ↓
Parse (❌ return [] везде)
    ↓
Deduplicate (⚠️ неправильная)
    ↓
Create Post (зависит от парсинга)
```

---

## 6. TODO И MOCK RESPONSES

### api/routes/ai.py
- `# TODO: Implement period filtering` (line ~30)
- `# TODO: Queue AI analysis task` (line ~50)
- `# TODO: Queue AI rewrite task` (line ~60)
- **Impact**: AI endpoints возвращают `{"message": "queued"}` вместо реальной обработки

### api/routes/posts.py
- `# TODO: Implement AI rewrite` (в rewrite_post)

### services/ai.py
- `pass` statements (empty implementations)

### services/parser.py
- `return []` везде при ошибках
- `NotImplementedError` для Telegram parser

---

## 7. КОНФИГУРАЦИЯ И ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ

### .env
```
BOT_TOKEN=8660988275:AAHxamyem5NALsqAUcVRTohpwT7b3KUSgeA  ⚠️ РЕАЛЬНЫЙ ТОКЕН В ГИТЕ!
DATABASE_URL=postgresql://contentflow:contentflow@postgres:5432/contentflow
REDIS_URL=redis://redis:6379/0
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...  ⚠️ РЕАЛЬНЫЙ КЛЮЧ В ГИТЕ!
SECRET_KEY=contentflow-dev-secret-key-change-in-production  ⚠️ ДЕФОЛТ!
```

**Проблемы**:
- Real API keys в гите (security issue)
- Дефолтные значения в production

---

## 8. DOCKER SETUP

### docker-compose.yml
```yaml
services:
  postgres:  ✅
  redis:     ✅
  api:       ✅
  bot:       ❌ ЗАВИСИТ ОТ ДРУГИХ КОМПОНЕНТ
  worker:    ✅
  scheduler: ✅
```

**Проблема**: Bot может запуститься до того как API будет ready.

---

## 9. ИТОГОВЫЙ ВЕРДИКТ

### ✅ Что работает:
1. Bot запускается и показывает UI меню
2. Можно добавлять каналы
3. Можно создавать посты через UI
4. Database соединение работает
5. API запускается

### ❌ Что НЕ работает (critical):
1. **Парсинг источников** - return [] везде
2. **AI обработка** - TODO, mock responses
3. **Telegram публикация** - No retry, no error handling, bot instance per call
4. **Scheduler архитектура** - memory-based, теряется при рестарте
5. **Deduplication** - race conditions
6. **End-to-end workflow** - невозможно пройти от источника до публикации

### ⚠️ Архитектурные проблемы:
1. MemoryStorage вместо Redis для FSM
2. Singleton Bot instance не реализован
3. Scheduler не персистентен
4. Нет database constraints для deduplication
5. Error handling везде через silent return

---

## 10. ПЛАН ВОССТАНОВЛЕНИЯ (ПРИОРИТЕТЫ)

### P0 (Critical - бот не работает):
1. ❌ Реализовать RSS parser (feedparser уже в требованиях)
2. ❌ Реализовать Website parser
3. ❌ Реализовать Telegram parsing
4. ❌ Реализовать Telegram publishing с retry

### P1 (Core pipeline):
5. ❌ Реализовать AI endpoints (не TODO)
6. ❌ Добавить database constraints для deduplication
7. ❌ Исправить FSM storage (Redis instead of Memory)
8. ❌ Исправить Bot singleton

### P2 (Reliability):
9. ❌ Добавить proper error handling
10. ❌ Добавить logging везде
11. ❌ Добавить retry mechanism для publishing
12. ❌ Добавить timezone support

### P3 (Security):
13. ❌ Удалить real API keys из .env (использовать defaults только для dev)
14. ❌ Добавить .env в .gitignore
15. ❌ Проверить rate limiting

### P4 (Quality):
16. ❌ Добавить тесты
17. ❌ Проверить Docker healthchecks

---

## 11. ESTIMATED SCOPE

- **Lines of code to fix/add**: ~3000 LOC
- **Files to modify**: 15+
- **Estimated complexity**: HIGH
- **Risk of regression**: MEDIUM (existing tests unknown)

---

## NEXT STEPS

1. ✅ Показать этот аудит пользователю
2. ❌ Начать P0 fixes по порядку
3. ❌ Проводить E2E тесты после каждого P0 fix
4. ❌ Затем P1-P4 в порядке приоритета
5. ❌ Финальная проверка end-to-end pipeline

---

**Дата аудита**: 2026-08-25  
**Статус проекта**: NOT PRODUCTION READY - REQUIRES CRITICAL FIXES
