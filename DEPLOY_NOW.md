# 🚀 ДЕПЛОЙ НА RAILWAY - ПРЯМО СЕЙЧАС!

## ⚡ БЫСТРЫЙ ПУТЬ (5 минут)

### Шаг 1: Авторизуйтесь на Railway

```bash
# Откройте https://railway.app в браузере
# Авторизуйтесь или создайте аккаунт
```

### Шаг 2: Создайте новый проект

На Railway dashboard:
1. Нажмите **"New Project"**
2. Выберите **"Deploy from GitHub"**
3. Выберите репо **`telegram-games-app`** (если еще не запушили - запушьте сейчас!)
4. Выберите **backend** папку
5. Нажмите **"Deploy"**

### Шаг 3: Добавьте MongoDB

1. В Railway dashboard вашего проекта нажмите **"New"**
2. Выберите **"Database"** → **"MongoDB"**
3. Railway автоматически создаст `MONGODB_URI`

### Шаг 4: Установите Environment Variables

В Railway dashboard → переключитесь на **backend** сервис → **Variables**:

```
TELEGRAM_BOT_TOKEN=8570031817:AAGgBlOIDZS9hWGpayZnd1nsCQgnJgLVvqw
NODE_ENV=production
CORS_ORIGIN=https://YOUR_VERCEL_DOMAIN.vercel.app
WEB_APP_URL=https://YOUR_VERCEL_DOMAIN.vercel.app
PORT=3001
```

*(Замените YOUR_VERCEL_DOMAIN на ваш Vercel домен - узнаете после деплоя frontend)*

### Шаг 5: Получите Backend URL

1. В Railway dashboard посмотрите **Deployments**
2. Найдите **Environment** → **Networking**
3. Скопируйте **Public URL** (выглядит как `https://xxx.railway.app`)

---

## 📋 ПОЛНЫЙ ПРОЦЕСС ДЕПЛОЯ

### Этап 1: GitHub (если еще не запушили)

```bash
# Создайте репо на https://github.com/new
# Имя: telegram-games-app
# Visibility: Private

# Запушьте код:
git remote add origin https://github.com/YOUR_USERNAME/telegram-games-app.git
git branch -M main
git push -u origin main
```

### Этап 2: Railway Backend

```bash
# Установите Railway CLI (если нужен):
npm install -g @railway/cli

# Авторизуйтесь:
railway login

# Инициализируйте проект:
railway init

# Деплой backend:
cd backend
railway up
```

**Или через GitHub:**
1. Откройте https://railway.app
2. New Project → Deploy from GitHub
3. Выберите `telegram-games-app` репо
4. Выберите `backend` папку
5. Deploy!

### Этап 3: MongoDB на Railway

В Railway dashboard:
1. Ваш проект
2. New → Database → MongoDB
3. Автоматически добавится `MONGODB_URI`

### Этап 4: Environment Variables

```bash
# Через CLI (если используете Railway CLI):
railway variable set TELEGRAM_BOT_TOKEN "8570031817:AAGgBlOIDZS9hWGpayZnd1nsCQgnJgLVvqw"
railway variable set NODE_ENV "production"
railway variable set CORS_ORIGIN "https://YOUR_VERCEL.vercel.app"
railway variable set WEB_APP_URL "https://YOUR_VERCEL.vercel.app"
railway variable set PORT "3001"

# Или через Dashboard:
# Backend → Variables → Add Variable
```

### Этаж 5: Проверьте деплой

```bash
# Посмотрите логи:
railway logs -f

# Или в Dashboard:
# Deployments → Latest → Logs
```

---

## 🔗 Backend URLs для Frontend

После успешного деплоя скопируйте **Public URL** и используйте для frontend:

```
REACT_APP_WS_URL=wss://YOUR_RAILWAY_URL
REACT_APP_API_URL=https://YOUR_RAILWAY_URL
```

---

## ✅ Проверка

```bash
# Проверьте что backend работает:
curl https://YOUR_RAILWAY_URL/api/leaderboard

# Должны увидеть JSON ответ (или пустой массив)
# Если ошибка MongoDB - это нормально, главное что backend отвечает!
```

---

## 🎯 Что дальше после Backend деплоя

1. ✅ Скопируйте **Public URL** backend с Railway
2. ⬜ Деплойте Frontend на Vercel (используйте URL backend)
3. ⬜ Установите Web App URL в BotFather
4. ⬜ Играйте в Telegram! 🎮

---

## 🚨 Troubleshooting

### "Build failed"
```
- Проверьте что Dockerfile корректный
- Посмотрите логи в Railway dashboard
- Убедитесь что package.json правильный
```

### "MongoDB connection timeout"
```
- Убедитесь что MongoDB добавлена в Railway
- Проверьте что MONGODB_URI установлена
- Перезагрузите backend деплой
```

### "Port already in use"
```
- Railway использует PORT из переменных
- Убедитесь что PORT=3001 установлена
```

### "Bot token invalid"
```
- Проверьте что TELEGRAM_BOT_TOKEN правильный
- Если в сомнениях - получите новый в @BotFather
```

---

## 📊 Статус деплоя

В Railway dashboard вы должны увидеть:

```
✅ Backend Status: Running
✅ MongoDB Status: Connected
✅ Deployments: Latest build successful
✅ Environment: Production
✅ URL: https://xxx.railway.app
```

---

## 🎉 Готово!

После успешного деплоя:
- ✅ Backend работает на Railway
- ✅ MongoDB подключена
- ✅ API доступен
- ✅ WebSocket работает

**Следующий шаг:** Деплой Frontend на Vercel!

