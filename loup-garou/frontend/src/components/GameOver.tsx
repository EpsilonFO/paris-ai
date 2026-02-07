import './GameOver.css';

interface GameOverProps {
  winner: string;
  onRestart: () => void;
}

export function GameOver({ winner, onRestart }: GameOverProps) {
  const isVillageWin = winner === 'Village';

  return (
    <div className={`game-over ${isVillageWin ? 'village-win' : 'wolf-win'}`}>
      <div className="game-over-content">
        <div className="winner-icon">
          {isVillageWin ? '🏡' : '🐺'}
        </div>
        <h1>Victoire !</h1>
        <h2>
          {isVillageWin
            ? 'Le Village a triomphe des Loups-Garous !'
            : 'Les Loups-Garous ont devore le Village !'}
        </h2>
        <button className="restart-button" onClick={onRestart}>
          Nouvelle Partie
        </button>
      </div>
    </div>
  );
}
