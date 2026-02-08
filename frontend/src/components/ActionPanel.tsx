import './ActionPanel.css';

interface ActionPanelProps {
  pendingAction: string | null;
  yourRole: string;
  selectedTarget: string | null;
  onAction: () => void;
  onSkip?: () => void;
  wolfVictim?: string;
  hasLifePotion?: boolean;
  hasDeathPotion?: boolean;
  onWitchSave?: () => void;
  onWitchKill?: () => void;
  isLoading?: boolean;
  onSendMessage?: (message: string) => void;
}

export function ActionPanel({
  pendingAction,
  yourRole,
  selectedTarget,
  onAction,
  onSkip,
  wolfVictim,
  hasLifePotion,
  hasDeathPotion,
  onWitchSave,
  onWitchKill,
  isLoading,
}: ActionPanelProps) {
  const getActionText = () => {
    switch (pendingAction) {
      case 'wolf_vote':
        return 'Choisissez une victime pour les loups';
      case 'seer_check':
        return 'Choisissez un joueur a examiner';
      case 'witch_choice':
        return 'Utilisez vos potions';
      case 'wait_night':
        return 'La nuit tombe sur le village...';
      case 'human_discussion':
        return "C'est votre tour de parler";
      case 'day_vote':
        return 'Votez pour eliminer un suspect';
      default:
        return 'En attente...';
    }
  };

  const getButtonText = () => {
    switch (pendingAction) {
      case 'wolf_vote':
        return `Attaquer ${selectedTarget || '...'}`;
      case 'seer_check':
        return `Examiner ${selectedTarget || '...'}`;
      case 'day_vote':
        return `Voter contre ${selectedTarget || '...'}`;
      default:
        return 'Confirmer';
    }
  };

  if (pendingAction === 'witch_choice') {
    return (
      <div className="action-panel witch-panel">
        <div className="action-title">Vous etes la Sorciere</div>
        <div className="action-description">{getActionText()}</div>

        {wolfVictim && (
          <div className="witch-info">
            Les loups ont attaque <strong>{wolfVictim}</strong>
          </div>
        )}

        <div className="witch-potions">
          {hasLifePotion && wolfVictim && (
            <button
              className="potion-button life"
              onClick={onWitchSave}
              disabled={isLoading}
            >
              Sauver {wolfVictim}
            </button>
          )}

          {hasDeathPotion && selectedTarget && (
            <button
              className="potion-button death"
              onClick={onWitchKill}
              disabled={isLoading}
            >
              Tuer {selectedTarget}
            </button>
          )}
        </div>

        <button
          className="action-button skip"
          onClick={onSkip}
          disabled={isLoading}
        >
          Ne rien faire
        </button>
      </div>
    );
  }

  if (pendingAction === 'wait_night') {
    return (
      <div className="action-panel">
        <div className="action-title">Nuit paisible</div>
        <div className="action-description">{getActionText()}</div>
        <button
          className="action-button"
          onClick={onAction}
          disabled={isLoading}
        >
          {isLoading ? 'En cours...' : 'Attendre'}
        </button>
      </div>
    );
  }

  return (
    <div className="action-panel">
      <div className="action-title">Votre role: {yourRole}</div>
      <div className="action-description">{getActionText()}</div>

      <button
        className="action-button"
        onClick={onAction}
        disabled={!selectedTarget || isLoading}
      >
        {isLoading ? 'En cours...' : getButtonText()}
      </button>
    </div>
  );
}
