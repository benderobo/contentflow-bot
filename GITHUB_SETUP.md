# 📤 Push на GitHub (Приватный репо)

## 🔒 Пошаговая инструкция

### Шаг 1: Создайте приватный репо на GitHub

1. Откройте **https://github.com/new**
2. Заполните форму:
   ```
   Repository name: telegram-games-app
   Description: SHISHKA_VPN Games - Telegram Mini App
   Visibility: ✓ Private
   ```
3. **НЕ инициализируйте** с README (у нас уже есть)
4. Нажмите **"Create repository"**

### Шаг 2: Настройка GitHub SSH или HTTPS

#### Вариант A: HTTPS (рекомендуется для первого раза)

**Создайте Personal Access Token:**
1. Откройте https://github.com/settings/tokens
2. Нажмите **"Generate new token"**
3. Выберите `repo` (полный доступ к репозиториям)
4. Скопируйте токен (он больше не будет виден!)

**Используйте токен для пуша:**
```bash
# Когда git просит пароль:
# Username: ваш GitHub username
# Password: ваш Personal Access Token
```

#### Вариант B: SSH (более безопасный)

**Если у вас уже есть SSH ключ:**
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

**Добавьте публичный ключ на GitHub:**
1. Откройте https://github.com/settings/ssh
2. Нажмите **"New SSH key"**
3. Вставьте содержимое `~/.ssh/id_ed25519.pub`
4. Нажмите **"Add SSH key"**

### Шаг 3: Запушьте код

```bash
# Перейдите в корневую папку проекта
cd /root/.claude/worktrees/telegram-games-app

# Проверьте статус
git status

# Если есть неотслеживаемые файлы - добавьте их
git add .

# Добавьте remote (HTTPS вариант)
git remote add origin https://github.com/YOUR_USERNAME/telegram-games-app.git

# Или добавьте remote (SSH вариант)
git remote add origin git@github.com:YOUR_USERNAME/telegram-games-app.git

# Переименуйте ветку на main если нужно
git branch -M main

# Запушьте код
git push -u origin main
```

**Замените `YOUR_USERNAME` на ваш GitHub username!**

### Шаг 4: Проверьте приватность

1. Откройте https://github.com/YOUR_USERNAME/telegram-games-app
2. Нажмите **Settings** (справа)
3. Найдите **Visibility**
4. Убедитесь что выбрано **Private**

---

## 🔐 Безопасность GitHub

### ✅ ЧТО ДЕЛАТЬ:

- ✅ Используйте **приватный репо** для приватного кода
- ✅ Используйте **Personal Access Token** вместо пароля
- ✅ Используйте **SSH ключи** для регулярного использования
- ✅ **Никогда** не коммитьте `.env` файлы
- ✅ Добавьте правильные люди в **Collaborators** (Settings → Collaborators)

### ❌ НЕ ДЕЛАЙТЕ:

- ❌ Не используйте пароль GitHub для git commands
- ❌ Не коммитьте токены или ключи
- ❌ Не делайте репо публичным если содержит секреты
- ❌ Не даёте token полный доступ если не нужно
- ❌ Не сохраняйте токены в файлах

---

## 📊 Проверка перед пушем

```bash
# Посмотрите что будет запушено
git log --oneline -5

# Проверьте все файлы
git status

# Убедитесь что .env в .gitignore
cat .gitignore | grep "\.env"

# Проверьте что нет токенов в коде
grep -r "TELEGRAM_BOT_TOKEN=" . --exclude-dir=node_modules --exclude-dir=.git
```

---

## 🚨 Если допустили ошибку и запушили секреты

**Немедленно:**

1. **Отозвите токен:**
   - Если это Telegram Bot Token: откройте @BotFather, отправьте /revoke
   - Если это GitHub Token: https://github.com/settings/tokens (удалите)

2. **Очистите git историю:**
   ```bash
   # Удалите файл из истории (ОСТОРОЖНО!)
   git filter-branch --tree-filter 'rm -f .env' HEAD
   
   # Запушьте заново
   git push --force origin main
   ```

3. **Создайте новые токены:**
   - Telegram Bot: получите новый через @BotFather
   - GitHub: создайте новый Personal Access Token

---

## 📝 Структура GitHub репо

```
telegram-games-app/
├── backend/
│   ├── index.js
│   ├── package.json
│   ├── Dockerfile
│   └── ...
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── Dockerfile
│   └── ...
├── .github/
│   └── workflows/
│       └── deploy.yml (CI/CD)
├── .gitignore
├── README.md
├── DEPLOYMENT.md
├── QUICKSTART_DEPLOY.md
├── DEPLOY_CHECKLIST.md
├── SECURITY_NOTICE.md
└── docker-compose.yml
```

**Что НЕ включается в git:**
```
.env
.env.local
node_modules/
build/
dist/
.DS_Store
*.log
```

---

## ✅ После пуша

1. **Проверьте репо на GitHub:**
   ```
   https://github.com/YOUR_USERNAME/telegram-games-app
   ```

2. **Убедитесь что приватный:**
   ```
   Settings → Visibility → Private
   ```

3. **Добавьте collaborators если нужно:**
   ```
   Settings → Collaborators → Add people
   ```

4. **Включите GitHub Actions (для CI/CD):**
   ```
   Actions → I understand my workflows, go ahead and enable them
   ```

5. **Настройте branch protection (опционально):**
   ```
   Settings → Branches → Add rule
   Pattern: main
   ✓ Require pull request reviews
   ✓ Require status checks to pass
   ```

---

## 🎯 Команды для быстрого пуша

```bash
# Первый раз:
git remote add origin https://github.com/YOUR_USERNAME/telegram-games-app.git
git branch -M main
git push -u origin main

# В следующий раз (просто пушьте):
git add .
git commit -m "your message"
git push
```

---

## 📞 Если что-то не работает

### "fatal: 'origin' does not appear to be a 'git' repository"
```bash
# Проверьте remote
git remote -v

# Удалите и добавьте заново
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/telegram-games-app.git
```

### "error: src refspec main does not match any"
```bash
# Переименуйте ветку
git branch -M main

# Или используйте текущую ветку
git branch
```

### "remote: Permission denied"
```bash
# Проверьте Personal Access Token
# Убедитесь что используете правильный username и token
# Попробуйте SSH вместо HTTPS
```

### "fatal: refusing to merge unrelated histories"
```bash
# Удалите локальный .git и начните заново
# ИЛИ используйте флаг
git pull origin main --allow-unrelated-histories
```

---

## 🎉 ВСЁ ГОТОВО!

Ваше приложение теперь в приватном GitHub репо! 🚀

Следующий шаг: Деплой на Railway + Vercel

