import React, { useState } from 'react';
import { useGameStore } from '../store';
import '../styles/GameTicTacToe.css';

function GameTicTacToe({ gameId }) {
  const { gameState, userId, players, makeTicMove, endGame, setCurrentScreen } = useGameStore();
  const [gameOver, setGameOver] = useState(false);

  const board = gameState?.board || Array(25).fill(null);
  const currentPlayer = gameState?.currentPlayer;
  const currentSymbol = currentPlayer === 0 ? 'X' : 'O';

  const handleCellClick = (position) => {
    if (board[position] === null && !gameOver) {
      makeTicMove(gameId, position, currentSymbol);
    }
  };

  const checkWinner = () => {
    // Проверка строк
    for (let row = 0; row < 5; row++) {
      for (let col = 0; col < 5; col++) {
        const idx = row * 5 + col;
        if (board[idx] && checkLine(idx, 0, 1)) return board[idx];
      }
    }
    // Проверка столбцов
    for (let col = 0; col < 5; col++) {
      for (let row = 0; row < 5; row++) {
        const idx = row * 5 + col;
        if (board[idx] && checkLine(idx, 5, 1)) return board[idx];
      }
    }
    // Проверка диагоналей
    for (let row = 0; row < 1; row++) {
      for (let col = 0; col < 1; col++) {
        const idx = row * 5 + col;
        if (board[idx] && checkLine(idx, 6, 1)) return board[idx];
        if (board[idx] && checkLine(idx, 4, 1)) return board[idx];
      }
    }
    return null;
  };

  const checkLine = (start, direction, length) => {
    const symbol = board[start];
    for (let i = 1; i < 3; i++) {
      if (board[start + direction * i] !== symbol) return false;
    }
    return true;
  };

  const winner = checkWinner();

  return (
    <div className="tictactoe-container">
      <div className="tictactoe-header">
        <h2>⭕ Крестики-Нолики (5×5)</h2>
        <div className="player-indicator">
          {winner ? (
            <p className="winner">🎉 Победитель: {winner === 'X' ? players?.[0]?.username : players?.[1]?.username}</p>
          ) : (
            <p>Ход: <strong>{currentSymbol}</strong></p>
          )}
        </div>
      </div>

      <div className="tictactoe-board">
        {board.map((cell, idx) => (
          <div
            key={idx}
            className={`cell ${cell ? 'filled' : ''} ${cell === 'X' ? 'x' : ''} ${cell === 'O' ? 'o' : ''}`}
            onClick={() => handleCellClick(idx)}
          >
            {cell}
          </div>
        ))}
      </div>

      <div className="tictactoe-footer">
        <p>Первый получивший 3 подряд выигрывает раунд!</p>
        {winner && (
          <button className="btn-next" onClick={() => endGame(gameId)}>
            → Следующая игра
          </button>
        )}
        <button className="btn-quit" onClick={() => setCurrentScreen('lobby')}>
          ← Выход
        </button>
      </div>
    </div>
  );
}

export default GameTicTacToe;
