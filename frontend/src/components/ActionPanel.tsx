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
        return 'Choose a victim for the werewolves';
      case 'seer_check':
        return 'Choose a player to examine';
      case 'witch_choice':
        return 'Use your potions';
      case 'wait_night':
        return 'Night falls on the village...';
      case 'human_discussion':
        return "It's your turn to speak";
      case 'day_vote':
        return 'Vote to eliminate a suspect';
      default:
        return 'Waiting...';
    }
  };

  const getButtonText = () => {
    switch (pendingAction) {
      case 'wolf_vote':
        return `Attack ${selectedTarget || '...'}`;
      case 'seer_check':
        return `Examine ${selectedTarget || '...'}`;
      case 'day_vote':
        return `Vote against ${selectedTarget || '...'}`;
      default:
        return 'Confirm';
    }
  };

  if (pendingAction === 'witch_choice') {
    return (
      <div className="action-panel witch-panel">
        <div className="action-title">You are the Witch</div>
        <div className="action-description">{getActionText()}</div>

        {wolfVictim && (
          <div className="witch-info">
            The werewolves attacked <strong>{wolfVictim}</strong>
          </div>
        )}

        <div className="witch-potions">
          {hasLifePotion && wolfVictim && (
            <button
              className="potion-button life"
              onClick={onWitchSave}
              disabled={isLoading}
            >
              Save {wolfVictim}
            </button>
          )}

          {hasDeathPotion && selectedTarget && (
            <button
              className="potion-button death"
              onClick={onWitchKill}
              disabled={isLoading}
            >
              Kill {selectedTarget}
            </button>
          )}
        </div>

        <button
          className="action-button skip"
          onClick={onSkip}
          disabled={isLoading}
        >
          Do nothing
        </button>
      </div>
    );
  }

  if (pendingAction === 'wait_night') {
    return (
      <div className="action-panel">
        <div className="action-title">Peaceful night</div>
        <div className="action-description">{getActionText()}</div>
        <button
          className="action-button"
          onClick={onAction}
          disabled={isLoading}
        >
          {isLoading ? 'Processing...' : 'Wait'}
        </button>
      </div>
    );
  }

  return (
    <div className="action-panel">
      <div className="action-title">Your role: {yourRole}</div>
      <div className="action-description">{getActionText()}</div>

      <button
        className="action-button"
        onClick={onAction}
        disabled={!selectedTarget || isLoading}
      >
        {isLoading ? 'Processing...' : getButtonText()}
      </button>
    </div>
  );
}
