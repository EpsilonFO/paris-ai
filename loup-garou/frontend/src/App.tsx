import { useState, useCallback, useEffect } from 'react';
import type { GameState, Discussion, CreateGameResponse, ActionResult } from './types';
import { createGame, getGameState, sendAction, getDiscussions } from './api';
import { StartScreen } from './components/StartScreen';
import { GameBoard } from './components/GameBoard';
import { ActionPanel } from './components/ActionPanel';
import { EventLog } from './components/EventLog';
import { GameOver } from './components/GameOver';
import './App.css';

interface GameEvent {
  id: number;
  type: 'death' | 'saved' | 'vote' | 'info';
  message: string;
}

function App() {
  const [gameId, setGameId] = useState<string | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [yourRole, setYourRole] = useState<string>('');
  const [fellowWolves, setFellowWolves] = useState<string[]>([]);
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [events, setEvents] = useState<GameEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [gameOver, setGameOver] = useState<{ winner: string } | null>(null);

  const addEvent = useCallback((type: GameEvent['type'], message: string) => {
    setEvents((prev) => [...prev, { id: Date.now(), type, message }]);
  }, []);

  const handleStartGame = async (playerName: string, numPlayers: number, numWolves: number) => {
    setIsLoading(true);
    try {
      const response: CreateGameResponse = await createGame(playerName, numPlayers, numWolves);
      setGameId(response.game_id);
      setYourRole(response.your_role);
      setFellowWolves(response.fellow_wolves || []);

      addEvent('info', response.message);

      if (response.fellow_wolves?.length) {
        addEvent('info', `Vos allies loups: ${response.fellow_wolves.join(', ')}`);
      }

      const state = await getGameState(response.game_id);
      setGameState(state);
    } catch (error) {
      console.error('Failed to start game:', error);
      addEvent('info', 'Erreur: impossible de creer la partie');
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
        setIsLoading(false);
        return;
      }

      processActionResult(result);
      setSelectedTarget(null);

      const newState = await getGameState(gameId);
      setGameState(newState);

      if (newState.phase === 'jour' && newState.status === 'en_cours') {
        await loadDiscussions();
      } else {
        setDiscussions([]);
      }
    } catch (error) {
      console.error('Action failed:', error);
      addEvent('info', `Erreur: ${error instanceof Error ? error.message : 'action echouee'}`);
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

      const newState = await getGameState(gameId);
      setGameState(newState);

      if (newState.phase === 'jour') {
        await loadDiscussions();
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
      setSelectedTarget(null);

      const newState = await getGameState(gameId);
      setGameState(newState);

      if (newState.phase === 'jour') {
        await loadDiscussions();
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
        await loadDiscussions();
      }
    } catch (error) {
      console.error('Witch skip failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const processActionResult = (result: ActionResult) => {
    result.messages.forEach((msg) => addEvent('info', msg));

    if (result.seer_result) {
      const { target, role, is_wolf } = result.seer_result;
      addEvent(is_wolf ? 'death' : 'saved', `${target} est ${role}`);
    }

    if (result.night_events) {
      result.night_events.deaths.forEach((death) => {
        addEvent('death', `${death.name} (${death.role}) a ete tue par ${death.cause}`);
      });
      if (result.night_events.saved) {
        addEvent('saved', `${result.night_events.saved} a ete sauve par la sorciere`);
      }
    }

    if (result.eliminated) {
      addEvent('vote', `${result.eliminated.name} (${result.eliminated.role}) elimine avec ${result.eliminated.votes} votes`);
    }

    if (result.tie) {
      addEvent('vote', 'Egalite ! Personne n\'est elimine');
    }

    if (result.game_over) {
      setGameOver({ winner: result.game_over.winner });
    }
  };

  const loadDiscussions = async () => {
    if (!gameId) return;
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
  };

  const handleRestart = () => {
    setGameId(null);
    setGameState(null);
    setYourRole('');
    setFellowWolves([]);
    setDiscussions([]);
    setSelectedTarget(null);
    setEvents([]);
    setGameOver(null);
  };

  useEffect(() => {
    if (gameState?.phase === 'jour' && gameState.status === 'en_cours' && discussions.length === 0) {
      loadDiscussions();
    }
  }, [gameState?.phase]);

  if (gameOver) {
    return <GameOver winner={gameOver.winner} onRestart={handleRestart} />;
  }

  if (!gameState) {
    return <StartScreen onStartGame={handleStartGame} isLoading={isLoading} />;
  }

  // Extraire les infos de la sorcière du gameState
  const hasLifePotion = gameState.potions?.life ?? false;
  const hasDeathPotion = gameState.potions?.death ?? false;
  const wolfVictim = gameState.wolf_victim;

  const showActionPanel = gameState.pending_action && gameState.status === 'en_cours';
  const isSelectableMode = ['wolf_vote', 'seer_check', 'day_vote'].includes(gameState.pending_action || '');
  const isWitchSelectMode = gameState.pending_action === 'witch_choice' && hasDeathPotion;

  return (
    <div className="app">
      <GameBoard
        players={gameState.players}
        discussions={discussions}
        phase={gameState.phase}
        dayNumber={gameState.day_number}
        selectedPlayer={selectedTarget}
        selectableMode={isSelectableMode || isWitchSelectMode}
        onPlayerSelect={setSelectedTarget}
      />

      <EventLog events={events} />

      {showActionPanel && (
        <ActionPanel
          pendingAction={gameState.pending_action}
          yourRole={yourRole}
          selectedTarget={selectedTarget}
          onAction={handleAction}
          onSkip={handleWitchSkip}
          wolfVictim={wolfVictim}
          hasLifePotion={hasLifePotion}
          hasDeathPotion={hasDeathPotion}
          onWitchSave={handleWitchSave}
          onWitchKill={handleWitchKill}
          isLoading={isLoading}
        />
      )}

      {fellowWolves.length > 0 && (
        <div className="wolf-allies">
          Allies loups: {fellowWolves.join(', ')}
        </div>
      )}
    </div>
  );
}

export default App;
