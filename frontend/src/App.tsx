import { useState, useEffect } from 'react';
import type { GameState, Discussion, CreateGameResponse, ActionResult } from './types';
import { createGame, getGameState, sendAction, getDiscussions, sendMessage } from './api';
import { StartScreen } from './components/StartScreen';
import { ActionPanel } from './components/ActionPanel';
import { GameOver } from './components/GameOver';
import { ChatPanel } from './components/ChatPanel';
import { PhaseIndicator } from './components/PhaseIndicator';
import { PlayerCard } from './components/PlayerCard';
import { getTTSService } from './services/ttsService';
import './App.css';
import './AppNew.css';

function App() {
  const [gameId, setGameId] = useState<string | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [yourRole, setYourRole] = useState<string>('');
  const [fellowWolves, setFellowWolves] = useState<string[]>([]);
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [gameOver, setGameOver] = useState<{ winner: string } | null>(null);
  const [witchInfo, setWitchInfo] = useState<{
    victim?: string;
    hasLife: boolean;
    hasDeath: boolean;
  }>({ hasLife: true, hasDeath: true });
  const [skipDayVoteExecuted, setSkipDayVoteExecuted] = useState(false);

  const handleStartGame = async (playerName: string, numPlayers: number, numWolves: number) => {
    setIsLoading(true);
    try {
      const response: CreateGameResponse = await createGame(playerName, numPlayers, numWolves);
      setGameId(response.game_id);
      setYourRole(response.your_role);
      setFellowWolves(response.fellow_wolves || []);

      const state = await getGameState(response.game_id);
      setGameState(state);
    } catch (error) {
      console.error('Failed to start game:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAction = async () => {
    if (!gameId || !gameState) return;

    setIsLoading(true);
    try {
      let result: ActionResult;

      if (gameState.pending_action === 'wait_night') {
        result = await sendAction(gameId, 'wait_night');
      } else if (selectedTarget) {
        result = await sendAction(gameId, gameState.pending_action!, selectedTarget);
      } else {
        return;
      }

      processActionResult(result);
      setSelectedTarget(null);

      const newState = await getGameState(gameId);
      setGameState(newState);

      if (newState.phase === 'jour' && newState.status === 'en_cours') {
        await loadDiscussions(newState);
        // Rafraîchir l'état du jeu pour récupérer le pending_action mis à jour (human_discussion)
        const updatedState = await getGameState(gameId);
        setGameState(updatedState);
      } else {
        setDiscussions([]);
      }
    } catch (error) {
      console.error('Action failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWitchSave = async () => {
    if (!gameId) return;
    setIsLoading(true);
    try {
      const result = await sendAction(gameId, 'witch_choice', undefined, true);
      processActionResult(result);
      setWitchInfo((prev) => ({ ...prev, hasLife: false }));

      const newState = await getGameState(gameId);
      setGameState(newState);

      if (newState.phase === 'jour') {
        await loadDiscussions(newState);
      }
    } catch (error) {
      console.error('Witch save failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWitchKill = async () => {
    if (!gameId || !selectedTarget) return;
    setIsLoading(true);
    try {
      const result = await sendAction(gameId, 'witch_choice', undefined, false, selectedTarget);
      processActionResult(result);
      setWitchInfo((prev) => ({ ...prev, hasDeath: false }));
      setSelectedTarget(null);

      const newState = await getGameState(gameId);
      setGameState(newState);

      if (newState.phase === 'jour') {
        await loadDiscussions(newState);
      }
    } catch (error) {
      console.error('Witch kill failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleWitchSkip = async () => {
    if (!gameId) return;
    setIsLoading(true);
    try {
      const result = await sendAction(gameId, 'witch_choice');
      processActionResult(result);

      const newState = await getGameState(gameId);
      setGameState(newState);

      if (newState.phase === 'jour') {
        await loadDiscussions(newState);
      }
    } catch (error) {
      console.error('Witch skip failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!gameId || !gameState) return;
    setIsLoading(true);
    try {
      // Trouver le nom du joueur humain
      const humanPlayer = gameState.players.find(p => p.is_human);
      const playerName = humanPlayer?.name || 'Vous';

      // Afficher immédiatement le message du joueur dans les discussions
      if (message) {
        setDiscussions((prev) => [...prev, { player: playerName, message }]);
      }

      const result = await sendMessage(gameId, message);

      // Afficher les nouvelles discussions des IA avec TTS (uniquement en phase JOUR)
      if (result.discussions && result.discussions.length > 0) {
        const ttsService = getTTSService();

        for (const disc of result.discussions) {
          await new Promise((resolve) => setTimeout(resolve, 800));
          setDiscussions((prev) => [...prev, disc]);

          // Jouer le TTS uniquement pour les messages des IA pendant la phase JOUR
          if (gameState.phase === 'jour') {
            try {
              // Trouver le voice_id du joueur qui parle
              const speaker = gameState.players.find(p => p.name === disc.player);
              const voiceId = speaker?.voice_id || 'YTpq7expH9539ERJ'; // Voix par défaut
              await ttsService.playText(disc.message, voiceId);
            } catch (error) {
              console.error('TTS playback failed:', error);
              // Continuer même si le TTS échoue
            }
          }
        }
      }

      // Rafraichir l'etat du jeu
      const newState = await getGameState(gameId);
      setGameState(newState);
    } catch (error) {
      console.error('Send message failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const processActionResult = (result: ActionResult) => {
    if (result.game_over) {
      setGameOver({ winner: result.game_over.winner });
    }
  };

  const loadDiscussions = async (currentGameState?: GameState) => {
    if (!gameId) return;

    // Utiliser l'état fourni en paramètre ou l'état actuel
    const stateToUse = currentGameState || gameState;
    if (!stateToUse) return;

    try {
      const disc = await getDiscussions(gameId);
      setDiscussions([]);

      const ttsService = getTTSService();

      for (let i = 0; i < disc.length; i++) {
        await new Promise((resolve) => setTimeout(resolve, 800));
        setDiscussions((prev) => [...prev, disc[i]]);

        // Jouer le TTS uniquement pour les messages des IA pendant la phase JOUR
        if (stateToUse.phase === 'jour') {
          try {
            // Trouver le voice_id du joueur qui parle
            const speaker = stateToUse.players.find(p => p.name === disc[i].player);
            const voiceId = speaker?.voice_id || 'YTpq7expH9539ERJ'; // Voix par défaut
            await ttsService.playText(disc[i].message, voiceId);
          } catch (error) {
            console.error('TTS playback failed:', error);
            // Continuer même si le TTS échoue
          }
        }
      }
    } catch (error) {
      console.error('Failed to load discussions:', error);
    }
  };

  const handleRestart = () => {
    setGameId(null);
    setGameState(null);
    setYourRole('');
    setFellowWolves([]);
    setDiscussions([]);
    setSelectedTarget(null);
    setGameOver(null);
    setWitchInfo({ hasLife: true, hasDeath: true });
    setSkipDayVoteExecuted(false);
  };

  useEffect(() => {
    if (gameState?.phase === 'jour' && gameState.status === 'en_cours' && discussions.length === 0) {
      loadDiscussions(gameState).then(() => {
        // Rafraîchir l'état du jeu pour récupérer le pending_action mis à jour
        getGameState(gameId!).then(setGameState);
      });
    }
  }, [gameState?.phase]);

  // Réinitialiser le flag skipDayVoteExecuted quand on change de jour
  useEffect(() => {
    setSkipDayVoteExecuted(false);
  }, [gameState?.day_number]);

  // Automatiser les actions quand le joueur est mort
  useEffect(() => {
    const humanPlayer = gameState?.players.find(p => p.is_human);
    const isPlayerDead = humanPlayer && !humanPlayer.is_alive;

    // Ne pas continuer si la partie est terminée
    if (gameState?.status !== 'en_cours') {
      return;
    }

    if (isPlayerDead && (gameState?.pending_action === 'auto_night' || gameState?.pending_action === 'auto_day') && !isLoading) {
      setIsLoading(true);
      sendAction(gameId!, gameState.pending_action!).then((result) => {
        processActionResult(result);
        return getGameState(gameId!);
      }).then((newState) => {
        setGameState(newState);
      }).catch((error) => {
        console.error('Auto action failed:', error);
      }).finally(() => {
        setIsLoading(false);
      });
    }
  }, [gameState?.pending_action, gameState?.players, gameState?.status, isLoading]);

  // Gérer le cas où le joueur est mort pendant le jour
  useEffect(() => {
    const humanPlayer = gameState?.players.find(p => p.is_human);
    const isPlayerDead = humanPlayer && !humanPlayer.is_alive;

    // Ne pas continuer si la partie est terminée
    if (gameState?.status !== 'en_cours') {
      return;
    }

    if (gameState?.phase === 'jour' && gameState.pending_action === 'day_vote' && isPlayerDead && !isLoading && !skipDayVoteExecuted) {
      // Le joueur est mort mais c'est le moment de voter - faire voter les IA automatiquement
      setSkipDayVoteExecuted(true);
      setIsLoading(true);
      sendAction(gameId!, 'skip_day_vote').then((result) => {
        processActionResult(result);
        return getGameState(gameId!);
      }).then((newState) => {
        setGameState(newState);
      }).catch((error) => {
        console.error('Skip day vote failed:', error);
        setSkipDayVoteExecuted(false);
      }).finally(() => {
        setIsLoading(false);
      });
    }
  }, [gameState?.phase, gameState?.pending_action, gameState?.day_number, gameState?.status, isLoading, skipDayVoteExecuted]);

  if (gameOver) {
    return (
      <div className="app full-screen">
        <GameOver winner={gameOver.winner} onRestart={handleRestart} />
      </div>
    );
  }

  if (!gameState) {
    return (
      <div className="app full-screen">
        <StartScreen onStartGame={handleStartGame} isLoading={isLoading} />
      </div>
    );
  }

  const showActionPanel = gameState.pending_action && gameState.status === 'en_cours';
  const isSelectableMode = ['wolf_vote', 'seer_check', 'day_vote'].includes(gameState.pending_action || '');
  const isNight = gameState.phase === 'nuit';
  const showVoteButtons = ['wolf_vote', 'seer_check', 'day_vote'].includes(gameState.pending_action || '');

  return (
    <div className="app-container">
      {/* Night overlay */}
      {isNight && <div className="night-overlay-game" />}

      {/* Header */}
      <header className="app-header">
        <h1 className="app-title">Loup-Garou</h1>
        <PhaseIndicator phase={gameState.phase} dayNumber={gameState.day_number} />
      </header>

      {/* Main game area */}
      <div className="app-main">
        {/* Left panel - Village display */}
        <main className="village-display">
          <div className="village-section">
            <h2 className="village-title">
              <span>⚜</span> Le Village <span>⚜</span>
            </h2>
            <p className="village-count">
              {gameState.players.filter(p => p.is_alive).length} villageois en vie
            </p>
          </div>

          {/* Players grid */}
          <div className="players-grid">
            {gameState.players.map((player) => (
              <PlayerCard
                key={player.name}
                player={player}
                showVote={showVoteButtons}
                onVote={() => {
                  setSelectedTarget(player.name);
                }}
                isNight={isNight}
                isSelected={selectedTarget === player.name}
                isSelectable={isSelectableMode && player.is_alive && !player.is_human}
                isWolfAlly={fellowWolves.includes(player.name)}
              />
            ))}
          </div>

          {/* Action hint */}
          {gameState.pending_action && (
            <div className="action-hint">
              <div className="action-hint-content">
                {gameState.pending_action === 'day_vote' && (
                  <span>🗳️ Choisissez qui éliminer...</span>
                )}
                {gameState.pending_action === 'human_discussion' && (
                  <span>💬 C'est à vous de parler dans la Chronique</span>
                )}
                {gameState.pending_action === 'wolf_vote' && (
                  <span>🐺 Choisissez votre victime...</span>
                )}
                {gameState.pending_action === 'seer_check' && (
                  <span>👁️ Choisissez quelqu'un à examiner...</span>
                )}
                {gameState.pending_action === 'witch_choice' && (
                  <span>🧙 Utilisez vos potions...</span>
                )}
                {gameState.pending_action === 'wait_night' && (
                  <span>🌙 Les loups rôdent...</span>
                )}
              </div>
            </div>
          )}
        </main>

        {/* Right panel - Chat */}
        <ChatPanel
          discussions={discussions}
          pendingAction={gameState.pending_action}
          humanPlayerName={gameState.players.find(p => p.is_human)?.name || 'Joueur'}
          onSendMessage={handleSendMessage}
        />
      </div>

      {/* Action panel */}
      {showActionPanel && gameState.players.find(p => p.is_human && !p.is_alive) ? (
        <div className="action-panel spectator-panel">
          <div className="action-title">⚰️ Vous êtes mort</div>
          <div className="action-description">
            {gameState.pending_action === 'auto_night'
              ? 'Les autres joueurs agissent durant la nuit...'
              : gameState.pending_action === 'auto_day'
              ? 'Les autres joueurs votent...'
              : 'En attente du prochain événement...'}
          </div>
          <div className="spectator-info">
            {isLoading ? '⏳ Traitement en cours...' : 'Vous observez le jeu en tant que spectateur'}
          </div>
        </div>
      ) : showActionPanel ? (
        <ActionPanel
          pendingAction={gameState.pending_action}
          yourRole={yourRole}
          selectedTarget={selectedTarget}
          onAction={handleAction}
          onSkip={handleWitchSkip}
          wolfVictim={witchInfo.victim}
          hasLifePotion={witchInfo.hasLife}
          hasDeathPotion={witchInfo.hasDeath}
          onWitchSave={handleWitchSave}
          onWitchKill={handleWitchKill}
          isLoading={isLoading}
        />
      ) : null}

    </div>
  );
}

export default App;