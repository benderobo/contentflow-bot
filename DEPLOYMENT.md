# 🚀 Развертывание Telegram Games Mini App

Полное руководство по развертыванию приложения на production.

## 📋 Предварительные требования

- GitHub аккаунт (для хостинга кода)
- Vercel аккаунт (для frontend)
- Railway аккаунт (для backend + MongoDB)
- Telegram Bot (создан через @BotFather)

## 🔑 Шаг 1: Подготовка Telegram Bot

### Создание бота

1. Откройте Telegram и найдите @BotFather
2. Отправьте `/newbot`
3. Следуйте инструкциям:
   - Придумайте имя бота (например, "My Games Bot")
   - Придумайте username (например, @my_games_bot)
4. Скопируйте **Bot Token** (выглядит как: `123456789:ABCDefGHIjklMNOpqrsTUVwxyz`)

### Регистрация Web App

1. В BotFather отправьте `/setwebapp`
2. Выберите вашего бота
3. Отправьте URL вашего frontend приложения (например: `https://my-games.vercel.app`)

## 📦 Шаг 2: Подготовка кода

### Клонирование репозитория

```bash
git clone https://github.com/yourusername/telegram-games-app.git
cd telegram-games-app
```

### Обновление .env файлов

**backend/.env:**
```
PORT=3001
MONGODB_URI=будет добавлен на Railway
TELEGRAM_BOT_TOKEN=8570031817:AAGgBlOIDZS9hWGpayZnd1nsCQgnJgLVvqw
NODE_ENV=production
CORS_ORIGIN=https://ваш-frontend.vercel.app
WEB_APP_URL=https://ваш-frontend.vercel.app
```

**frontend/.env:**
```
REACT_APP_WS_URL=wss://ваш-backend.railway.app
REACT_APP_API_URL=https://ваш-backend.railway.app
REACT_APP_BOT_USERNAME=my_games_bot
```

## 🚂 Шаг 3: Деплой Backend на Railway

### 1. Инициализация Railway

```bash
npm install -g @railway/cli

# Авторизуемся
railway login

# Переходим в папку backend
cd backend

# Инициализируем проект
railway init
```

### 2. Добавление переменных окружения

```bash
railway variable set TELEGRAM_BOT_TOKEN "8570031817:AAGgBlOIDZS9hWGpayZnd1nsCQgnJgLVvqw"
railway variable set CORS_ORIGIN "https://ваш-frontend.vercel.app"
railway variable set WEB_APP_URL "https://ваш-frontend.vercel.app"
railway variable set NODE_ENV "production"
```

### 3. Добавление MongoDB

```bash
# В Railway dashboard:
# 1. Нажмите "+ Create"
# 2. Выберите "MongoDB"
# 3. Railway автоматически добавит MONGODB_URI
```

### 4. Деплой

```bash
railway up
```

Скопируйте URL вашего backend приложения (выглядит как: `https://xxx.railway.app`)

## 🎨 Шаг 4: Деплой Frontend на Vercel

### 1. Инициализация Vercel

```bash
npm install -g vercel

# Авторизуемся
vercel login

# Переходим в папку frontend
cd ../frontend

# Деплоим
vercel --prod
```

### 2. Добавление переменных окружения

На Vercel dashboard:
1. Перейдите в Settings → Environment Variables
2. Добавьте:
   - `REACT_APP_WS_URL` = `wss://ваш-backend.railway.app`
   - `REACT_APP_API_URL` = `https://ваш-backend.railway.app`

### 3. Пересборка

```bash
vercel --prod
```

## 🔗 Шаг 5: Финальная конфигурация

### Обновление Bot Web App URL

1. В BotFather отправьте `/setwebapp`
2. Выберите вашего бота
3. Отправьте URL вашего frontend приложения на Vercel

### Тестирование

```bash
# Откройте ваш бот в Telegram
# Отправьте /start
# Нажмите кнопку "🎮 Играть сейчас"
# Проверьте что приложение загружается и работает
```

## 🐛 Troubleshooting

### "WebSocket не подключается"

**Проблема:** `WebSocket connection failed`

