require('dotenv').config();
const express = require('express');
const cors = require('cors');
const WebSocket = require('ws');
const http = require('http');
const mongoose = require('mongoose');
const TelegramBot = require('node-telegram-bot-api');
const crypto = require('crypto');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Telegram Bot initialization
const bot = process.env.TELEGRAM_BOT_TOKEN ? new TelegramBot(process.env.TELEGRAM_BOT_TOKEN, { polling: true }) : null;

// Restrict CORS to frontend origin
app.use(cors({
  origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
  credentials: true
}));
app.use(express.json());

// Validate Telegram WebApp initData signature
function validateTelegramData(initData, botToken) {
  if (!initData) return null;
  const data = new URLSearchParams(initData);
  const hash = data.get('hash');
  if (!hash) return null;

  data.delete('hash');
  const dataCheckString = Array.from(data.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');

  const secretKey = crypto
    .createHmac('sha256', 'WebAppData')
    .update(botToken)
    .digest();

  const calculatedHash = crypto
    .createHmac('sha256', secretKey)
    .update(dataCheckString)
    .digest('hex');

  return calculatedHash === hash ? JSON.parse(data.get('user') || '{}') : null;
}

// Подключение к MongoDB
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/telegram-games';
mongoose.connect(MONGODB_URI).catch(err => console.error('MongoDB connection error:', err));

// Схемы БД
const gameSessionSchema = new mongoose.Schema({
  gameId: String,
  gameType: String, // 'quiz', 'tic-tac-toe', 'rhyme'
  players: [{ userId: String, username: String, score: Number, status: String }],
  state: mongoose.Schema.Types.Mixed,
  createdAt: { type: Date, default: Date.now },
  completedAt: Date,
  results: [{ userId: String, score: Number, place: Number }]
});

const GameSession = mongoose.model('GameSession', gameSessionSchema);

// Store active WebSocket connections
const clients = new Map();
const gameSessions = new Map();

// Утилиты для игр
const generateGameId = () => 'game_' + crypto.randomBytes(16).toString('hex');
const generateClientId = () => crypto.randomBytes(16).toString('hex');

// Quiz Game Logic
const createQuizGame = () => ({
  currentQuestion: 0,
  questions: [
    { text: 'Столица России?', answers: ['Москва'], options: ['Москва', 'СПб', 'Казань', 'Новосибирск'] },
    { text: 'Сколько планет в Солнечной системе?', answers: ['8', 'восемь'], options: ['7', '8', '9', '10'] },
    { text: 'Автор "Войны и мира"?', answers: ['Толстой', 'Лев Толстой'], options: ['Толстой', 'Достоевский', 'Пушкин', 'Лермонтов'] }
  ],
  scores: {},
  answered: {}
});

// Tic Tac Toe Game Logic
const createTicTacToeGame = () => ({
  board: Array(25).fill(null),
  currentPlayer: 0,
  players: [],
  winner: null,
  moves: []
});

// Rhyme Game Logic
const createRhymeGame = () => ({
  word: ['кот', 'дом', 'сон', 'лес', 'ночь', 'день'][Math.floor(Math.random() * 6)],
  rhymes: {},
  votes: {},
  timeLeft: 30
});

// WebSocket connections
wss.on('connection', (ws, req) => {
  const clientId = generateClientId();
  clients.set(clientId, { ws, userId: null, gameId: null, authenticated: false });

  ws.on('message', async (message) => {
    try {
      const data = JSON.parse(message);
      const client = clients.get(clientId);

      if (!client) return;

      switch (data.type) {
        case 'init':
          // Validate Telegram data signature
          const user = validateTelegramData(data.initData, process.env.TELEGRAM_BOT_TOKEN);
          if (!user || !user.id) {
            ws.send(JSON.stringify({ type: 'error', message: 'Invalid authentication' }));
            ws.close();
            return;
          }
          client.userId = String(user.id);
          client.username = user.username || user.first_name || 'Unknown';
          client.authenticated = true;
          ws.send(JSON.stringify({ type: 'connected', clientId }));
          break;

        case 'create_game':
          if (!client.authenticated) return;
          if (!data.gameType || !['quiz', 'tic-tac-toe', 'rhyme'].includes(data.gameType)) return;

          const gameId = generateGameId();
          const newSession = {
            gameId,
            gameType: data.gameType,
            players: [{ userId: client.userId, username: client.username, score: 0, status: 'joined' }],
            state: {
              quiz: createQuizGame,
              'tic-tac-toe': createTicTacToeGame,
              rhyme: createRhymeGame
            }[data.gameType]?.() || {},
            createdAt: new Date()
          };
          gameSessions.set(gameId, newSession);
          client.gameId = gameId;

          ws.send(JSON.stringify({ type: 'game_created', gameId, game: newSession }));
          await new GameSession(newSession).save();
          break;

        case 'join_game':
          if (!client.authenticated) return;
          if (typeof data.gameId !== 'string' || data.gameId.length < 10) return;

          const session = gameSessions.get(data.gameId);
          if (session && session.players.length < 8 && !session.players.some(p => p.userId === client.userId)) {
            session.players.push({ userId: client.userId, username: client.username, score: 0, status: 'joined' });
            client.gameId = data.gameId;
            broadcastToGame(data.gameId, { type: 'player_joined', players: session.players });
          }
          break;

        case 'start_game':
          if (!client.authenticated) return;
          const game = gameSessions.get(data.gameId);
          if (game && game.players.some(p => p.userId === client.userId)) {
            game.state.started = true;
            broadcastToGame(data.gameId, { type: 'game_started', state: game.state });
          }
          break;

        case 'quiz_answer':
          if (!client.authenticated) return;
          const quizGame = gameSessions.get(data.gameId);
          if (!quizGame || quizGame.gameType !== 'quiz' || !quizGame.players.some(p => p.userId === client.userId)) return;
          if (typeof data.answer !== 'string' || data.answer.length > 100) return;
          if (quizGame.state.answered?.[client.userId]) return;

          const q = quizGame.state.questions[quizGame.state.currentQuestion];
          const isCorrect = q.answers.includes(data.answer.toLowerCase().trim());

          if (isCorrect) {
            const pointsMap = { 1: 3, 2: 2, 3: 1 };
            const score = pointsMap[Object.keys(quizGame.state.answered).length + 1] || 0;
            quizGame.state.scores[client.userId] = (quizGame.state.scores[client.userId] || 0) + score;
            broadcastToGame(data.gameId, { type: 'correct_answer', userId: client.userId, score });
          }

          quizGame.state.answered[client.userId] = true;
          if (Object.keys(quizGame.state.answered).length === quizGame.players?.length) {
            quizGame.state.currentQuestion++;
            if (quizGame.state.currentQuestion < quizGame.state.questions.length) {
              broadcastToGame(data.gameId, { type: 'next_question', question: quizGame.state.questions[quizGame.state.currentQuestion] });
            } else {
              broadcastToGame(data.gameId, { type: 'quiz_complete' });
            }
          }
          break;

        case 'tic_move':
          if (!client.authenticated) return;
          const tictacGame = gameSessions.get(data.gameId);
          if (!tictacGame || tictacGame.gameType !== 'tic-tac-toe') return;
          if (!tictacGame.players.some(p => p.userId === client.userId)) return;

          // Validate position and symbol
          if (!Number.isInteger(data.position) || data.position < 0 || data.position > 24) return;
          if ((data.symbol !== 'X' && data.symbol !== 'O') || tictacGame.state.board[data.position] !== null) return;

          // Verify it's the correct player's turn
          const currentPlayerId = tictacGame.players[tictacGame.state.currentPlayer]?.userId;
          if (currentPlayerId !== client.userId) return;

          tictacGame.state.board[data.position] = data.symbol;
          tictacGame.state.moves.push({ position: data.position, symbol: data.symbol, userId: client.userId });
          tictacGame.state.currentPlayer = 1 - tictacGame.state.currentPlayer;
          broadcastToGame(data.gameId, { type: 'board_updated', board: tictacGame.state.board, currentPlayer: tictacGame.state.currentPlayer });
          break;

        case 'rhyme_submit':
          if (!client.authenticated) return;
          const rhymeGame = gameSessions.get(data.gameId);
          if (!rhymeGame || rhymeGame.gameType !== 'rhyme' || !rhymeGame.players.some(p => p.userId === client.userId)) return;
          if (typeof data.rhyme !== 'string' || data.rhyme.length < 1 || data.rhyme.length > 100) return;
          if (rhymeGame.state.rhymes?.[client.userId]) return;

          rhymeGame.state.rhymes[client.userId] = data.rhyme.trim();
          broadcastToGame(data.gameId, { type: 'rhyme_submitted', count: Object.keys(rhymeGame.state.rhymes).length });
          break;

        case 'vote_rhyme':
          if (!client.authenticated) return;
          const voteGame = gameSessions.get(data.gameId);
          if (!voteGame || voteGame.gameType !== 'rhyme' || !voteGame.players.some(p => p.userId === client.userId)) return;
          if (typeof data.rhymeUserId !== 'string' || !voteGame.players.some(p => p.userId === data.rhymeUserId)) return;
          if (data.rhymeUserId === client.userId) return; // Can't vote for yourself

          if (!voteGame.state.votes[data.rhymeUserId]) voteGame.state.votes[data.rhymeUserId] = 0;
          voteGame.state.votes[data.rhymeUserId]++;
          broadcastToGame(data.gameId, { type: 'rhyme_voted', userId: data.rhymeUserId, votes: voteGame.state.votes[data.rhymeUserId] });
          break;

        case 'end_game':
          if (!client.authenticated) return;
          const endGame = gameSessions.get(data.gameId);
          if (!endGame || !endGame.players.some(p => p.userId === client.userId)) return;

          endGame.completedAt = new Date();
          endGame.results = endGame.players.map((p, i) => ({ userId: p.userId, score: endGame.state.scores?.[p.userId] || 0, place: i + 1 })).sort((a, b) => b.score - a.score);
          broadcastToGame(data.gameId, { type: 'game_ended', results: endGame.results });
          await new GameSession(endGame).save();
          gameSessions.delete(data.gameId);
          break;
      }
    } catch (err) {
      console.error('WebSocket error:', err);
    }
  });

  ws.on('close', () => {
    clients.delete(clientId);
  });
});

// Утилита для отправки сообщений всем игрокам в сессии
function broadcastToGame(gameId, message) {
  clients.forEach((client) => {
    if (client.gameId === gameId && client.ws.readyState === WebSocket.OPEN) {
      client.ws.send(JSON.stringify(message));
    }
  });
}

// REST API endpoints
app.get('/api/leaderboard', async (req, res) => {
  try {
    const leaderboard = await GameSession.aggregate([
      { $unwind: '$results' },
      { $group: { _id: '$results.userId', totalScore: { $sum: '$results.score' }, games: { $sum: 1 } } },
      { $sort: { totalScore: -1 } },
      { $limit: 10 }
    ]);
    res.json(leaderboard);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/user/:userId/stats', async (req, res) => {
  try {
    const stats = await GameSession.aggregate([
      { $match: { 'results.userId': req.params.userId } },
      { $group: { _id: null, totalGames: { $sum: 1 }, totalScore: { $sum: { $cond: [{ $eq: ['$results.userId', req.params.userId] }, { $arrayElemAt: ['$results.score', 0] }, 0] } } } }
    ]);
    res.json(stats[0] || { totalGames: 0, totalScore: 0 });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/games/:gameType', async (req, res) => {
  try {
    const games = await GameSession.find({ gameType: req.params.gameType }).limit(20);
    res.json(games);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Telegram Bot handlers
if (bot) {
  bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    const username = msg.from.username || msg.from.first_name;

    const keyboard = {
      inline_keyboard: [
        [
          {
            text: '🎮 Играть сейчас',
            web_app: { url: process.env.WEB_APP_URL || 'http://localhost:3000' }
          }
        ],
        [
          {
            text: '🏆 Лидерборд',
            callback_data: 'view_leaderboard'
          }
        ],
        [
          {
            text: '📊 Мой профиль',
            callback_data: `profile_${userId}`
          }
        ]
      ]
    };

    bot.sendMessage(chatId, `👋 Привет, ${username}!\n\n🎮 Добро пожаловать в Telegram Games!\n\nЗдесь ты можешь:\n• Играть в 3 разных игры\n• Соревноваться с друзьями\n• Подняться на вершину лидерборда\n\nНажми кнопку ниже, чтобы начать! 🚀`, {
      reply_markup: keyboard
    });
  });

  bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const userId = query.from.id;
    const data = query.data;

    if (data === 'view_leaderboard') {
      try {
        const leaderboard = await GameSession.aggregate([
          { $unwind: '$results' },
          { $group: { _id: '$results.userId', totalScore: { $sum: '$results.score' }, games: { $sum: 1 } } },
          { $sort: { totalScore: -1 } },
          { $limit: 10 }
        ]);

        let message = '🏆 Глобальный Лидерборд\n\n';
        const medals = ['🥇', '🥈', '🥉'];

        leaderboard.forEach((entry, idx) => {
          const medal = idx < 3 ? medals[idx] : `#${idx + 1}`;
          message += `${medal} User ${entry._id}: ${entry.totalScore} баллов (${entry.games} игр)\n`;
        });

        bot.answerCallbackQuery(query.id);
        bot.sendMessage(chatId, message);
      } catch (err) {
        console.error('Error fetching leaderboard:', err);
        bot.answerCallbackQuery(query.id, { text: 'Ошибка при загрузке лидерборда' });
      }
    }

    if (data.startsWith('profile_')) {
      const profileUserId = data.replace('profile_', '');
      try {
        const stats = await GameSession.aggregate([
          { $match: { 'results.userId': profileUserId } },
          { $group: { _id: null, totalGames: { $sum: 1 }, totalScore: { $sum: 1 } } }
        ]);

        const userStats = stats[0] || { totalGames: 0, totalScore: 0 };
        const message = `📊 Ваш профиль\n\nВсего игр: ${userStats.totalGames}\n\nПродолжайте играть! 🚀`;

        bot.answerCallbackQuery(query.id);
        bot.sendMessage(chatId, message);
      } catch (err) {
        console.error('Error fetching user stats:', err);
        bot.answerCallbackQuery(query.id, { text: 'Ошибка при загрузке профиля' });
      }
    }
  });

  console.log('✅ Telegram Bot initialized successfully');
}

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`WebSocket available at ws://localhost:${PORT}`);
});
