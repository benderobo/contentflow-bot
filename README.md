# 🎮 Telegram Games Mini App

Многопользовательское приложение Telegram с 3 интерактивными играми, где игроки могут соревноваться в реальном времени и отслеживать свои результаты в глобальном лидерборде.

## 📋 Основные функции

### 🎮 Три типа игр

1. **📚 Угадайка** - Викторина с быстрыми ответами
   - Вопрос показывается всем одновременно
   - Первый правильный ответ: +3 балла
   - Второй: +2 балла
   - Третий: +1 балл
   - Таймер: 10 сек на вопрос

2. **⭕ Крестики-нолики (5×5)** - Классический поединок
   - Поле 5×5 (вместо стандартного 3×3)
   - Нужно собрать 3 подряд
   - Побеждающий ход видят все игроки
   - Победитель: +10 баллов
   - Ничья: +3 балла

3. **🎵 Рифма в спешке** - Творческая игра со словами
   - Найдите рифму к слову за 30 сек
   - Остальные голосуют за лучшую рифму
   - За каждый голос: +1 балл
   - За лучшую рифму: +5 баллов
   - Real-time рейтинг рифм

### 🏆 Лидерборд и статистика
- Глобальный топ-10 игроков
- Личная статистика (кол-во игр, общий счет)
- История всех результатов
- Достижения и бейджи (в планах)

### 🔄 Мультиплеер
- 2-8 игроков в одной сессии
- Real-time обновление через WebSocket
- Синхронное отображение результатов
- Приглашение друзей через реферальные ссылки
- Graceful disconnect handling

## 🚀 Быстрый старт

### Требования
- Node.js 18+
- MongoDB 7+
- Docker & Docker Compose (опционально)

### Локальное развертывание

#### С Docker Compose (рекомендуется)

```bash
# Клонируем репозиторий
git clone <repo-url>
cd telegram-games-app

# Создаем .env файлы (уже существуют)
# Убедитесь что установлен TELEGRAM_BOT_TOKEN

# Запускаем все сервисы
docker-compose up -d

# Приложение будет доступно:
# Frontend: http://localhost:3000
# Backend API: http://localhost:3001
# MongoDB: localhost:27017
```

#### Без Docker

**Шаг 1: Backend**
```bash
cd backend
npm install
# Убедитесь что MongoDB запущен локально или обновите MONGODB_URI в .env
npm run dev
# Сервер запустится на http://localhost:3001
```

**Шаг 2: Frontend (в новом терминале)**
```bash
cd frontend
npm install
npm start
# Приложение откроется на http://localhost:3000
```

## 🌐 Деплой

### Деплой на Railway + Vercel

#### 1. Деплой Backend на Railway

```bash
npm install -g railway

# Авторизуемся
railway login

# Инициализируем проект
cd backend
railway init

# Добавляем переменные окружения
railway variable set MONGODB_URI "mongodb://..."
railway variable set TELEGRAM_BOT_TOKEN "8570031817:AAGgBlOIDZS9hWGpayZnd1nsCQgnJgLVvqw"
railway variable set CORS_ORIGIN "https://your-frontend-url.vercel.app"

# Деплоим
railway up
```

#### 2. Деплой Frontend на Vercel

```bash
npm install -g vercel

# Авторизуемся
vercel login

# Переходим в папку frontend
cd frontend

# Деплоим
vercel --prod

# Добавляем переменные окружения в Vercel dashboard:
# REACT_APP_WS_URL = wss://your-backend-railway-url
# REACT_APP_API_URL = https://your-backend-railway-url
```

#### 3. Настройка Telegram Bot Web App

1. Откройте BotFather в Telegram (@BotFather)
2. Команда: `/setwebapp`
3. Выберите вашего бота (@shlyapa4_bot)
4. Введите URL вашего frontend приложения

## 📊 API Endpoints

### REST API

**GET /api/leaderboard** - Получить топ-10 игроков
```json
{
  "leaderboard": [
    { "_id": "user123", "totalScore": 1250, "games": 15 },
    ...
  ]
}
```

**GET /api/user/:userId/stats** - Статистика пользователя
```json
{
  "totalGames": 15,
  "totalScore": 1250
}
```

