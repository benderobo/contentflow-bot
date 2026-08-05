import React, { useState, useEffect } from 'react';
import { useGameStore } from '../store';
import '../styles/GameQuiz.css';

function GameQuiz({ gameId }) {
  const { gameState, players, answerQuiz, endGame, setCurrentScreen } = useGameStore();
  const [userAnswer, setUserAnswer] = useState('');
  const [timeLeft, setTimeLeft] = useState(10);
  const [answered, setAnswered] = useState(false);

  useEffect(() => {
    if (timeLeft > 0 && !answered) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [timeLeft, answered]);

  useEffect(() => {
    if (gameState?.currentQuestion >= gameState?.questions?.length) {
      endGame(gameId);
    }
  }, [gameState?.currentQuestion]);

  const handleAnswer = () => {
    answerQuiz(gameId, userAnswer);
    setAnswered(true);
    setUserAnswer('');
  };

  const currentQuestion = gameState?.questions?.[gameState?.currentQuestion];

  return (
    <div className="quiz-container">
      <div className="quiz-header">
        <h2>📚 Викторина</h2>
        <div className="timer">{timeLeft}s</div>
      </div>

      {currentQuestion && (
        <div className="quiz-content">
          <h3>{currentQuestion.text}</h3>
          <div className="options">
            {currentQuestion.options.map((option, idx) => (
              <button
                key={idx}
                className={`option-btn ${userAnswer === option ? 'selected' : ''}`}
                onClick={() => setUserAnswer(option)}
                disabled={answered}
              >
                {option}
              </button>
            ))}
          </div>

          {!answered ? (
            <button className="btn-submit" onClick={handleAnswer}>
              Ответить
            </button>
          ) : (
            <p className="waiting">Ожидание других игроков...</p>
          )}
        </div>
      )}

      <div className="leaderboard-mini">
        <h4>Текущий счёт</h4>
        <div className="scores-list">
          {players?.map((player, idx) => (
            <div key={idx} className="score-item">
              <span>{player.username}</span>
              <span className="score">{gameState?.scores?.[player.userId] || 0}</span>
            </div>
          ))}
        </div>
      </div>

      <button className="btn-quit" onClick={() => setCurrentScreen('lobby')}>
        ← Выход
      </button>
    </div>
  );
}

export default GameQuiz;
