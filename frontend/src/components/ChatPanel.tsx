import { Send } from 'lucide-react';
import { useState, useEffect } from 'react';
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

  useEffect(() => {
    if (discussions.length > 0) {
      const lastDiscussion = discussions[discussions.length - 1];
      console.log(`[FRONTEND_DISPLAY] NEW MESSAGE DISPLAYED - ${lastDiscussion.player}: ${lastDiscussion.message.substring(0, 80)}...`);
    }
  }, [discussions]);

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
        <h3 className="chat-title">⚜️ The Chronicle ⚜️</h3>
      </div>

      <div className="chat-messages">
        {discussions.length === 0 ? (
          <div className="chat-empty">
            Waiting for discussions...
          </div>
        ) : (
          discussions.map((discussion, index) => {
            console.log(`[FRONTEND_RENDER] Rendering message #${index} - ${discussion.player}`);
            return (
              <div
                key={index}
                className={`chat-message ${discussion.player === humanPlayerName ? 'human' : 'ai'}`}
              >
                <div className="message-player">{discussion.player}</div>
                <div className="message-text">{discussion.message}</div>
              </div>
            );
          })
        )}
      </div>

      {canDiscuss && (
        <div className="chat-input-area">
          <div className="chat-input-wrapper">
            <textarea
              className="chat-input"
              placeholder="Speak to the village..."
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
