import './PhaseIndicator.css';

interface PhaseIndicatorProps {
  phase: 'nuit' | 'jour';
  dayNumber: number;
}

export function PhaseIndicator({ phase, dayNumber }: PhaseIndicatorProps) {
  const isNight = phase === 'nuit';

  return (
    <div className="phase-indicator-component">
      <div className="phase-content">
        <div className="phase-icon">
          {isNight ? '🌙' : '☀️'}
        </div>
        <div className="phase-text">
          <div className="phase-name">
            {isNight ? 'Nuit' : 'Jour'} {dayNumber}
          </div>
        </div>
      </div>
    </div>
  );
}
