import { useEffect, useRef, useState } from 'react';
import type { Discussion } from '../types';
import './DiscussionPanel.css';

interface DiscussionPanelProps {
  discussions: Discussion[];
  phase: 'nuit' | 'jour';
  canDiscuss: boolean;
  isLoading: boolean;
  onSendMessage: (message: string) => void;
}

export function DiscussionPanel({
  discussions,
  phase,
  canDiscuss,
  isLoading,
  onSendMessage
}: DiscussionPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [discussions]);

  const handleSend = () => {
    if (message.trim() && !isLoading) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleSkip = () => {
    if (!isLoading) {
      onSendMessage('');
      setMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="discussion-panel">
      <div className="discussion-header">
        <h3>💬 Discussion du village</h3>
      </div>

      <div className="discussion-messages">
        {discussions.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#999', fontSize: '14px' }}>
            {phase === 'nuit'
              ? 'La nuit est tombée... Silence dans le village.'
              : 'Aucune discussion pour le moment.'}
          </div>
        ) : (
          <>
            {discussions.map((discussion, index) => (
              <div key={index} className="discussion-message">
                <div className="message-author">{discussion.player}</div>
                <div className="message-content">{discussion.message}</div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {phase === 'jour' && canDiscuss && (
        <div className="discussion-input-container">
          <textarea
            className="discussion-input"
            placeholder="Écrivez votre message..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading}
          />
          <div className="discussion-buttons">
            <button
              className="discussion-send-button"
              onClick={handleSend}
              disabled={!message.trim() || isLoading}
            >
              Envoyer
            </button>
            <button
              className="discussion-skip-button"
              onClick={handleSkip}
              disabled={isLoading}
            >
              Passer
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
