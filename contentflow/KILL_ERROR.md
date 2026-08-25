# 🐛 ContentFlow Bot - Журнал ошибок и решений

## ✅ Исправленные ошибки

### 1. **RedisStorage key_builder AttributeError** (Сессия 1)
- **Ошибка**: `AttributeError: 'function' object has no attribute 'build'`
- **Причина**: Передача lambda вместо DefaultKeyBuilder в RedisStorage
- **Решение**: `RedisStorage(redis=redis, key_builder=DefaultKeyBuilder())`
- **Файл**: `bot/main.py`

### 2. **FastAPI HTTPAuthCredentials ImportError** (Сессия 1)
- **Ошибка**: `ImportError: cannot import name 'HTTPAuthCredentials' from 'fastapi.security'`
- **Причина**: Класс не существует в fastapi.security
- **Решение**: Переписать `get_current_user()` с ручной экстракцией JWT из Authorization header
- **Файл**: `api/dependencies.py`

### 3. **Missing Model Imports** (Сессия 1)
- **Ошибка**: `NameError: name 'get_current_user' is not defined`
- **Причина**: Функции используются в Depends() но не импортируются
- **Решение**: Добавить импорты в `api/routes/posts.py`
- **Файл**: `api/routes/posts.py`

### 4. **Python 3.8 Type Hints Incompatibility** (Сессия 1)
- **Ошибка**: `TypeError: 'type' object is not subscriptable` при использовании `list[Dict[str, Any]]`
- **Причина**: Python 3.8 не поддерживает PEP 585 (built-in generic types требуют Python 3.9+)
- **Решение**: Использовать `List[Dict[str, Any]]` из typing модуля
- **Файлы**: `services/parser.py`, `core/config.py`

### 5. **Markdown Parsing Errors in Settings UI** (Сессия 1)
- **Ошибка**: `TelegramBadRequest: Can't find end of the entity starting at byte offset 66`
- **Причина**: Markdown парсер ломается на @username и специальных символах
- **Решение**: Удалить `parse_mode="Markdown"` из settings handlers
- **Файлы**: `bot/handlers.py` (settings_profile, settings_general, settings_security)

### 6. **API Connectivity - DNS Resolution Failure** (Сессия 1)
- **Ошибка**: `ConnectError: [Errno -3] Temporary failure in name resolution`
- **Причина**: API_URL не установлена, бот пытался подключиться к "http://api:8000" которого нет в DNS
- **Решение**: Добавить `API_URL=http://contentflow-api:8000` в .env
- **Файл**: `.env`

### 7. **Telegram User ID Out of int32 Range** (Сессия 1)
- **Ошибка**: `NumericValueOutOfRangeError: integer out of range` и `invalid input for query argument $1: 5264530602 (value out of int32 range)`
- **Причина**: Telegram user ID 5264530602 превышает max int32 (2,147,483,647)
- **Решение**: Изменить все user_id колонки с Integer на BigInteger в 10 моделях
- **Файлы**: `models/*.py` (user, source, post, channel, ai_request, setting, ai_usage, ai_prompt, audit_log, category)
- **Важно**: Полный reset БД со новой схемой

### 8. **ForeignKeyViolationError - User Not Found** (Сессия 1)
- **Ошибка**: `insert or update on table "sources" violates foreign key constraint... Key (user_id)=(5264530602) is not present in table "users"`
- **Причина**: Пользователь пытался добавить source до регистрации в БД
- **Решение**: Создать систему регистрации юзеров через /api/users endpoint, триггер на /start команду
- **Файлы**: `bot/handlers.py`, `api/routes/users.py`

### 9. **Admin Notification to Bot ID** (Сессия 2)
- **Ошибка**: `Telegram server says - Forbidden: the bot can't send messages to the bot`
- **Причина**: Админ ID установлен как ID бота (8660988275) вместо реального пользователя
- **Решение**: Изменить admin_id на настоящий user_id пользователя (5264530602)
- **Файлы**: `bot/handlers.py` (строки 48, 76)

### 10. **PATCH Request Missing user_id** (Сессия 2)
- **Ошибка**: `HTTP/1.1 400 Bad Request` при подтверждении пользователя
- **Причина**: PATCH /api/users/{user_id} не получал user_id в JSON body
- **Решение**: Добавить `"user_id": callback.from_user.id` в JSON payload
- **Файлы**: `bot/handlers.py` (handle_approve_user, handle_reject_user)

### 11. **Query Parameter Parsing TypeError** (Сессия 2)
- **Ошибка**: `TypeError: Mapping.get() got an unexpected keyword argument 'type'`
- **Причина**: `request.query_params.get("user_id", type=int)` не поддерживается
- **Решение**: Ручное преобразование: `int(request.query_params.get("user_id"))`
- **Файлы**: `api/routes/sources.py`, `api/routes/channels.py`, `api/routes/stats.py`, `api/routes/posts.py`

### 12. **Settings ValidationError - Empty Telegram API ID** (Сессия 2)
- **Ошибка**: `ValidationError: Input should be a valid integer, unable to parse string as an integer`
- **Причина**: TELEGRAM_API_ID в .env пуста, но поле не Optional
- **Решение**: Добавить field_validator для преобразования пустых строк в None
- **Файлы**: `core/config.py` (добавлен @field_validator)

### 13. **PII/Secrets in Logs** (Сессия 2)
- **Ошибка**: Security finding - логирование user_signature
- **Причина**: Секретные данные попадают в логи
- **Решение**: Redact sensitive fields перед логированием
- **Файлы**: `api/routes/users.py` (PATCH endpoint logging)

---

## 📋 Текущий статус

### ✅ Реализовано:
- [x] Пользовательская регистрация и одобрение админом
- [x] Разделение данных по пользователям (источники, посты, каналы)
- [x] Поддержка открытых Telegram каналов
- [x] Поддержка закрытых Telegram каналов (с TELEGRAM_PHONE)
- [x] API endpoints для источников, постов, каналов
- [x] Безопасность: JWT + HMAC подписи
- [x] Логирование без утечек секретов

### 🔄 В процессе:
- [ ] Тестирование системы подтверждения пользователей
- [ ] Парсинг закрытых каналов (требует TELEGRAM_API_ID и TELEGRAM_PHONE)

### ⚠️ Известные ограничения:
- Закрытые каналы требуют настройки TELEGRAM_PHONE и аккаунт должен быть членом канала
- Query ID timeout при нажатии на старые inline кнопки после перезагрузки бота (нормально)

---

## 🛠️ Инструменты для отладки

### Просмотр логов:
```bash
docker logs contentflow-bot -n 50
docker logs contentflow-api -n 50
docker logs contentflow-db
```

### Проверка БД:
```bash
docker exec contentflow-db psql -U contentflow -d contentflow -c "SELECT * FROM users;"
```

### Перезагрузка контейнеров:
```bash
docker stop contentflow-bot contentflow-api
docker rm contentflow-bot contentflow-api
# Пересобрать и запустить
```

---

## 📝 Notes
- Все BigInteger изменения требуют полного сброса БД
- Валидаторы Pydantic используют mode='before' для обработки пустых строк из .env
- telethon требует номер телефона для аутентификации при парсинге закрытых каналов
