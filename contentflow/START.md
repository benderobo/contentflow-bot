# 🚀 Запуск ContentFlow Bot

## ✅ Предварительные требования

- ✅ Docker & Docker Compose установлены
- ✅ `.env` файл с параметрами (уже создан)
- ✅ Telegram Bot Token от @BotFather
- ✅ AI API ключ (OpenRouter/OpenAI/Anthropic/Ollama)

## 🎯 Пошаговый запуск

### Шаг 1: Проверить .env

```bash
cat .env
# Убедитесь что там:
# - BOT_TOKEN=8660988275:AAHx...
# - OPENROUTER_API_KEY=sk-or-... (или другой AI ключ)
# - ADMIN_TELEGRAM_IDS=ваш-id
```

### Шаг 2: Запустить Docker Compose

```bash
# Запустить все сервисы
docker compose up -d

# Проверить что все поднялось
docker compose ps
```

**Должны быть статусы `Up`:**
```
bot         (Telegram Bot)
api         (REST API на порту 8000)
postgres    (База данных)
redis       (Кэш)
worker      (Фоновые задачи)
scheduler   (Планировщик)
web         (Dashboard на порту 3000)
```

### Шаг 3: Проверить логи

```bash
# Смотреть логи бота (должны быть сообщения о запуске)
docker compose logs -f bot

# Если видите "Bot started" - всё работает! ✅
```

### Шаг 4: Протестировать бота

1. Откройте **Telegram**
2. Найдите бота по токену: **@8660988275_bot** (или как вы его назвали)
3. Отправьте `/start`
4. Должно появиться главное меню с 7 кнопок

## 🎮 Первый тест

**Нажимайте кнопку "📥 Источники":**
- ➕ Добавить источник
- Выбирайте тип: `rss` или `website`
- Вводите URL: `https://example.com`
- Сохраняйте

**Затем "📝 Посты":**
- Должны появиться найденные материалы

## 🆘 Если что-то не работает

### Бот не отвечает

```bash
# 1. Проверить статус
docker compose ps bot

# 2. Посмотреть ошибки
docker compose logs bot | tail -50

# 3. Перезагрузить
docker compose restart bot
```

### Ошибка подключения к БД

```bash
# Проверить postgres
docker compose logs postgres | tail -20

# Перезагрузить БД
docker compose restart postgres

# Очистить данные (ОПАСНО!)
docker compose down -v
docker compose up -d
```

### API не работает

```bash
# Проверить API контейнер
docker compose logs api | tail -50

# Проверить доступность
curl http://localhost:8000/health

# Должен вернуть: {"status":"ok"}
```

## 📊 Доступные сервисы

| Сервис | URL | Назначение |
|--------|-----|-----------|
| **Bot** | Telegram | Основной интерфейс |
| **API** | http://localhost:8000 | REST API |
| **Docs** | http://localhost:8000/docs | Swagger документация |
| **Web** | http://localhost:3000 | Dashboard |
| **Database** | localhost:5432 | PostgreSQL |
| **Cache** | localhost:6379 | Redis |

## 🔧 Полезные команды

```bash
# Остановить все
docker compose down

# Перезапустить конкретный сервис
docker compose restart bot

# Просмотреть логи всех сервисов
docker compose logs -f

# Удалить всё (включая данные)
docker compose down -v

# Пересобрать образы
docker compose build --no-cache

# Запустить тесты
docker compose exec bot pytest tests/
```

## 🎓 Дальше

После успешного запуска:

1. **Добавьте источник** (RSS, сайт или Telegram канал)
2. **Настройте AI провайдера** (OpenRouter, OpenAI и т.д.)
3. **Добавьте Telegram-канал** для публикации
4. **Запустите парсинг** - бот найдет контент
5. **Отредактируйте посты** через бот или Web App
6. **Опубликуйте** или запланируйте публикацию

---

**✅ Готово к запуску!**

Если возникнут вопросы или ошибки - писать логи и я помогу отладить.
