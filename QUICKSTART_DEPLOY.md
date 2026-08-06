# 🚀 Быстрый Деплой на Railway + Vercel (5 минут)

## Вариант 1: Автоматический деплой через GitHub

### Шаг 1: Push на GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/telegram-games-app.git
git push -u origin main
```

### Шаг 2: Настроить GitHub Secrets
В GitHub репозитории → Settings → Secrets and variables → Actions:

Добавьте:
```
TELEGRAM_BOT_TOKEN = 8570031817:AAGgBlOIDZS9hWGpayZnd1nsCQgnJgLVvqw
RAILWAY_BACKEND_PROJECT_ID = (получить из Railway)
VERCEL_TOKEN = (получить из Vercel)
```

### Шаг 3: Push в main
```bash
git add .
git commit -m "Deploy to production"
git push origin main
```

GitHub Actions автоматически:
- ✅ Деплоит backend на Railway
- ✅ Деплоит frontend на Vercel
- ✅ Запускает тесты

---

## Вариант 2: Ручной деплой (Рекомендуется для первого раза)

### 📝 Требования
- Railway аккаунт (railway.app)
- Vercel аккаунт (vercel.com)
- GitHub репозиторий

---

## 🚂 BACKEND на Railway

### Шаг 1: Создать Railway проект

```bash
# Установите Railway CLI
npm install -g @railway/cli

# Авторизуйтесь
railway login

# Создайте новый проект
railway init
```

### Шаг 2: Добавить MongoDB

В Railway dashboard:
1. Откройте ваш проект
2. Нажмите `+ Create`
3. Выберите `Database` → `MongoDB`
4. Railway автоматически добавит `MONGODB_URI`

### Шаг 3: Настроить Environment Variables

В Railway dashboard → Variables → добавьте:

```
TELEGRAM_BOT_TOKEN=8570031817:AAGgBlOIDZS9hWGpayZnd1nsCQgnJgLVvqw
NODE_ENV=production
CORS_ORIGIN=https://your-frontend.vercel.app
WEB_APP_URL=https://your-frontend.vercel.app
PORT=3001
```

### Шаг 4: Деплой Backend

```bash
cd backend

# Деплой на Railway
railway up

# Получить URL
railway open
```

**Скопируйте URL вашего backend** (выглядит как: `https://xxx.railway.app`)

---

## 🎨 FRONTEND на Vercel

### Шаг 1: Подключить репозиторий

1. Откройте vercel.com
2. Нажмите `Import Project`
3. Введите URL вашего GitHub репозитория
4. Выберите `frontend` как root directory

### Шаг 2: Настроить Environment Variables

В Vercel dashboard → Settings → Environment Variables:

```
REACT_APP_WS_URL=wss://your-backend-railway-url.com
REACT_APP_API_URL=https://your-backend-railway-url.com
REACT_APP_BOT_USERNAME=your_bot_username
```

*(Замените URL на реальный backend URL из Railway)*

### Шаг 3: Деплой

Vercel автоматически деплоит при подключении репозитория.

**Скопируйте URL вашего frontend** (выглядит как: `https://xxx.vercel.app`)

---

## 🤖 Финальная настройка Telegram Bot

### В BotFather (@BotFather)

1. Отправьте `/setwebapp`
2. Выберите вашего бота
3. Отправьте URL вашего Vercel frontend:
   ```
   https://your-frontend.vercel.app
   ```

### Тестирование

1. Откройте Telegram и найдите вашего бота
2. Отправьте `/start`
3. Нажмите кнопку "🎮 Играть сейчас"
4. Приложение должно загрузиться! 🎉

---

## 🐛 Troubleshooting

### "WebSocket connection failed"
```
1. Проверьте что REACT_APP_WS_URL использует wss:// (не ws://)
2. Убедитесь что URL backend правильный
3. Обновите CORS_ORIGIN в Railway переменных
```

### "MongoDB connection timeout"
```
1. Проверьте что MongoDB создана в Railway
2. Скопируйте MONGODB_URI из Railway dashboard
3. Убедитесь что все переменные установлены
```

### "Bot не отвечает"
```
1. Проверьте TELEGRAM_BOT_TOKEN в Railway
2. Убедитесь что Web App URL установлен в BotFather
3. Проверьте логи: railway logs
```

---

## 📊 Проверка статуса

### Railway
```bash
railway status
railway logs -f
```

### Vercel
Откройте Vercel dashboard → Deployments → посмотрите логи

---

## ✅ Чек-лист

- [ ] GitHub репозиторий создан
- [ ] Railway проект создан
- [ ] MongoDB добавлена в Railway
- [ ] Environment variables установлены на Railway
- [ ] Backend деплоен на Railway
- [ ] Vercel проект создан
- [ ] Environment variables установлены на Vercel
- [ ] Frontend деплоен на Vercel
- [ ] Web App URL установлен в BotFather
- [ ] `/start` команда работает
- [ ] Приложение загружается в Web App
- [ ] Игры работают

---

## 🎉 Готово!

Ваше приложение теперь доступно для всех пользователей Telegram!

**Бот:** @shlyapa4_bot (или ваше имя бота)

Пригласите друзей и начните играть! 🚀

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи в Railway: `railway logs`
2. Проверьте логи в Vercel Dashboard
3. Убедитесь что все переменные окружения установлены
4. Перезагрузите приложение в Telegram

