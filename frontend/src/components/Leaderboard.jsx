import React, { useState, useEffect } from 'react';
import { useGameStore } from '../store';
import '../styles/Leaderboard.css';

function Leaderboard() {
  const { setCurrentScreen } = useGameStore();
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:3001'}/api/leaderboard`);
        const data = await response.json();
        setLeaderboard(data);
      } catch (err) {
        console.error('Error fetching leaderboard:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, []);

  const medals = ['🥇', '🥈', '🥉'];

  return (
    <div className="leaderboard-container">
      <div className="leaderboard-header">
        <h2>🏆 Глобальный Лидерборд</h2>
        <p>Топ-10 игроков по общему счету</p>
      </div>

      {loading ? (
        <p className="loading">Загрузка...</p>
      ) : leaderboard.length > 0 ? (
        <div className="leaderboard-list">
          {leaderboard.map((entry, idx) => (
            <div key={idx} className={`leaderboard-item ${idx < 3 ? 'top-3' : ''}`}>
              <div className="rank">
                {idx < 3 ? medals[idx] : `#${idx + 1}`}
              </div>
              <div className="player-info">
                <div className="player-name">User #{entry._id}</div>
                <div className="games-count">{entry.games} игр</div>
              </div>
              <div className="player-score">{entry.totalScore} pts</div>
            </div>
          ))}
        </div>
      ) : (
        <p className="no-data">Ещё нет результатов. Сыграйте первую игру!</p>
      )}

      <button className="btn-back" onClick={() => setCurrentScreen('lobby')}>
        ← Вернуться в лобби
      </button>
    </div>
  );
}

export default Leaderboard;
