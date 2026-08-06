# 🔐 SECURITY NOTICE - TELEGRAM BOT TOKEN

## ⚠️ ВАЖНО: Если вы видели токен в коде

Если в каком-то из документов, скриптов или примеров вы видели реальный Telegram Bot Token (выглядит как `8570031817:AAGgBlOIDZS9hWGpayZnd1nsCQgnJgLVvqw`):

### 🚨 ЭТО УЯЗВИМОСТЬ!

**Немедленно сделайте:**

1. **Отозвите токен в BotFather:**
   ```
   Откройте Telegram → @BotFather
   Отправьте /revoke
   Выберите своего бота
   Выберите токен
   ```

2. **Получите новый токен:**
   ```
   В BotFather отправьте /token
   Выберите своего бота
   Скопируйте новый токен
   ```

3. **Обновите переменные:**
   - Railway: `railway variable set TELEGRAM_BOT_TOKEN "your_new_token"`
   - Environment: `export TELEGRAM_BOT_TOKEN="your_new_token"`

---

## 🔒 BEST PRACTICES для Telegram Bot Token

### ✅ ДЕЛАЙТЕ:
- ✅ Храните токен в `.env` файлах
- ✅ Добавьте `.env` в `.gitignore`
- ✅ Используйте environment variables в production
- ✅ Никогда не коммитьте токены
- ✅ Используйте Railway Secret Variables
- ✅ Используйте Vercel Environment Variables
- ✅ Регулярно меняйте токены

### ❌ НЕ ДЕЛАЙТЕ:
- ❌ Не пишите токены в коде
- ❌ Не публикуйте токены в документах
- ❌ Не отправляйте токены по email
- ❌ Не коммитьте токены в git
- ❌ Не делитесь токенами в Telegram
- ❌ Не используйте один токен для разных приложений

---

## 🛡️ Как правильно использовать токен

### В development (.env файл)
```bash
# .env (НЕ ДОБАВЛЯЙТЕ В GIT!)
TELEGRAM_BOT_TOKEN=your_actual_token_here
NODE_ENV=development
```

### В production (Railway)
```bash
# Через CLI:
railway variable set TELEGRAM_BOT_TOKEN "your_token"

# Или через Dashboard:
# Settings → Variables → Add Variable
# Name: TELEGRAM_BOT_TOKEN
# Value: your_token
```

### В production (Vercel)
```bash
# Settings → Environment Variables
# Name: (если нужен на frontend - используйте REACT_APP_ префикс)
```

### В коде
```javascript
// Используйте environment variables, НИКОГДА hardcoded:
const token = process.env.TELEGRAM_BOT_TOKEN;

if (!token) {
    throw new Error('TELEGRAM_BOT_TOKEN is not set!');
}

const bot = new TelegramBot(token, { polling: true });
```

---

## 📋 Правильная структура .env

### Backend (.env)
```
# БЕЗ КАВЫЧЕК! (часто ошибка)
TELEGRAM_BOT_TOKEN=8570031817:AAGgBlOIDZS9hWGpayZnd1nsCQgnJgLVvqw
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/db
NODE_ENV=production
CORS_ORIGIN=https://your-frontend.vercel.app
WEB_APP_URL=https://your-frontend.vercel.app
PORT=3001
```

### Frontend (.env)
```
# Только REACT_APP_ переменные видны на frontend!
REACT_APP_WS_URL=wss://your-backend.railway.app
REACT_APP_API_URL=https://your-backend.railway.app
# НЕ ДОБАВЛЯЙТЕ ТОКЕНЫ НА FRONTEND!
```

---

## 🔍 Как проверить что всё в порядке

### В git
```bash
# Проверьте что .env в .gitignore
cat .gitignore | grep "\.env"

# Проверьте что токенов нет в истории
git log -p | grep -i "TELEGRAM_BOT_TOKEN" | head -5

# Проверьте коммиты
git grep "8570031817" || echo "✅ Нет токенов в коде"
```

### В проекте
```bash
# Поищите все упоминания токена
grep -r "8570031817" . --exclude-dir=node_modules || echo "✅ OK"
grep -r "AAGgBlOIDZS9" . --exclude-dir=node_modules || echo "✅ OK"
```

---

## 📞 Что делать если токен был скомпрометирован

1. **Немедленно отозвите токен в BotFather** (/revoke)
2. **Получите новый токен** (/token)
3. **Обновите везде:**
   - Railway переменные
   - Vercel переменные
   - Все .env файлы
   - Запустите новый деплой
4. **Проверьте логи** - не было ли несанкционированного доступа
5. **Усильте security:**
   - Проверьте что только вы имеете доступ к Railway/Vercel
   - Включите 2FA везде где возможно
   - Регулярно меняйте пароли

---

## ✅ ИТОГОВЫЙ ЧЕК-ЛИСТ БЕЗОПАСНОСТИ

- [ ] .env файлы НЕ в git
- [ ] .env добавлены в .gitignore
- [ ] Токенов нет в коде
- [ ] Токенов нет в документации
- [ ] Environment variables используются везде
- [ ] Railway переменные установлены
- [ ] Vercel переменные установлены
- [ ] Скрипты запрашивают токены при запуске
- [ ] Токен тестирован и работает
- [ ] 2FA включена на Railway/Vercel

---

## 🎯 ГЛАВНОЕ ПРАВИЛО

**НИКОГДА не публикуйте, не коммитьте и не документируйте реальные Telegram Bot токены!**

Если вы случайно опубликовали - немедленно отозвите через BotFather и получите новый.

