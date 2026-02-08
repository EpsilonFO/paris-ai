import { useState, useEffect, useRef } from 'react';
import { Send, MessageSquare } from 'lucide-react';
import type { Discussion } from '@/types';
import { cn } from '@/lib/utils';

interface ChatPanelProps {
  discussions: Discussion[];
  pendingAction: string | null;
  humanPlayerName: string;
  onSendMessage: (message: string) => void;
}

const ChatPanel = ({ discussions, pendingAction, humanPlayerName, onSendMessage }: ChatPanelProps) => {
  const [message, setMessage] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll vers le bas quand un message arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [discussions]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      onSendMessage(message);
      setMessage('');
    }
  };

  // On peut écrire seulement si c'est notre tour
  const canChat = pendingAction === 'human_discussion';

  return (
    <div className="flex flex-col h-full bg-black/20 rounded-lg border border-amber-900/30 overflow-hidden">
      {/* Titre */}
      <div className="p-3 bg-amber-950/50 border-b border-amber-900/30 flex items-center gap-2">
        <MessageSquare className="w-4 h-4 text-amber-500" />
        <h3 className="font-serif text-amber-100 text-sm font-bold tracking-wider">CHRONIQUES DU VILLAGE</h3>
      </div>

      {/* Zone des messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
        {discussions.length === 0 ? (
          <div className="text-center text-amber-500/40 italic text-sm mt-10">
            Le silence règne sur le village...
          </div>
        ) : (
          discussions.map((disc, idx) => {
            const isMe = disc.player === humanPlayerName || disc.player === 'Moi';
            return (
              <div key={idx} className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                <span className="text-xs text-amber-500/60 mb-1 px-1 font-serif">
                  {disc.player}
                </span>
                <div className={cn(
                  "max-w-[85%] px-3 py-2 rounded-lg text-sm leading-relaxed shadow-sm",
                  isMe 
                    ? "bg-amber-700/80 text-amber-50 rounded-tr-none border border-amber-600/50" 
                    : "bg-[#2c241b] text-amber-100/90 rounded-tl-none border border-amber-900/30"
                )}>
                  {disc.message}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Zone de saisie */}
      <div className="p-3 bg-amber-950/30 border-t border-amber-900/30">
        <form onSubmit={handleSubmit} className="relative flex items-center gap-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={!canChat}
            placeholder={canChat ? "Exprimez-vous..." : "Attendez votre tour..."}
            className={cn(
              "w-full bg-[#1a1510] border rounded px-4 py-2 text-sm text-amber-100 placeholder:text-amber-700/50 focus:outline-none focus:ring-1 focus:ring-amber-600 transition-colors",
              canChat ? "border-amber-700/50" : "border-amber-900/20 opacity-50 cursor-not-allowed"
            )}
          />
          <button
            type="submit"
            disabled={!canChat || !message.trim()}
            className={cn(
              "p-2 rounded transition-colors",
              canChat && message.trim() 
                ? "bg-amber-700 text-amber-100 hover:bg-amber-600 shadow-lg" 
                : "bg-amber-900/20 text-amber-800 cursor-not-allowed"
            )}
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;