import './ActionPanel.css';

interface Event {
  id: number;
  type: 'death' | 'saved' | 'vote' | 'info';
  message: string;
}

interface EventLogProps {
  events: Event[];
}

export function EventLog({ events }: EventLogProps) {
  if (events.length === 0) return null;

  return (
    <div className="event-log">
      <h3>Evenements</h3>
      {events.slice(-10).map((event) => (
        <div key={event.id} className={`event-item ${event.type}`}>
          {event.message}
        </div>
      ))}
    </div>
  );
}
