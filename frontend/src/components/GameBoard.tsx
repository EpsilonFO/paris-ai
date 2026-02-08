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
  phase,
  dayNumber,
  selectedPlayer,
  selectableMode,
  onPlayerSelect,
}: GameBoardProps) {
  const isNight = phase === 'nuit';

  // Position players in a circle around a virtual table
  const getPlayerPosition = (index: number, total: number) => {
    const angle = (index / total) * 2 * Math.PI - Math.PI / 2; // Start from top
    const radiusX = 45; // Horizontal radius in percentage
    const radiusY = 35; // Vertical radius in percentage
    const centerX = 50;
    const centerY = 50;

    const x = centerX + radiusX * Math.cos(angle);
    const y = centerY + radiusY * Math.sin(angle);

    return {
      left: `${x}%`,
      top: `${y}%`,
      transform: 'translate(-50%, -50%)',
    };
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
          {players.map((player, index) => (
            <PlayerAvatar
              key={player.name}
              player={player}
              isNight={isNight}
              isSelectable={selectableMode && player.is_alive && !player.is_human}
              isSelected={selectedPlayer === player.name}
              onClick={() => onPlayerSelect(player.name)}
              style={getPlayerPosition(index, players.length)}
            />
          ))}
        </div>
      </div>

      <div className="ground" />
    </div>
  );
}
