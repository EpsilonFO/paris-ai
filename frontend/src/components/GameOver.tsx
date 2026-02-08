import './GameOver.css';

interface GameOverProps {
  winner: string;
  onRestart: () => void;
}

export function GameOver({ winner, onRestart }: GameOverProps) {
  const isVillageWin = winner === 'Village';

  return (
    <div className="game-over wood-panel">
      <div className="game-over-parchment">
        <div className={`winner-icon-circle ${isVillageWin ? 'village' : 'wolf'}`}>
          {isVillageWin ? '🏆' : '💀'}
        </div>

        <h1 className="game-over-title">
          {isVillageWin ? 'Victoire du Village !' : 'Les Loups Triomphent...'}
        </h1>

        <p className="game-over-description">
          {isVillageWin
            ? 'La lumiere a vaincu les tenebres. Le village peut enfin dormir en paix.'
            : 'Les hurlements resonnent dans la nuit. Le village n\'est plus qu\'un souvenir...'}
        </p>

        <button className="restart-button" onClick={onRestart}>
          Nouvelle Partie
        </button>
      </div>
    </div>
  );
}
