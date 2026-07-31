# ☀️ Sunny English — Telegram Bot + Web Dashboard

Интерактивная система управления курсом английского языка с Telegram ботом, веб-сайтом и отслеживанием прогресса студентов.

## 🚀 Основные возможности

- **Telegram бот** для управления уроками
- **Интерактивный курс** с 15 уроками
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
├── milasha.html              # Дашборд студента
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

# Создайте .env файл с конфигурацией (не включен в репо):
cat > .env << 'ENVEOF'
BOT_TOKEN=<ваш_telegram_bot_token>
ADMIN_CHAT_ID=<ваш_chat_id_админа>
ADMIN_PASSWORD=<ваш_секретный_пароль>
ENVEOF

chmod 600 .env
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
# Настройте proxy на localhost:8089 для /lessons/api/*
```

## 🎯 Использование

### Для администратора

1. **Открыть courseplan.html в браузере**
   ```
   http://localhost:8080/courseplan.html
   ```

2. **Логин с админ паролем**
   - Введите пароль администратора (установлен в lessons_server.py)

3. **Команды в Telegram боте**
   - `/status` — показать прогресс всех студентов
   - `/close N` — отметить урок N как выполненный
   - `/reset` — очистить прогресс студента
   - Inline кнопки: ✅ Уроки, 🔄 Сбросить всё

### Для студента

1. **Получить инвайт код от админа**
   - Код имеет формат: `ИМЯСТУДЕНТА-XXXXXX`

2. **Логиниться через инвайт код**
   ```
   http://localhost:8080/courseplan.html?code=ИМЯСТУДЕНТА-XXXXXX
   ```
   или введите код вручную в форму логина

3. **Просмотреть личный прогресс**
   - Видеть только свой прогресс
   - Просматривать материалы уроков
   - Отслеживать выполненные уроки

## 🔐 Безопасность

### Защита конфиденциальной информации

- **Bot Token** — передавайте через переменные окружения, НЕ коммитьте в репо
- **Admin Chat ID** — персональный ID админа, держите в секрете
- **Admin Password** — стойкий пароль, меняйте регулярно
- **Invite codes** — одноразовые коды, могут быть деактивированы

### Конфигурация

Все секреты должны быть в файле `.env` или переменных окружения:

```bash
export BOT_TOKEN="your_token_here"
export ADMIN_CHAT_ID="your_id_here"
export ADMIN_PASSWORD="strong_password_here"
python3 lessons_server.py
```

Добавьте `.env` в `.gitignore`:
```bash
echo ".env" >> .gitignore
```

## 🗄️ Структура данных

### lessons_progress.json (per-student)
```json
{
  "student_name": {
    "done": [1, 2, 3, 7, 9, 15],
    "chat_id": "telegram_chat_id"
  }
}
```

### invites.json
```json
{
  "STUDENTNAME-ABC123": {
    "child": "Student Name",
    "created": 1783283479.822139,
    "active": true
  }
}
```

## 🔄 Архитектура

**Telegram → Webhook → lessons_server.py → JSON → courseplan.html**

1. Админ нажимает кнопку в Telegram боте
2. Callback query отправляется в `/api/webhook`
3. `lessons_server.py` обновляет `lessons_progress.json`
4. `courseplan.html` делает GET `/api/progress?student=имя`
5. Браузер показывает обновленный статус в real-time

## 📱 API endpoints

| Метод | Path | Параметры | Описание |
|-------|------|-----------|---------|
| GET | `/api/progress` | `student=имя` | Получить прогресс студента |
| GET | `/api/verify` | `password=...` | Логин админа |
| GET | `/api/verify` | `code=...` | Логин студента |
| POST | `/api/webhook` | (JSON body) | Telegram webhook |

## 🚀 Развертывание

### Cloudflare Tunnel
```bash
cloudflared tunnel create sunny-english
cloudflared tunnel route dns sunny-english example.com
cloudflared tunnel run --url http://localhost:8089 sunny-english
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY sunnyenglish/ .
EXPOSE 8089
ENV BOT_TOKEN=$BOT_TOKEN
ENV ADMIN_CHAT_ID=$ADMIN_CHAT_ID
ENV ADMIN_PASSWORD=$ADMIN_PASSWORD
CMD ["python3", "lessons_server.py"]
```

### Systemd Service

Создайте `/etc/systemd/system/sunny-english.service`:
```ini
[Unit]
Description=Sunny English Bot and API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/sunny-english
EnvironmentFile=/opt/sunny-english/.env
ExecStart=/usr/bin/python3 lessons_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 📝 Лицензия

Приватный проект.

---

**Status**: ✅ Production ready | **Version**: 2.0 (Per-student architecture)
