import React, { useEffect, useState } from 'react';
import { useGameStore } from './store';
import GameLobby from './components/GameLobby';
import GameQuiz from './components/GameQuiz';
import GameTicTacToe from './components/GameTicTacToe';
import GameRhyme from './components/GameRhyme';
import Leaderboard from './components/Leaderboard';
import './App.css';

function App() {
  const { currentScreen, gameType, gameId, ws, initWebSocket } = useGameStore();
  const [tgUser, setTgUser] = useState(null);

  useEffect(() => {
    // Инициализация Telegram Web App
    if (window.Telegram?.WebApp) {
      const webApp = window.Telegram.WebApp;
      webApp.ready();
      const user = webApp.initDataUnsafe.user;
      setTgUser(user);

      // Инициализация WebSocket
      initWebSocket(user?.id || 'anonymous', user?.username || 'Unknown');
    }
  }, [initWebSocket]);

  useEffect(() => {
    document.body.style.backgroundColor = '#1a1a2e';
    document.body.style.color = '#fff';
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-brand">
          <h1>🎮 SHISHKA_VPN Games</h1>
          <p className="brand-tagline">Multiplayer Fun & Speed</p>
        </div>
        {tgUser && <p className="user-info">@{tgUser.username || tgUser.id}</p>}
      </header>

      <main className="app-main">
        {currentScreen === 'lobby' && <GameLobby />}
        {currentScreen === 'quiz' && <GameQuiz gameId={gameId} />}
        {currentScreen === 'tic-tac-toe' && <GameTicTacToe gameId={gameId} />}
        {currentScreen === 'rhyme' && <GameRhyme gameId={gameId} />}
        {currentScreen === 'leaderboard' && <Leaderboard />}
      </main>

      <footer className="app-footer">
        <p>Real-time multiplayer games 🚀</p>
      </footer>
    </div>
  );
}

export default App;
