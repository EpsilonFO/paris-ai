import type { Player } from '../types';
import './PlayerAvatar.css';

interface PlayerAvatarProps {
  player: Player;
  isSelected?: boolean;
  isSelectable?: boolean;
  onClick?: () => void;
  isNight?: boolean;
  style?: React.CSSProperties;
}

const AVATAR_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
];

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function getInitials(name: string): string {
  return name.charAt(0).toUpperCase();
}

export function PlayerAvatar({
  player,
  isSelected,
  isSelectable,
  onClick,
  isNight,
  style,
}: PlayerAvatarProps) {
  const avatarColor = getAvatarColor(player.name);
  const isDead = !player.is_alive;

  return (
    <div
      className={`player-avatar-container ${isDead ? 'dead' : ''} ${isSelectable ? 'selectable' : ''} ${isSelected ? 'selected' : ''}`}
      onClick={isSelectable && !isDead ? onClick : undefined}
      style={style}
    >

      <div
        className={`player-avatar ${isNight ? 'night' : 'day'}`}
        style={{ backgroundColor: isDead ? '#666' : avatarColor }}
      >
        <span className="player-initial">{getInitials(player.name)}</span>
        {isDead && <div className="death-overlay">X</div>}
        {player.is_human && <div className="human-indicator">YOU</div>}
      </div>

      <div className="player-name">{player.name}</div>

      {player.role && (
        <div className={`player-role ${player.role.toLowerCase().replace('-', '_')}`}>
          {player.role}
        </div>
      )}

      {player.personality && !isDead && (
        <div className="player-personality">{player.personality}</div>
      )}
    </div>
  );
}
