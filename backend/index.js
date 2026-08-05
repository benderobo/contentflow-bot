require('dotenv').config();
const express = require('express');
const cors = require('cors');
const WebSocket = require('ws');
const http = require('http');
const mongoose = require('mongoose');
const TelegramBot = require('node-telegram-bot-api');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Telegram Bot initialization
const bot = process.env.TELEGRAM_BOT_TOKEN ? new TelegramBot(process.env.TELEGRAM_BOT_TOKEN, { polling: true }) : null;

app.use(cors());
app.use(express.json());

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
const generateGameId = () => 'game_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

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
wss.on('connection', (ws) => {
  const clientId = generateGameId();
  clients.set(clientId, { ws, userId: null, gameId: null });

  ws.on('message', async (message) => {
    try {
      const data = JSON.parse(message);
      const client = clients.get(clientId);

      switch (data.type) {
        case 'init':
          client.userId = data.userId;
          client.username = data.username;
          ws.send(JSON.stringify({ type: 'connected', clientId }));
          break;

        case 'create_game':
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
          const session = gameSessions.get(data.gameId);
          if (session && session.players.length < 8) {
            session.players.push({ userId: client.userId, username: client.username, score: 0, status: 'joined' });
            client.gameId = data.gameId;
            broadcastToGame(data.gameId, { type: 'player_joined', players: session.players });
          }
          break;

        case 'start_game':
          const game = gameSessions.get(data.gameId);
          if (game) {
            game.state.started = true;
            broadcastToGame(data.gameId, { type: 'game_started', state: game.state });
          }
          break;

        case 'quiz_answer':
          const quizGame = gameSessions.get(data.gameId);
          if (quizGame && quizGame.gameType === 'quiz') {
            const q = quizGame.state.questions[quizGame.state.currentQuestion];
            const isCorrect = q.answers.includes(data.answer.toLowerCase());

            if (isCorrect) {
              const pointsMap = { 1: 3, 2: 2, 3: 1 };
              const score = pointsMap[Object.keys(quizGame.state.answered).length + 1] || 0;
              quizGame.state.scores[client.userId] = (quizGame.state.scores[client.userId] || 0) + score;
              broadcastToGame(data.gameId, { type: 'correct_answer', userId: client.userId, score });
            }

            quizGame.state.answered[client.userId] = true;
            if (Object.keys(quizGame.state.answered).length === quizGame.state.players?.length) {
              quizGame.state.currentQuestion++;
              broadcastToGame(data.gameId, { type: 'next_question', question: quizGame.state.questions[quizGame.state.currentQuestion] });
            }
          }
          break;

        case 'tic_move':
          const tictacGame = gameSessions.get(data.gameId);
          if (tictacGame && tictacGame.gameType === 'tic-tac-toe') {
            tictacGame.state.board[data.position] = data.symbol;
            tictacGame.state.moves.push({ position: data.position, symbol: data.symbol });
            tictacGame.state.currentPlayer = 1 - tictacGame.state.currentPlayer;
            broadcastToGame(data.gameId, { type: 'board_updated', board: tictacGame.state.board, currentPlayer: tictacGame.state.currentPlayer });
          }
          break;

        case 'rhyme_submit':
          const rhymeGame = gameSessions.get(data.gameId);
          if (rhymeGame && rhymeGame.gameType === 'rhyme') {
            rhymeGame.state.rhymes[client.userId] = data.rhyme;
            broadcastToGame(data.gameId, { type: 'rhyme_submitted', count: Object.keys(rhymeGame.state.rhymes).length });
          }
          break;

        case 'vote_rhyme':
          const voteGame = gameSessions.get(data.gameId);
          if (voteGame && voteGame.gameType === 'rhyme') {
            if (!voteGame.state.votes[data.rhymeUserId]) voteGame.state.votes[data.rhymeUserId] = 0;
            voteGame.state.votes[data.rhymeUserId]++;
            broadcastToGame(data.gameId, { type: 'rhyme_voted', userId: data.rhymeUserId, votes: voteGame.state.votes[data.rhymeUserId] });
          }
          break;

        case 'end_game':
          const endGame = gameSessions.get(data.gameId);
          if (endGame) {
            endGame.completedAt = new Date();
            endGame.results = endGame.players.map((p, i) => ({ userId: p.userId, score: endGame.state.scores?.[p.userId] || 0, place: i + 1 })).sort((a, b) => b.score - a.score);
            broadcastToGame(data.gameId, { type: 'game_ended', results: endGame.results });
            await GameSession.findByIdAndUpdate(endGame._id, endGame);
          }
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
