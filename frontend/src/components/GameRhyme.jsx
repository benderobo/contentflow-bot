import React, { useState, useEffect } from 'react';
import { useGameStore } from '../store';
import '../styles/GameRhyme.css';

function GameRhyme({ gameId }) {
  const { gameState, userId, players, submitRhyme, voteRhyme, endGame, setCurrentScreen } = useGameStore();
  const [userRhyme, setUserRhyme] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [votingPhase, setVotingPhase] = useState(false);
  const [timeLeft, setTimeLeft] = useState(30);

  useEffect(() => {
    if (timeLeft > 0 && !submitted) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
      return () => clearTimeout(timer);
    } else if (timeLeft === 0 && !votingPhase) {
      setVotingPhase(true);
    }
  }, [timeLeft, submitted, votingPhase]);

  const handleSubmitRhyme = () => {
    submitRhyme(gameId, userRhyme);
    setSubmitted(true);
  };

  const handleVote = (userId) => {
    voteRhyme(gameId, userId);
  };

  const word = gameState?.word;
  const rhymes = gameState?.rhymes || {};
  const votes = gameState?.votes || {};

  return (
    <div className="rhyme-container">
      <div className="rhyme-header">
        <h2>🎵 Рифма в спешке</h2>
        <div className="word-display">
          <p>Найдите рифму к слову:</p>
          <h3>{word}</h3>
        </div>
        <div className="timer">{timeLeft}s</div>
      </div>

      {!votingPhase ? (
        <div className="rhyme-input">
          <input
            type="text"
            placeholder="Введите вашу рифму..."
            value={userRhyme}
            onChange={(e) => setUserRhyme(e.target.value)}
            disabled={submitted}
          />
          {!submitted ? (
            <button className="btn-submit" onClick={handleSubmitRhyme}>
              Отправить рифму
            </button>
          ) : (
            <p className="waiting">Ожидание других игроков...</p>
          )}
        </div>
      ) : (
        <div className="voting-phase">
          <h3>🗳️ Голосуйте за лучшую рифму!</h3>
          <div className="rhymes-list">
            {Object.entries(rhymes).map(([userId, rhyme]) => (
              <div key={userId} className="rhyme-item">
                <div className="rhyme-text">{rhyme}</div>
                <div className="rhyme-votes">{votes[userId] || 0} 👍</div>
                <button
                  className="btn-vote"
                  onClick={() => handleVote(userId)}
                >
                  👍 Голос
                </button>
              </div>
            ))}
          </div>
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

export default GameRhyme;
