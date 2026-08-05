const mongoose = require('mongoose');

const gameSessionSchema = new mongoose.Schema({
  gameId: String,
  gameType: String,
  players: [{
    userId: String,
    username: String,
    score: Number,
    status: String
  }],
  state: mongoose.Schema.Types.Mixed,
  createdAt: { type: Date, default: Date.now },
  completedAt: Date,
  results: [{
    userId: String,
    score: Number,
    place: Number
  }]
});

module.exports = mongoose.model('GameSession', gameSessionSchema);
