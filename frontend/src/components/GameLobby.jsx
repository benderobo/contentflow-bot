import React, { useState } from 'react';
import { useGameStore } from '../store';
import '../styles/GameLobby.css';

function GameLobby() {
  const { createGame, setCurrentScreen } = useGameStore();
  const [selectedGame, setSelectedGame] = useState(null);

  const games = [
    {
      id: 'quiz',
      name: '📚 Угадайка',
      description: 'Быстрая викторина с вопросами. Первый правильный ответ = 3 балла, второй = 2, третий = 1',
      icon: '📚'
    },
    {
      id: 'tic-tac-toe',
      name: '⭕ Крестики-нолики',
      description: 'Классический поединок на поле 5×5. Побеждающий ход видит вся комната',
      icon: '⭕'
    },
    {
      id: 'rhyme',
      name: '🎵 Рифма в спешке',
      description: 'Пишите рифмы за 30 сек и голосуйте. Лучшая рифма = +5 баллов',
      icon: '🎵'
    }
  ];

  const handleCreateGame = (gameId) => {
    createGame(gameId);
    setSelectedGame(gameId);
  };

  return (
    <div className="lobby">
      <div className="lobby-header">
        <h2>Выберите игру</h2>
        <p>Создайте сессию или присоединитесь к друзьям</p>
      </div>

      <div className="games-grid">
        {games.map((game) => (
          <div key={game.id} className="game-card">
            <div className="game-icon">{game.icon}</div>
            <h3>{game.name}</h3>
            <p>{game.description}</p>
            <button
              className="btn-create"
              onClick={() => handleCreateGame(game.id)}
            >
              Создать игру
            </button>
          </div>
        ))}
      </div>

      <div className="lobby-footer">
        <button className="btn-leaderboard" onClick={() => setCurrentScreen('leaderboard')}>
          🏆 Лидерборд
        </button>
      </div>
    </div>
  );
}

export default GameLobby;
