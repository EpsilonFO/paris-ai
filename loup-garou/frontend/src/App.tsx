import { useState, useCallback } from 'react';
import type { CreateGameResponse } from './types';
import { setAnthropicKey, createGame } from './api';
import GameInterface from './components/GameInterface';
import { Loader2, Moon } from 'lucide-react';
import { cn } from './lib/utils';

function App() {
  const [gameId, setGameId] = useState<string | null>(null);
  const [yourRole, setYourRole] = useState('');
  const [fellowWolves, setFellowWolves] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Start screen state ─────────────────────────────
  const [apiKey, setApiKey] = useState('');
  const [playerName, setPlayerName] = useState('');
  const [numPlayers, setNumPlayers] = useState(6);
  const [numWolves, setNumWolves] = useState(2);

  const handleStartGame = useCallback(async () => {
    if (!apiKey.trim() || !playerName.trim()) {
      setError('Veuillez remplir tous les champs');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await setAnthropicKey(apiKey);
      const response: CreateGameResponse = await createGame(playerName, numPlayers, numWolves);
      setGameId(response.game_id);
      setYourRole(response.your_role);
      setFellowWolves(response.fellow_wolves || []);
    } catch (err) {
      console.error('Failed to start game:', err);
      setError(err instanceof Error ? err.message : 'Impossible de créer la partie');
    } finally {
      setIsLoading(false);
    }
  }, [apiKey, playerName, numPlayers, numWolves]);

  const handleRestart = useCallback(() => {
    setGameId(null);
    setYourRole('');
    setFellowWolves([]);
  }, []);

  // ── Game is running → render GameInterface ─────────
  if (gameId) {
    return (
      <GameInterface
        gameId={gameId}
        initialRole={yourRole}
        fellowWolves={fellowWolves}
        onRestart={handleRestart}
      />
    );
  }

  // ── Start screen ───────────────────────────────────
  return (
    <div className="min-h-screen wood-panel flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Title */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-amber-800 to-amber-950 flex items-center justify-center border-2 border-gold-bright/50">
            <Moon className="w-10 h-10 text-gold-bright" />
          </div>
          <h1 className="font-display text-4xl text-parchment-light tracking-wide">
            Loup-Garou
          </h1>
          <p className="text-amber-100/40 font-serif italic mt-2">
            Le village s'endort... les loups se réveillent
          </p>
        </div>

        {/* Form */}
        <div className="bg-wood/80 rounded-xl border border-amber-900/30 p-6 space-y-5">
          {/* API Key */}
          <div>
            <label className="block text-xs text-amber-400/70 font-serif mb-1.5">
              Clé API Anthropic
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-ant-..."
              className="w-full bg-wood-dark border border-amber-900/30 rounded-lg px-4 py-2.5 text-sm text-amber-100 placeholder:text-amber-700/40 focus:outline-none focus:ring-1 focus:ring-gold-bright/50 transition-colors"
            />
          </div>

          {/* Player name */}
          <div>
            <label className="block text-xs text-amber-400/70 font-serif mb-1.5">
              Votre nom
            </label>
            <input
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              placeholder="Entrez votre nom..."
              className="w-full bg-wood-dark border border-amber-900/30 rounded-lg px-4 py-2.5 text-sm text-amber-100 placeholder:text-amber-700/40 focus:outline-none focus:ring-1 focus:ring-gold-bright/50 transition-colors"
            />
          </div>

          {/* Config row */}
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-xs text-amber-400/70 font-serif mb-1.5">
                Joueurs
              </label>
              <select
                value={numPlayers}
                onChange={(e) => setNumPlayers(Number(e.target.value))}
                className="w-full bg-wood-dark border border-amber-900/30 rounded-lg px-4 py-2.5 text-sm text-amber-100 focus:outline-none focus:ring-1 focus:ring-gold-bright/50"
              >
                {[4, 5, 6, 7, 8, 9, 10].map(n => (
                  <option key={n} value={n}>{n} joueurs</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs text-amber-400/70 font-serif mb-1.5">
                Loups
              </label>
              <select
                value={numWolves}
                onChange={(e) => setNumWolves(Number(e.target.value))}
                className="w-full bg-wood-dark border border-amber-900/30 rounded-lg px-4 py-2.5 text-sm text-amber-100 focus:outline-none focus:ring-1 focus:ring-gold-bright/50"
              >
                {[1, 2, 3].map(n => (
                  <option key={n} value={n}>{n} loup{n > 1 ? 's' : ''}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Error */}
          {error && (
            <p className="text-red-400 text-sm text-center font-serif">{error}</p>
          )}

          {/* Start button */}
          <button
            onClick={handleStartGame}
            disabled={isLoading}
            className={cn(
              "w-full py-3 rounded-lg font-bold text-sm tracking-wide transition-all",
              isLoading
                ? "bg-amber-900/40 text-amber-400/50 cursor-wait"
                : "bg-gradient-to-r from-gold-bright to-gold-dark text-ink-brown hover:shadow-lg hover:shadow-gold-bright/20"
            )}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Création de la partie...
              </span>
            ) : (
              "Commencer la Partie"
            )}
          </button>
        </div>

        {/* Roles info */}
        <div className="mt-6 grid grid-cols-2 gap-3">
          {[
            { name: 'Loup-Garou', desc: 'Dévore un villageois chaque nuit', color: 'text-red-400' },
            { name: 'Villageois', desc: 'Trouve et élimine les loups', color: 'text-amber-400' },
            { name: 'Voyante', desc: "Découvre le rôle d'un joueur", color: 'text-blue-400' },
            { name: 'Sorcière', desc: 'Possède 2 potions magiques', color: 'text-purple-400' },
          ].map(role => (
            <div key={role.name} className="bg-black/20 rounded-lg border border-amber-900/20 p-3">
              <span className={cn("text-xs font-bold", role.color)}>{role.name}</span>
              <p className="text-[10px] text-amber-100/40 mt-0.5">{role.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