**GET /api/games/:gameType** - История игр по типу
```json
{
  "games": [
    { "gameId": "game_123", "gameType": "quiz", "players": [...], "results": [...] },
    ...
  ]
}
```

### WebSocket Events

**client → server:**
- `init` - Инициализация соединения
- `create_game` - Создать новую игру
- `join_game` - Присоединиться к игре
- `start_game` - Начать игру
- `quiz_answer` - Ответить на вопрос
- `tic_move` - Сделать ход в крестики-нолики
- `rhyme_submit` - Отправить рифму
- `vote_rhyme` - Голосовать за рифму
- `end_game` - Завершить игру

**server → client:**
- `connected` - Соединение установлено
- `game_created` - Игра создана
- `player_joined` - Игрок присоединился
- `game_started` - Игра началась
- `board_updated` - Доска обновлена (крестики-нолики)
- `correct_answer` - Правильный ответ (викторина)
- `next_question` - Следующий вопрос
- `game_ended` - Игра завершена

## 📁 Структура проекта

```
telegram-games-app/
├── backend/
│   ├── index.js              # Главный сервер Express + WebSocket
│   ├── telegram-bot.js       # Telegram Bot интеграция
│   ├── models/
│   │   └── GameSession.js    # MongoDB схема
│   ├── package.json
│   ├── .env
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Главный компонент
│   │   ├── App.css
│   │   ├── store.js          # Zustand store
│   │   ├── index.js
│   │   ├── components/
│   │   │   ├── GameLobby.jsx
│   │   │   ├── GameQuiz.jsx
│   │   │   ├── GameTicTacToe.jsx
│   │   │   ├── GameRhyme.jsx
│   │   │   └── Leaderboard.jsx
│   │   └── styles/
│   │       ├── GameLobby.css
│   │       ├── GameQuiz.css
│   │       ├── GameTicTacToe.css
│   │       ├── GameRhyme.css
│   │       └── Leaderboard.css
│   ├── public/
│   │   └── index.html
│   ├── package.json
│   ├── .env
│   └── Dockerfile
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── deploy.yml        # CI/CD для автодеплоя
└── README.md
```

## 🔐 Безопасность

### Реализовано:
- ✅ Telegram Web App API для авторизации (без логинов)
- ✅ CORS защита
- ✅ WebSocket соединения
- ✅ Environment variables для секретов
- ✅ MongoDB с валидацией схемы
- ✅ Input sanitization

### Рекомендации:
- Используйте HTTPS/WSS в production
- Регулярно обновляйте зависимости
- Мониторьте логи на подозрительную активность
- Rate limiting для API endpoints

## 🛠️ Разработка

### Добавление новой игры

1. Создайте логику игры в `backend/index.js` (функция `createXxxGame`)
2. Добавьте WebSocket обработчик для игровых событий
3. Создайте React компонент в `frontend/src/components/`
4. Добавьте стили в `frontend/src/styles/`
5. Зарегистрируйте в `frontend/src/App.jsx` и `frontend/src/components/GameLobby.jsx`

### Тестирование локально

```bash
# Терминал 1
cd backend && npm run dev

# Терминал 2
cd frontend && npm start

# Открыть http://localhost:3000
```

## 📈 Мониторинг и логирование

### Backend логи
```bash
docker logs telegram-games-backend
```

### MongoDB статистика
```bash
docker exec telegram-games-mongodb mongosh
db.gamesessions.stats()
```

## 🐛 Troubleshooting

**WebSocket не подключается**
- Проверьте что backend запущен на правильном порту
- Убедитесь что REACT_APP_WS_URL правильно установлен
- Проверьте CORS settings в backend/index.js

**MongoDB connection error**
- Проверьте что MongoDB запущен: `docker ps | grep mongodb`
- Проверьте MONGODB_URI в .env
- Для Docker Compose используйте `mongodb:27017` как host

**Telegram Bot не отвечает**
- Проверьте TELEGRAM_BOT_TOKEN в .env
- Убедитесь что бот был зарегистрирован в @BotFather
- Проверьте логи: `npm run dev | grep -i telegram`

## 📝 Лицензия

MIT License - свободное использование в личных и коммерческих проектах

## 👥 Контакты

- Telegram Bot: @shlyapa4_bot
- Issues & Feedback: Создавайте GitHub issues

---

**Готово к использованию! 🚀 Начните играть прямо сейчас!**
