import { Skull } from 'lucide-react';
import type { Player } from '../types';
import './PlayerCard.css';

interface PlayerCardProps {
  player: Player;
  showVote: boolean;
  onVote: () => void;
  isNight: boolean;
  isSelected?: boolean;
  isSelectable?: boolean;
  isWolfAlly?: boolean;
}

export function PlayerCard({
  player,
  showVote,
  onVote,
  isSelected,
  isSelectable,
  isWolfAlly,
}: PlayerCardProps) {
  const canVote = isSelectable && player.is_alive;

  return (
    <div
      className={`player-card ${!player.is_alive ? 'dead' : ''} ${isSelected ? 'selected' : ''} ${canVote && showVote ? 'votable' : ''} ${isWolfAlly ? 'wolf-ally' : ''}`}
      onClick={() => canVote && showVote && onVote()}
    >
      <div className="player-card-inner">
        {/* Status indicator */}
        <div className="player-status">
          {!player.is_alive && (
            <div className="death-indicator">
              <Skull size={20} />
            </div>
          )}
          {isWolfAlly && player.is_alive && (
            <div className="wolf-ally-badge" title="Allié loup">
              🐺
            </div>
          )}
        </div>

        {/* Role indicator */}
        {player.role && (
          <div className="role-badge">
            {player.role === 'wAIr-wolf' && '🐺'}
            {player.role === 'Seer' && '👁️'}
            {player.role === 'Witch' && '🧙'}
            {player.role === 'Hunter' && '🏹'}
            {player.role === 'Villager' && '👨'}
          </div>
        )}

        {/* Player info */}
        <div className="player-info">
          <div className="player-name">{player.name}</div>
          {player.role && <div className="player-role">{player.role}</div>}
          {player.personality && (
            <div className="player-personality">{player.personality}</div>
          )}
        </div>

        {/* Vote button */}
        {canVote && showVote && (
          <button className="vote-button" onClick={onVote}>
            Vote
          </button>
        )}
      </div>
    </div>
  );
}
