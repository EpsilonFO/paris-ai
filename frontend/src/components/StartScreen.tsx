import { useState } from 'react';
import { setAnthropicKey } from '../api';
import './StartScreen.css';

interface StartScreenProps {
  onStartGame: (playerName: string, numPlayers: number, numWolves: number) => void;
  isLoading: boolean;
}

export function StartScreen({ onStartGame, isLoading }: StartScreenProps) {
  const [playerName, setPlayerName] = useState('');
  const [numPlayers, setNumPlayers] = useState(6);
  const [numWolves, setNumWolves] = useState(2);
  const [apiKey, setApiKey] = useState('');
  const [apiKeySet, setApiKeySet] = useState(false);
  const [apiKeyError, setApiKeyError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (playerName.trim()) {
      onStartGame(playerName.trim(), numPlayers, numWolves);
    }
  };

  return (
    <div className="start-screen">
      <div className="start-content">
        <h1 className="game-title">wAIr-wolves</h1>

        <form onSubmit={handleSubmit} className="start-form">
          {/* Configuration API Anthropic */}

          <div className="form-group">
            <label htmlFor="playerName">Your name</label>
            <input
              id="playerName"
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              placeholder="Enter your name..."
              disabled={isLoading}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="numPlayers">Players</label>
              <select
                id="numPlayers"
                value={numPlayers}
                onChange={(e) => setNumPlayers(Number(e.target.value))}
                disabled={isLoading}
              >
                {[4, 5, 6, 7, 8, 9, 10].map((n) => (
                  <option key={n} value={n}>{n} players</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="numWolves">Wolves</label>
              <select
                id="numWolves"
                value={numWolves}
                onChange={(e) => setNumWolves(Number(e.target.value))}
                disabled={isLoading}
              >
                {[1, 2, 3].map((n) => (
                  <option key={n} value={n}>{n} loup{n > 1 ? 's' : ''}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            type="submit"
            className="start-button"
            disabled={!playerName.trim() || isLoading}
          >
            {isLoading ? 'Creation...' : 'Commencer la partie'}
          </button>
        </form>

        <div className="roles-info">
          <h3>Les roles</h3>
          <div className="roles-grid">
            <div className="role-card wolf">
              <span className="role-icon">🐺</span>
              <span className="role-name">wAIr-wolves</span>
            </div>
            <div className="role-card villager">
              <span className="role-icon">👨‍🌾</span>
              <span className="role-name">Villager</span>
            </div>
            <div className="role-card seer">
              <span className="role-icon">🔮</span>
              <span className="role-name">Seer</span>
            </div>
            <div className="role-card witch">
              <span className="role-icon">🧙‍♀️</span>
              <span className="role-name">Witch</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
