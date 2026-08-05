const TelegramBot = require('node-telegram-bot-api');
const GameSession = require('./models/GameSession');

const token = process.env.TELEGRAM_BOT_TOKEN;
const bot = new TelegramBot(token, { polling: true });
const WEB_APP_URL = process.env.WEB_APP_URL || 'https://telegram-games.vercel.app';

bot.onText(/\/start/, (msg) => {
  const chatId = msg.chat.id;
  const userId = msg.from.id;
  const username = msg.from.username || msg.from.first_name;

  const keyboard = {
    inline_keyboard: [
      [
        {
          text: '🎮 Играть сейчас',
          web_app: { url: WEB_APP_URL }
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
        { $group: { _id: null, totalGames: { $sum: 1 }, totalScore: { $sum: { $arrayElemAt: ['$results.score', 0] } } } }
      ]);

      const userStats = stats[0] || { totalGames: 0, totalScore: 0 };
      const message = `📊 Ваш профиль\n\nВсего игр: ${userStats.totalGames}\nОбщий счет: ${userStats.totalScore} баллов\n\nПродолжайте играть! 🚀`;

      bot.answerCallbackQuery(query.id);
      bot.sendMessage(chatId, message);
    } catch (err) {
      console.error('Error fetching user stats:', err);
      bot.answerCallbackQuery(query.id, { text: 'Ошибка при загрузке профиля' });
    }
  }
});

bot.on('message', (msg) => {
  if (msg.text && !msg.text.startsWith('/')) {
    bot.sendMessage(msg.chat.id, 'Используй команду /start или нажми кнопку "Играть сейчас" чтобы начать! 🎮');
  }
});

module.exports = bot;
