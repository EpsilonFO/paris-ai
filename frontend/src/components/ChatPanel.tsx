import { Send } from 'lucide-react';
import { useState } from 'react';
import type { Discussion } from '../types';
import './ChatPanel.css';

interface ChatPanelProps {
  discussions: Discussion[];
  pendingAction: string | null;
  humanPlayerName: string;
  onSendMessage: (message: string) => void;
}

export function ChatPanel({
  discussions,
  pendingAction,
  humanPlayerName,
  onSendMessage,
}: ChatPanelProps) {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim()) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canDiscuss = pendingAction === 'human_discussion';

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h3 className="chat-title">⚜️ La Chronique ⚜️</h3>
      </div>

      <div className="chat-messages">
        {discussions.length === 0 ? (
          <div className="chat-empty">
            En attente de discussions...
          </div>
        ) : (
          discussions.map((discussion, index) => (
            <div
              key={index}
              className={`chat-message ${discussion.player === humanPlayerName ? 'human' : 'ai'}`}
            >
              <div className="message-player">{discussion.player}</div>
              <div className="message-text">{discussion.message}</div>
            </div>
          ))
        )}
      </div>

      {canDiscuss && (
        <div className="chat-input-area">
          <div className="chat-input-wrapper">
            <textarea
              className="chat-input"
              placeholder="Parlez au village..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              rows={3}
            />
            <button
              className="chat-send-button"
              onClick={handleSend}
              disabled={!message.trim()}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
