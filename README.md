# ☀️ Sunny English — Telegram Bot + Web Dashboard

Интерактивная система управления курсом английского языка с Telegram ботом, веб-сайтом и отслеживанием прогресса студентов.

## 🚀 Основные возможности

- **Telegram бот** (@sunny_englishbot) для управления уроками
- **Интерактивный курс** courseplan.html с 15 уроками
- **Личные дашборды** для каждого студента (прогресс, материалы)
- **Многопользовательская система** (админ + несколько студентов)
- **Webhook интеграция** для real-time обновлений
- **Secure коды приглашения** для доступа студентов

## 📋 Структура проекта

```
sunnyenglish/
├── lessons_server.py         # API сервер + Telegram бот (port 8089)
├── revoke_server.py          # Сервер отзыва доступа (port 8090)
├── courseplan.html           # Курс + админ панель (веб)
├── milasha.html              # Дашборд студента Милаши
├── index.html                # Публичная информация о курсе
├── lessons_progress.json     # Данные прогресса (per-student)
├── invites.json              # Коды приглашения студентов
├── students.json             # Реестр студентов
└── img/                      # Картинки и аватары
```

## 📦 Установка

```bash
# Клонирование
git clone https://github.com/benderobo/sunny_english.git
cd sunny_english/sunnyenglish

# Убедитесь что Python 3.8+ установлен
python3 --version
```

## 🏃 Запуск

### Запуск API сервера и бота

```bash
python3 lessons_server.py
# Сервер доступен на http://localhost:8089
# Webhook слушает POST /api/webhook от Telegram
```

### Запуск веб-сайта

```bash
# Вариант 1: встроенный веб-сервер Python
cd /путь/к/sunnyenglish
python3 -m http.server 8080

# Вариант 2: через nginx
# Proxy на localhost:8089 для /lessons/api/*
```

## 🎯 Использование

### Для администратора

1. **Открыть courseplan.html в браузере**
   ```
   http://localhost:8080/courseplan.html
   ```

2. **Логин с паролем админа**
   - Код/пароль: `noinspiration`

3. **Команды в Telegram боте**
   - `/status` — показать прогресс всех студентов
   - `/close 5` — отметить урок 5
   - `/reset` — очистить прогресс
   - Inline кнопки: ✅ Урок 1-15, 🔄 Сбросить всё

### Для студента

1. **Получить инвайт код**
   - Находится в invites.json (format: `ИМЯСТУДЕНТА-XXXXXX`)

2. **Логиниться через код**
   ```
   http://localhost:8080/courseplan.html?code=ВИКА-YEO086
   ```

3. **Просмотреть личный прогресс**
   - Видеть только свой прогресс
   - Просматривать материалы
   - Отслеживать выполненные уроки

## 🔐 Безопасность

- **Админ пароль**: см. lessons_server.py `ADMIN_PASSWORD`
- **Инвайт коды**: одноразовые в invites.json
- **Telegram токен**: переменная окружения `BOT_TOKEN`
- **Chat ID админа**: `ADMIN_CHAT_ID`

## 🗄️ Структура данных

### lessons_progress.json (per-student)
```json
{
  "милаша": {
    "done": [1, 2, 3, 7, 9, 15],
    "chat_id": "1139186144"
  },
  "вика": {
    "done": [],
    "chat_id": ""
  }
}
```

### invites.json
```json
{
  "ВИКА-YEO086": {
    "child": "Вика",
    "created": 1783283479.822139,
    "active": true
  }
}
```

## 🔄 Архитектура

**Telegram → Webhook → lessons_server.py → JSON → courseplan.html**

1. Админ нажимает кнопку в Telegram боте
2. Callback query отправляется в /api/webhook
3. lessons_server.py обновляет lessons_progress.json
4. courseplan.html делает GET /api/progress?student=имя
5. Браузер показывает обновленный статус в real-time

## 📱 API endpoints

| Метод | Path | Описание |
|-------|------|---------|
| GET | `/api/progress?student=имя` | Получить прогресс студента |
| GET | `/api/verify?password=...` | Логин админа |
| GET | `/api/verify?code=...` | Логин студента |
| POST | `/api/webhook` | Telegram webhook |

## 🚀 Развертывание

### Cloudflare Tunnel
```bash
cloudflared tunnel run --url http://localhost:8089 sunny-english
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY sunnyenglish/ .
EXPOSE 8089
CMD ["python3", "lessons_server.py"]
```

## 📝 Версия

**Status**: ✅ Production ready | **Версия**: 2.0 (Per-student architecture)
