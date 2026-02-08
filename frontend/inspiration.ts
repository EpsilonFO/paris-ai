import { useState } from 'react';
import { Skull, Trophy, Moon } from 'lucide-react';
import { GameState, Discussion, Player } from '@/types/game';
import PlayerCard from './PlayerCard';
import ChatPanel from './ChatPanel';
import PhaseIndicator from './PhaseIndicator';
import { cn } from '@/lib/utils';

// Mock data for demonstration
const mockPlayers: Player[] = [
  { name: "Guillaume", is_alive: true, is_human: true, role: "Villageois", personality: "Prudent" },
  { name: "Élise", is_alive: true, is_human: false, role: "Loup-Garou", personality: "Rusée" },
  { name: "Bernard", is_alive: false, is_human: false, role: "Voyante", personality: "Sage" },
  { name: "Marie", is_alive: true, is_human: false, personality: "Méfiante" },
  { name: "Jacques", is_alive: true, is_human: false, personality: "Impulsif" },
  { name: "Isabelle", is_alive: true, is_human: false, personality: "Observatrice" },
  { name: "Pierre", is_alive: false, is_human: false, role: "Chasseur", personality: "Brave" },
  { name: "Margot", is_alive: true, is_human: false, personality: "Discrète" },
];

const mockDiscussions: Discussion[] = [
  { player: "Marie", message: "J'ai remarqué qu'Élise était particulièrement silencieuse cette nuit..." },
  { player: "Jacques", message: "Absurde ! Tu accuses sans preuve, comme d'habitude !" },
  { player: "Guillaume", message: "Calmons-nous. Nous devons réfléchir avant d'agir." },
  { player: "Isabelle", message: "Je suis d'accord avec Guillaume. Précipitation mène à l'erreur." },
  { player: "Élise", message: "Marie cherche à détourner l'attention. C'est elle la suspecte !" },
];

interface GameInterfaceProps {
  initialState?: GameState;
  initialDiscussions?: Discussion[];
}

const GameInterface = ({ initialState, initialDiscussions }: GameInterfaceProps) => {
  const [gameState, setGameState] = useState<GameState>(initialState || {
    phase: 'jour',
    day_number: 3,
    players: mockPlayers,
    pending_action: 'human_discussion',
    status: 'en_cours',
  });

  const [discussions, setDiscussions] = useState<Discussion[]>(initialDiscussions || mockDiscussions);

  const humanPlayer = gameState.players.find(p => p.is_human);
  const isNight = gameState.phase === 'nuit';
  const showVoteButtons = gameState.pending_action === 'vote';

  const handleVote = (playerName: string) => {
    console.log(`Vote contre ${playerName}`);
    // Add vote logic here
  };

  const handleSendMessage = (message: string) => {
    if (humanPlayer) {
      setDiscussions(prev => [...prev, { player: humanPlayer.name, message }]);
    }
  };

  // Victory/Defeat screen
  if (gameState.status !== 'en_cours') {
    const isVillageVictory = gameState.status === 'victoire_village';
    
    return (
      <div className="min-h-screen wood-panel flex items-center justify-center p-8">
        <div className="parchment ornate-frame p-12 text-center max-w-lg">
          <div className={cn(
            "w-24 h-24 mx-auto mb-6 rounded-full flex items-center justify-center",
            isVillageVictory 
              ? "bg-gradient-to-br from-gold-bright to-gold-dark"
              : "bg-gradient-to-br from-blood to-destructive"
          )}>
            {isVillageVictory ? (
              <Trophy className="w-12 h-12 text-primary-foreground" />
            ) : (
              <Skull className="w-12 h-12 text-parchment-light" />
            )}
          </div>
          
          <h1 className="font-display text-3xl mb-4 text-ink-brown">
            {isVillageVictory ? "Victoire du Village !" : "Les Loups Triomphent..."}
          </h1>
          
          <p className="font-serif text-lg text-muted-foreground italic">
            {isVillageVictory 
              ? "La lumière a vaincu les ténèbres. Le village peut enfin dormir en paix."
              : "Les hurlements résonnent dans la nuit. Le village n'est plus qu'un souvenir..."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen wood-panel flex flex-col relative">
      {/* Night overlay */}
      {isNight && <div className="night-overlay" />}

      {/* Header */}
      <header className="relative z-20 flex items-center justify-between px-6 py-4 border-b border-gold-dark/30">
        <h1 className="font-display text-2xl text-foreground tracking-wide">
          Loup-Garou
        </h1>
        <PhaseIndicator phase={gameState.phase} dayNumber={gameState.day_number} />
      </header>

      {/* Main content */}
      <div className="relative z-20 flex-1 flex overflow-hidden">
        {/* Village area (70%) */}
        <main className="w-[70%] p-6 overflow-y-auto scroll-container">
          <div className="mb-4">
            <h2 className="font-display text-xl text-foreground flex items-center gap-2">
              <span className="text-gold-bright">⚜</span>
              Le Village
              <span className="text-gold-bright">⚜</span>
            </h2>
            <p className="text-sm text-muted-foreground mt-1 italic">
              {gameState.players.filter(p => p.is_alive).length} villageois en vie
            </p>
          </div>

          {/* Players grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {gameState.players.map((player) => (
              <PlayerCard
                key={player.name}
                player={player}
                showVote={showVoteButtons}
                onVote={() => handleVote(player.name)}
                isNight={isNight}
              />
            ))}
          </div>

          {/* Action hint */}
          {gameState.pending_action && (
            <div className="mt-6 text-center">
              <div className={cn(
                "inline-block px-6 py-3 rounded-sm font-serif italic text-sm",
                "parchment ornate-frame",
                gameState.pending_action === 'vote' && "action-glow"
              )}>
                {gameState.pending_action === 'vote' && (
                  <span className="text-ink-brown">
                    🗳️ Choisissez qui éliminer...
                  </span>
                )}
                {gameState.pending_action === 'human_discussion' && (
                  <span className="text-ink-brown">
                    💬 C'est à vous de parler dans la Chronique
                  </span>
                )}
                {gameState.pending_action === 'wait_night' && (
                  <span className="text-ink-brown flex items-center gap-2 justify-center">
                    <Moon className="w-4 h-4" />
                    Les loups rôdent...
                  </span>
                )}
              </div>
            </div>
          )}
        </main>

        {/* Chat panel (30%) */}
        <aside className="w-[30%] border-l border-gold-dark/30 p-4">
          <ChatPanel
            discussions={discussions}
            pendingAction={gameState.pending_action}
            humanPlayerName={humanPlayer?.name || 'Joueur'}
            onSendMessage={handleSendMessage}
          />
        </aside>
      </div>
    </div>
  );
};

export default GameInterface;
