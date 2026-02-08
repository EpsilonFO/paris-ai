import { Skull, Eye, Shield, User, Crosshair } from 'lucide-react';
import type { Player } from '@/types';
import { useFalImage } from '@/hooks/useFalImage';
import { cn } from '@/lib/utils';

interface PlayerCardProps {
  player: Player;
  showVote: boolean;
  onVote: () => void;
  isNight: boolean;
  isSelectable?: boolean;
  isSelected?: boolean;
  onSelect?: () => void;
}

const roleIcons: Record<string, typeof User> = {
  'Loup-Garou': Skull,
  'Voyante': Eye,
  'Sorcière': Shield,
};

const roleColors: Record<string, string> = {
  'Loup-Garou': 'text-red-400',
  'Voyante': 'text-blue-400',
  'Sorcière': 'text-purple-400',
  'Villageois': 'text-amber-400',
};

const PlayerCard = ({ player, showVote, onVote, isNight, isSelectable, isSelected, onSelect }: PlayerCardProps) => {
  const { imageUrl, loading } = useFalImage(player.personality || '', !player.is_human);
  const RoleIcon = (player.role && roleIcons[player.role]) || User;
  const roleColor = (player.role && roleColors[player.role]) || 'text-amber-400';
  const isDead = !player.is_alive;
  const clickable = (showVote || isSelectable) && player.is_alive && !player.is_human;

  const handleClick = () => {
    if (!clickable) return;
    if (showVote) onVote();
    if (isSelectable && onSelect) onSelect();
  };

  return (
    <div
      onClick={handleClick}
      className={cn(
        "relative rounded-lg border p-3 transition-all duration-300 flex flex-col items-center gap-2",
        isDead
          ? "bg-black/40 border-gray-700/30 opacity-50"
          : "bg-wood/80 border-amber-900/30",
        clickable && "cursor-pointer hover:border-gold-bright hover:shadow-lg hover:shadow-gold-bright/10",
        isSelected && "border-gold-bright ring-2 ring-gold-bright/50 shadow-lg shadow-gold-bright/20",
        isNight && !isDead && "bg-night-surface border-blue-900/30",
        player.is_human && !isDead && "border-gold-bright/40"
      )}
    >
      {/* Avatar */}
      <div className={cn(
        "relative w-16 h-16 rounded-full overflow-hidden border-2 flex items-center justify-center",
        isDead ? "border-gray-600" : player.is_human ? "border-gold-bright" : "border-amber-800/50",
        isNight && !isDead && "border-blue-700/50"
      )}>
        {imageUrl && !loading ? (
          <img src={imageUrl} alt={player.name} className="w-full h-full object-cover" />
        ) : (
          <div className={cn(
            "w-full h-full flex items-center justify-center",
            isDead ? "bg-gray-800" : "bg-wood-light"
          )}>
            <RoleIcon className={cn("w-7 h-7", isDead ? "text-gray-500" : roleColor)} />
          </div>
        )}
        {isDead && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
            <Skull className="w-6 h-6 text-red-400/80" />
          </div>
        )}
      </div>

      {/* Name */}
      <span className={cn(
        "text-sm font-serif font-bold truncate max-w-full",
        isDead ? "text-gray-500 line-through" : "text-amber-100",
        player.is_human && !isDead && "text-gold-bright"
      )}>
        {player.name} {player.is_human && "(vous)"}
      </span>

      {/* Role (visible only if revealed) */}
      {player.role && (
        <span className={cn("text-xs italic", isDead ? "text-gray-600" : roleColor)}>
          {player.role}
        </span>
      )}

      {/* Vote target indicator */}
      {clickable && (
        <div className="absolute -top-1 -right-1">
          <Crosshair className={cn(
            "w-5 h-5",
            isSelected ? "text-gold-bright" : "text-amber-600/40"
          )} />
        </div>
      )}

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/30 rounded-lg">
          <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
};

export default PlayerCard;
