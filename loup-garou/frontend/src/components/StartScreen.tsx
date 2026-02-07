import { useState } from 'react';
import './StartScreen.css';

interface StartScreenProps {
  onStartGame: (playerName: string, numPlayers: number, numWolves: number) => void;
  isLoading: boolean;
}

export function StartScreen({ onStartGame, isLoading }: StartScreenProps) {
  const [playerName, setPlayerName] = useState('');
  const [numPlayers, setNumPlayers] = useState(6);
  const [numWolves, setNumWolves] = useState(2);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (playerName.trim()) {
      onStartGame(playerName.trim(), numPlayers, numWolves);
    }
  };

  return (
    <div className="start-screen">
      <div className="start-content">
        <h1 className="game-title">Loup-Garou</h1>
        <p className="game-subtitle">Le jeu de roles mystere</p>

        <form onSubmit={handleSubmit} className="start-form">
          <div className="form-group">
            <label htmlFor="playerName">Votre nom</label>
            <input
              id="playerName"
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              placeholder="Entrez votre nom..."
              disabled={isLoading}
              autoFocus
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="numPlayers">Joueurs</label>
              <select
                id="numPlayers"
                value={numPlayers}
                onChange={(e) => setNumPlayers(Number(e.target.value))}
                disabled={isLoading}
              >
                {[4, 5, 6, 7, 8, 9, 10].map((n) => (
                  <option key={n} value={n}>{n} joueurs</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="numWolves">Loups</label>
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
              <span className="role-name">Loup-Garou</span>
            </div>
            <div className="role-card villager">
              <span className="role-icon">👨‍🌾</span>
              <span className="role-name">Villageois</span>
            </div>
            <div className="role-card seer">
              <span className="role-icon">🔮</span>
              <span className="role-name">Voyante</span>
            </div>
            <div className="role-card witch">
              <span className="role-icon">🧙‍♀️</span>
              <span className="role-name">Sorciere</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
