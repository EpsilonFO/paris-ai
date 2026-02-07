import type { Player, Discussion } from '../types';
import { PlayerAvatar } from './PlayerAvatar';
import './GameBoard.css';

interface GameBoardProps {
  players: Player[];
  discussions: Discussion[];
  phase: 'nuit' | 'jour';
  dayNumber: number;
  selectedPlayer: string | null;
  selectableMode: boolean;
  onPlayerSelect: (playerName: string) => void;
}

export function GameBoard({
  players,
  discussions,
  phase,
  dayNumber,
  selectedPlayer,
  selectableMode,
  onPlayerSelect,
}: GameBoardProps) {
  const isNight = phase === 'nuit';

  const getPlayerMessage = (playerName: string): string | undefined => {
    const discussion = discussions.find((d) => d.player === playerName);
    return discussion?.message;
  };

  return (
    <div className={`game-board ${isNight ? 'night' : 'day'}`}>
      <div className="sky">
        <div className={`celestial-body ${isNight ? 'moon' : 'sun'}`}>
          {isNight ? '🌙' : '☀️'}
        </div>
        <div className="stars">
          {isNight &&
            Array.from({ length: 20 }).map((_, i) => (
              <div
                key={i}
                className="star"
                style={{
                  left: `${Math.random() * 100}%`,
                  top: `${Math.random() * 60}%`,
                  animationDelay: `${Math.random() * 2}s`,
                }}
              />
            ))}
        </div>
      </div>

      <div className="phase-indicator">
        <h2>
          {isNight ? '🌙 Nuit' : '☀️ Jour'} {dayNumber}
        </h2>
      </div>

      <div className="village-scene">
        <div className="players-circle">
          {players.map((player) => (
            <PlayerAvatar
              key={player.name}
              player={player}
              message={getPlayerMessage(player.name)}
              isNight={isNight}
              isSelectable={selectableMode && player.is_alive && !player.is_human}
              isSelected={selectedPlayer === player.name}
              onClick={() => onPlayerSelect(player.name)}
            />
          ))}
        </div>
      </div>

      <div className="ground" />
    </div>
  );
}
