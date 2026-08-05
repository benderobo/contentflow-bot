import { create } from 'zustand';

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:3001';

export const useGameStore = create((set, get) => ({
  ws: null,
  clientId: null,
  userId: null,
  username: null,
  currentScreen: 'lobby',
  gameType: null,
  gameId: null,
  players: [],
  gameState: null,
  leaderboard: [],
  userStats: null,

  initWebSocket: (userId, username) => {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'init', userId, username }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const state = get();

      switch (data.type) {
        case 'connected':
          set({ clientId: data.clientId });
          break;

        case 'game_created':
          set({ gameId: data.gameId, gameState: data.game.state, players: data.game.players });
          break;

        case 'player_joined':
          set({ players: data.players });
          break;

        case 'game_started':
          set({ gameState: data.state, currentScreen: state.gameType });
          break;

        case 'board_updated':
          set({ gameState: { ...state.gameState, board: data.board, currentPlayer: data.currentPlayer } });
          break;

        case 'correct_answer':
          set({
            gameState: {
              ...state.gameState,
              scores: { ...state.gameState.scores, [data.userId]: data.score }
            }
          });
          break;

        case 'next_question':
          set({
            gameState: {
              ...state.gameState,
              currentQuestion: state.gameState.currentQuestion + 1,
              answered: {}
            }
          });
          break;

        case 'game_ended':
          set({ currentScreen: 'leaderboard', gameState: { results: data.results } });
          break;

        default:
          break;
      }
    };

    set({ ws, userId, username });
  },

  createGame: (gameType) => {
    const ws = get().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'create_game', gameType }));
      set({ gameType, currentScreen: 'lobby' });
    }
  },

  joinGame: (gameId) => {
    const ws = get().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'join_game', gameId }));
    }
  },

  startGame: (gameId) => {
    const ws = get().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'start_game', gameId }));
    }
  },

  answerQuiz: (gameId, answer) => {
    const ws = get().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'quiz_answer', gameId, answer }));
    }
  },

  makeTicMove: (gameId, position, symbol) => {
    const ws = get().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'tic_move', gameId, position, symbol }));
    }
  },

  submitRhyme: (gameId, rhyme) => {
    const ws = get().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'rhyme_submit', gameId, rhyme }));
    }
  },

  voteRhyme: (gameId, rhymeUserId) => {
    const ws = get().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'vote_rhyme', gameId, rhymeUserId }));
    }
  },

  endGame: (gameId) => {
    const ws = get().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'end_game', gameId }));
    }
  },

  setCurrentScreen: (screen) => set({ currentScreen: screen }),
}));
