import { Skull, Loader2 } from 'lucide-react';
import type { Player } from '../types';
import { useFalImage } from '../hooks/useFalImage';
import './PlayerCard.css';

interface PlayerCardProps {
  player: Player;
  showVote?: boolean;
  onVote?: () => void;
  isNight?: boolean;
  isSelected?: boolean;
  isSelectable?: boolean;
  isWolfAlly?: boolean;
  dyingType?: 'wolf' | 'vote';
}

export function PlayerCard({
  player,
  showVote,
  onVote,
  isSelected,
  isSelectable,
  isWolfAlly,
  dyingType
}: PlayerCardProps) {
  
  // 👇 C'EST ICI QUE ÇA SE PASSE
  // On passe 'player.role' au hook.
  // Quand le joueur meurt, player.role change -> le hook régénère l'image avec le costume !
  const { imageUrl, loading } = useFalImage(
    player.personality || "", 
    player.is_human, 
    player.role // <--- Ajouté ici
  );

  const canVote = isSelectable && player.is_alive;

  return (
    <div
      className={`player-card ${!player.is_alive ? 'dead' : ''} ${isSelected ? 'selected' : ''} ${canVote && showVote ? 'votable' : ''}`}
      onClick={() => canVote && showVote && onVote && onVote()}
    >
      <div className="player-card-inner">
        
        {/* IMAGE */}
        <div className="card-image-wrapper">
          {loading ? (
            <div className="card-loader">
              <Loader2 className="animate-spin text-amber-500" size={32} />
            </div>
          ) : (
            <img 
              src={imageUrl || "/placeholder-avatar.jpg"} 
              alt={player.name} 
              className="card-image"
            />
          )}
          
          {/* ... (Le reste de tes animations slash/vote inchangé) ... */}
          {dyingType === 'wolf' && <div className="wolf-slash animate-slash-1"></div>}
          {/* ... */}
        </div>

        {/* INFO */}
        <div className="player-info">
          <div className="player-name">{player.name}</div>
          
          {/* Si le rôle est révélé, on l'affiche aussi en texte */}
          {player.role && (
            <div className="role-badge" style={{color: '#fca5a5'}}>
              {player.role}
            </div>
          )}
          
          {canVote && showVote && (
            <button className="vote-button" onClick={(e) => {
              e.stopPropagation();
              onVote && onVote();
            }}>
              VOTER
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default PlayerCard;