**Решение:**
```bash
# 1. Проверьте что REACT_APP_WS_URL используется wss:// (не ws://)
# 2. Убедитесь что URL backend правильный
# 3. Проверьте CORS в backend/index.js

# backend/index.js
app.use(cors({
  origin: process.env.CORS_ORIGIN,
  credentials: true
}));
```

### "MongoDB connection error"

**Проблема:** `Error connecting to MongoDB`

**Решение:**
```bash
# 1. В Railway dashboard проверьте что MongoDB создан
# 2. Скопируйте MONGODB_URI с Railway dashboard
# 3. Добавьте в environment variables
railway variable set MONGODB_URI "mongodb+srv://..."
```

### "Telegram Bot не отвечает"

**Проблема:** Bot не реагирует на /start

**Решение:**
```bash
# 1. Проверьте что TELEGRAM_BOT_TOKEN правильный
railway variable set TELEGRAM_BOT_TOKEN "ваш_token"

# 2. Проверьте логи
railway logs -f

# 3. Перезагрузите backend
railway redeploy
```

### "Лидерборд не загружается"

**Проблема:** API возвращает 500 ошибку

**Решение:**
```bash
# Проверьте MongoDB соединение
railway logs | grep -i mongodb

# Проверьте что collection создана
# В MongoDB shell:
# use telegram-games
# db.gamesessions.find()
```

## 📊 Мониторинг

### Логи Backend

```bash
# Real-time логи
railway logs -f

# Последние 100 строк
railway logs | tail -100
```

### Статистика MongoDB

```bash
# В Railway dashboard → MongoDB → Web UI
# Или через MongoDB Atlas:
db.gamesessions.countDocuments()
db.gamesessions.aggregate([{$group: {_id: null, total: {$sum: 1}}}])
```

### Vercel Analytics

Vercel dashboard → Analytics → Web Vitals

## 🔐 Безопасность в Production

### Обновление зависимостей

```bash
# Backend
cd backend
npm update
npm audit fix

# Frontend
cd ../frontend
npm update
npm audit fix
```

### Включение HTTPS

✅ Railway автоматически использует HTTPS
✅ Vercel автоматически использует HTTPS

### Rate Limiting

Добавьте в `backend/index.js`:

```javascript
const rateLimit = require('express-rate-limit');

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});

app.use('/api/', limiter);
```

## 🔄 Continuous Deployment

GitHub Actions автоматически деплоит при пуше на `main`:

```bash
# Просто сделайте коммит и пуш
git add .
git commit -m "Add new feature"
git push origin main

# GitHub Actions автоматически:
# 1. Запустит тесты
# 2. Деплоит backend на Railway
# 3. Деплоит frontend на Vercel
```

## 📈 Масштабирование

### Если приложение медленное

1. **Railway:** Увеличьте CPU/RAM в Settings
2. **Vercel:** Проверьте Build Logs
3. **MongoDB:** Добавьте индексы:
   ```javascript
   db.gamesessions.createIndex({ "results.userId": 1 })
   db.gamesessions.createIndex({ "gameType": 1 })
   ```

### Если много игроков

1. Включите кэширование:
   ```javascript
   const redis = require('redis');
   const cache = redis.createClient();
   ```

2. Используйте CDN для frontend (Vercel это делает автоматически)

3. Масштабируйте MongoDB на MongoDB Atlas

## ✅ Чек-лист развертывания

- [ ] Telegram Bot создан в @BotFather
- [ ] Bot Token добавлен в Railway
- [ ] Backend успешно деплоен на Railway
- [ ] MongoDB подключена к Railway
- [ ] Frontend успешно деплоен на Vercel
- [ ] Environment variables добавлены везде
- [ ] Web App URL установлен в BotFather
- [ ] `/start` команда работает в боте
- [ ] Приложение загружается при нажатии на Web App кнопку
- [ ] Лидерборд работает
- [ ] Игры работают и сохраняют результаты
- [ ] WebSocket соединение стабильно

## 🎉 Готово!

Ваше приложение теперь доступно для всех пользователей Telegram!

Откройте бота: **@shlyapa4_bot**
Нажмите "🎮 Играть сейчас"
Начните играть! 🚀
