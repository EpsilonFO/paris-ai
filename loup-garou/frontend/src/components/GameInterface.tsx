import { useState, useCallback, useEffect, useRef } from 'react';
import { Skull, Trophy, Moon, Shield, Droplet, Swords, SkipForward, Loader2, Eye } from 'lucide-react';
import type { GameState, Discussion, ActionResult } from '@/types';
import { getGameState, sendAction, getDiscussions, sendMessage } from '@/api';
import PlayerCard from './PlayerCard';
import ChatPanel from './ChatPanel';
import PhaseIndicator from './PhaseIndicator';
import { cn } from '@/lib/utils';

interface GameEvent {
  id: number;
  type: 'death' | 'saved' | 'vote' | 'info';
  message: string;
}

interface GameInterfaceProps {
  gameId: string;
  initialRole: string;
  fellowWolves: string[];
  onRestart: () => void;
}

const GameInterface = ({ gameId, initialRole, fellowWolves, onRestart }: GameInterfaceProps) => {
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [events, setEvents] = useState<GameEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [gameOver, setGameOver] = useState<{ winner: string } | null>(null);
  const [witchInfo, setWitchInfo] = useState<{
    victim?: string;
    hasLife: boolean;
    hasDeath: boolean;
  }>({ hasLife: true, hasDeath: true });
  const [skipDayVoteExecuted, setSkipDayVoteExecuted] = useState(false);
  const prevPhaseRef = useRef<string | null>(null);

  const addEvent = useCallback((type: GameEvent['type'], message: string) => {
    setEvents((prev) => [...prev, { id: Date.now(), type, message }]);
  }, []);

  // Load initial game state
  useEffect(() => {
    getGameState(gameId).then(setGameState).catch(console.error);
  }, [gameId]);

  const humanPlayer = gameState?.players.find(p => p.is_human);
  const isNight = gameState?.phase === 'nuit';
  const pendingAction = gameState?.pending_action ?? null;

  // Determine which action mode we're in
  const isSelectableMode = ['wolf_vote', 'seer_check', 'day_vote'].includes(pendingAction || '');
  const isWitchSelectMode = pendingAction === 'witch_choice' && witchInfo.hasDeath;

  // ── Process backend action result ────────────────────────
  const processActionResult = useCallback((result: ActionResult) => {
    result.messages.forEach((msg) => addEvent('info', msg));

    if (result.seer_result) {
      const { target, role, is_wolf } = result.seer_result;
      addEvent(is_wolf ? 'death' : 'saved', `${target} est ${role}`);
    }

    if (result.night_events) {
      result.night_events.deaths.forEach((death) => {
        addEvent('death', `${death.name} (${death.role}) a été tué par ${death.cause}`);
      });
      if (result.night_events.saved) {
        addEvent('saved', `${result.night_events.saved} a été sauvé par la sorcière`);
      }
    }

    if (result.eliminated) {
      addEvent('vote', `${result.eliminated.name} (${result.eliminated.role}) éliminé avec ${result.eliminated.votes} votes`);
    }

    if (result.tie) {
      addEvent('vote', "Égalité ! Personne n'est éliminé");
    }

    if (result.game_over) {
      setGameOver({ winner: result.game_over.winner });
    }
  }, [addEvent]);

  // ── Load AI discussions with delay animation ─────────────
  const loadDiscussions = useCallback(async () => {
    try {
      const disc = await getDiscussions(gameId);
      setDiscussions([]);
      for (let i = 0; i < disc.length; i++) {
        await new Promise((resolve) => setTimeout(resolve, 800));
        setDiscussions((prev) => [...prev, disc[i]]);
      }
    } catch (error) {
      console.error('Failed to load discussions:', error);
    }
  }, [gameId]);

  // ── Auto-load discussions when day phase starts ──────────
  useEffect(() => {
    if (
      gameState?.phase === 'jour' &&
      gameState.status === 'en_cours' &&
      prevPhaseRef.current !== 'jour'
    ) {
      loadDiscussions().then(() => {
        getGameState(gameId).then(setGameState);
      });
    }
    prevPhaseRef.current = gameState?.phase ?? null;
  }, [gameState?.phase, gameState?.status, gameId, loadDiscussions]);

  // Reset skipDayVoteExecuted when day changes
  useEffect(() => {
    setSkipDayVoteExecuted(false);
  }, [gameState?.day_number]);

  // Handle dead player auto-vote during day
  useEffect(() => {
    const isPlayerDead = humanPlayer && !humanPlayer.is_alive;

    if (
      gameState?.phase === 'jour' &&
      gameState.pending_action === 'day_vote' &&
      isPlayerDead &&
      !isLoading &&
      !skipDayVoteExecuted
    ) {
      setSkipDayVoteExecuted(true);
      setIsLoading(true);
      sendAction(gameId, 'skip_day_vote')
        .then((result) => {
          processActionResult(result);
          return getGameState(gameId);
        })
        .then(setGameState)
        .catch((error) => {
          console.error('Skip day vote failed:', error);
          setSkipDayVoteExecuted(false);
        })
        .finally(() => setIsLoading(false));
    }
  }, [gameState?.phase, gameState?.pending_action, gameState?.day_number, isLoading, skipDayVoteExecuted, humanPlayer, gameId, processActionResult]);

  // ── Player select handler ────────────────────────────────
  const handlePlayerSelect = (playerName: string) => {
    if (!isSelectableMode && !isWitchSelectMode) return;
    setSelectedTarget(prev => prev === playerName ? null : playerName);
  };

  // ── Main action handler ──────────────────────────────────
  const handleAction = async () => {
    if (!gameState) return;
    setIsLoading(true);
    try {
      let result: ActionResult;
      if (pendingAction === 'wait_night') {
        result = await sendAction(gameId, 'wait_night');
      } else if (selectedTarget) {
        result = await sendAction(gameId, pendingAction!, selectedTarget);
      } else {
        return;
      }
      processActionResult(result);
      setSelectedTarget(null);

      const newState = await getGameState(gameId);
      setGameState(newState);

      if (newState.phase === 'jour' && newState.status === 'en_cours') {
        await loadDiscussions();
        const updatedState = await getGameState(gameId);
        setGameState(updatedState);
      } else {
        setDiscussions([]);
      }
    } catch (error) {
      console.error('Action failed:', error);
      addEvent('info', `Erreur: ${error instanceof Error ? error.message : 'action échouée'}`);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Witch handlers ───────────────────────────────────────
  const handleWitchSave = async () => {
    setIsLoading(true);
    try {
      const result = await sendAction(gameId, 'witch_choice', undefined, true);
      processActionResult(result);
      setWitchInfo((prev) => ({ ...prev, hasLife: false }));
      const newState = await getGameState(gameId);
      setGameState(newState);
      if (newState.phase === 'jour') await loadDiscussions();
    } catch (error) {
      console.error('Witch save failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWitchKill = async () => {
    if (!selectedTarget) return;
    setIsLoading(true);
    try {
      const result = await sendAction(gameId, 'witch_choice', undefined, false, selectedTarget);
      processActionResult(result);
      setWitchInfo((prev) => ({ ...prev, hasDeath: false }));
      setSelectedTarget(null);
      const newState = await getGameState(gameId);
      setGameState(newState);
      if (newState.phase === 'jour') await loadDiscussions();
    } catch (error) {
      console.error('Witch kill failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWitchSkip = async () => {
    setIsLoading(true);
    try {
      const result = await sendAction(gameId, 'witch_choice');
      processActionResult(result);
      const newState = await getGameState(gameId);
      setGameState(newState);
      if (newState.phase === 'jour') await loadDiscussions();
    } catch (error) {
      console.error('Witch skip failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Send message handler ─────────────────────────────────
  const handleSendMessage = async (message: string) => {
    setIsLoading(true);
    try {
      const result = await sendMessage(gameId, message);
      if (message) {
        addEvent('info', `Vous avez dit: "${message}"`);
      } else {
        addEvent('info', 'Vous avez passé votre tour');
      }
      if (result.discussions?.length > 0) {
        for (const disc of result.discussions) {
          await new Promise((resolve) => setTimeout(resolve, 800));
          setDiscussions((prev) => [...prev, disc]);
        }
      }
      const newState = await getGameState(gameId);
      setGameState(newState);
    } catch (error) {
      console.error('Send message failed:', error);
      addEvent('info', `Erreur: ${error instanceof Error ? error.message : 'envoi échoué'}`);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Loading state ────────────────────────────────────────
  if (!gameState) {
    return (
      <div className="min-h-screen wood-panel flex items-center justify-center">
        <Loader2 className="w-10 h-10 text-gold-bright animate-spin" />
      </div>
    );
  }

  // ── Victory / Defeat screen ──────────────────────────────
  if (gameOver) {
    const isVillageVictory = gameOver.winner === 'Village';
    return (
      <div className="min-h-screen wood-panel flex items-center justify-center p-8">
        <div className="parchment ornate-frame p-12 text-center max-w-lg rounded-lg">
          <div className={cn(
            "w-24 h-24 mx-auto mb-6 rounded-full flex items-center justify-center",
            isVillageVictory
              ? "bg-gradient-to-br from-gold-bright to-gold-dark"
              : "bg-gradient-to-br from-blood to-red-900"
          )}>
            {isVillageVictory ? (
              <Trophy className="w-12 h-12 text-white" />
            ) : (
              <Skull className="w-12 h-12 text-parchment-light" />
            )}
          </div>
          <h1 className="font-display text-3xl mb-4 text-ink-brown">
            {isVillageVictory ? "Victoire du Village !" : "Les Loups Triomphent..."}
          </h1>
          <p className="font-serif text-lg text-ink-brown/70 italic mb-8">
            {isVillageVictory
              ? "La lumière a vaincu les ténèbres. Le village peut enfin dormir en paix."
              : "Les hurlements résonnent dans la nuit. Le village n'est plus qu'un souvenir..."}
          </p>
          <button
            onClick={onRestart}
            className="px-6 py-3 bg-gold-bright text-ink-brown font-bold rounded-lg hover:bg-gold-dark transition-colors"
          >
            Nouvelle Partie
          </button>
        </div>
      </div>
    );
  }

  // ── Action bar content ───────────────────────────────────
  const isPlayerDead = humanPlayer && !humanPlayer.is_alive;

  const renderActionBar = () => {
    if (!pendingAction || gameState.status !== 'en_cours') return null;

    // Dead player spectator
    if (isPlayerDead) {
      return (
        <div className="px-6 py-4 bg-black/40 border-t border-gray-700/30 text-center">
          <p className="text-gray-400 italic font-serif">
            <Skull className="w-4 h-4 inline mr-2" />
            Vous êtes mort. Vous observez le jeu...
          </p>
        </div>
      );
    }

    // Witch choice
    if (pendingAction === 'witch_choice') {
      return (
        <div className="px-6 py-4 bg-black/40 border-t border-amber-900/30">
          <p className="text-amber-300 font-serif text-center mb-3">
            <Shield className="w-4 h-4 inline mr-2" />
            Sorcière — Choisissez une potion
            {witchInfo.victim && <span className="text-red-400 ml-1">(Victime : {witchInfo.victim})</span>}
          </p>
          <div className="flex justify-center gap-3 flex-wrap">
            {witchInfo.hasLife && witchInfo.victim && (
              <button
                onClick={handleWitchSave}
                disabled={isLoading}
                className="px-4 py-2 bg-green-700/80 text-green-100 rounded-lg hover:bg-green-600 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <Droplet className="w-4 h-4" /> Sauver
              </button>
            )}
            {witchInfo.hasDeath && (
              <button
                onClick={handleWitchKill}
                disabled={isLoading || !selectedTarget}
                className="px-4 py-2 bg-red-800/80 text-red-100 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <Skull className="w-4 h-4" /> Tuer {selectedTarget ? `(${selectedTarget})` : ''}
              </button>
            )}
            <button
              onClick={handleWitchSkip}
              disabled={isLoading}
              className="px-4 py-2 bg-amber-900/50 text-amber-300 rounded-lg hover:bg-amber-800/50 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <SkipForward className="w-4 h-4" /> Passer
            </button>
          </div>
        </div>
      );
    }

    // Wait night (villageois)
    if (pendingAction === 'wait_night') {
      return (
        <div className="px-6 py-4 bg-black/40 border-t border-blue-900/30 text-center">
          <p className="text-blue-300 font-serif mb-3">
            <Moon className="w-4 h-4 inline mr-2" />
            Les loups rôdent dans la nuit...
          </p>
          <button
            onClick={handleAction}
            disabled={isLoading}
            className="px-6 py-2 bg-blue-800/60 text-blue-200 rounded-lg hover:bg-blue-700/60 transition-colors disabled:opacity-50"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin inline" /> : "Attendre le jour"}
          </button>
        </div>
      );
    }

    // Discussion hint
    if (pendingAction === 'human_discussion') {
      return (
        <div className="px-6 py-3 bg-black/30 border-t border-amber-900/20 text-center">
          <p className="text-amber-400/70 font-serif text-sm italic">
            C'est à vous de parler dans les Chroniques du Village
          </p>
        </div>
      );
    }

    // Vote / Attack / Seer
    if (isSelectableMode) {
      const labels: Record<string, { title: string; button: string; icon: typeof Swords }> = {
        wolf_vote: { title: "Choisissez votre victime", button: "Attaquer", icon: Skull },
        seer_check: { title: "Qui voulez-vous observer ?", button: "Observer", icon: Eye },
        day_vote: { title: "Votez pour éliminer un joueur", button: "Voter", icon: Swords },
      };
      const config = labels[pendingAction!] || labels.day_vote;
      const Icon = config.icon;

      return (
        <div className="px-6 py-4 bg-black/40 border-t border-amber-900/30">
          <p className="text-amber-300 font-serif text-center mb-3">
            <Icon className="w-4 h-4 inline mr-2" />
            {config.title}
          </p>
          <div className="flex justify-center">
            <button
              onClick={handleAction}
              disabled={isLoading || !selectedTarget}
              className="px-6 py-2 bg-gold-bright text-ink-brown font-bold rounded-lg hover:bg-gold-dark transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : (
                <>
                  <Icon className="w-4 h-4" />
                  {config.button} {selectedTarget ? `(${selectedTarget})` : ''}
                </>
              )}
            </button>
          </div>
        </div>
      );
    }

    return null;
  };

  // ── Main render ──────────────────────────────────────────
  return (
    <div className="min-h-screen wood-panel flex flex-col relative">
      {isNight && <div className="night-overlay" />}

      {/* Header */}
      <header className="relative z-20 flex items-center justify-between px-6 py-4 border-b border-gold-dark/30">
        <div>
          <h1 className="font-display text-2xl text-parchment-light tracking-wide">
            Loup-Garou
          </h1>
          <span className={cn(
            "text-xs font-serif italic",
            initialRole === 'Loup-Garou' ? 'text-red-400' : 'text-amber-400'
          )}>
            {initialRole}
          </span>
        </div>
        <PhaseIndicator phase={gameState.phase} dayNumber={gameState.day_number} />
      </header>

      {/* Fellow wolves indicator */}
      {fellowWolves.length > 0 && (
        <div className="relative z-20 mx-6 mt-2 px-4 py-2 bg-red-900/30 rounded-lg border border-red-800/30 text-red-300 text-xs">
          <Skull className="w-3 h-3 inline mr-1" />
          Alliés loups : {fellowWolves.join(', ')}
        </div>
      )}

      {/* Main content */}
      <div className="relative z-20 flex-1 flex overflow-hidden">
        {/* Village area (70%) */}
        <main className="w-[70%] p-6 overflow-y-auto scroll-container">
          <div className="mb-4">
            <h2 className="font-display text-xl text-parchment-light flex items-center gap-2">
              <span className="text-gold-bright">&#9884;</span>
              Le Village
              <span className="text-gold-bright">&#9884;</span>
            </h2>
            <p className="text-sm text-amber-100/50 mt-1 italic">
              {gameState.players.filter(p => p.is_alive).length} villageois en vie
            </p>
          </div>

          {/* Players grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {gameState.players.map((player) => (
              <PlayerCard
                key={player.name}
                player={player}
                showVote={pendingAction === 'day_vote' && !isPlayerDead}
                onVote={() => handlePlayerSelect(player.name)}
                isNight={!!isNight}
                isSelectable={(isSelectableMode || isWitchSelectMode) && player.is_alive && !player.is_human}
                isSelected={selectedTarget === player.name}
                onSelect={() => handlePlayerSelect(player.name)}
              />
            ))}
          </div>

          {/* Event log */}
          {events.length > 0 && (
            <div className="mt-6 space-y-1 max-h-40 overflow-y-auto scroll-container">
              {events.map((evt) => (
                <div
                  key={evt.id}
                  className={cn(
                    "text-xs px-3 py-1 rounded font-serif",
                    evt.type === 'death' && "bg-red-900/20 text-red-300",
                    evt.type === 'saved' && "bg-green-900/20 text-green-300",
                    evt.type === 'vote' && "bg-amber-900/20 text-amber-300",
                    evt.type === 'info' && "bg-blue-900/10 text-blue-200/70"
                  )}
                >
                  {evt.message}
                </div>
              ))}
            </div>
          )}
        </main>

        {/* Chat panel (30%) */}
        <aside className="w-[30%] border-l border-gold-dark/30 p-4 flex flex-col">
          <ChatPanel
            discussions={discussions}
            pendingAction={pendingAction}
            humanPlayerName={humanPlayer?.name || 'Joueur'}
            onSendMessage={handleSendMessage}
          />
        </aside>
      </div>

      {/* Action bar */}
      <div className="relative z-20">
        {renderActionBar()}
      </div>
    </div>
  );
};

export default GameInterface;
