import type { GameState, CreateGameResponse, ActionResult, Discussion } from './types';

const API_BASE = 'http://localhost:8000/api/v1';

export async function setAnthropicKey(apiKey: string): Promise<{ success: boolean }> {
  const response = await fetch(`${API_BASE}/config/anthropic`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!response.ok) throw new Error('Failed to set API key');
  return response.json();
}

export async function createGame(
  playerName: string,
  numPlayers = 6,
  numWolves = 2
): Promise<CreateGameResponse> {
  const response = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      player_name: playerName,
      num_players: numPlayers,
      num_wolves: numWolves,
      include_seer: true,
      include_witch: true,
    }),
  });
  if (!response.ok) throw new Error('Failed to create game');
  return response.json();
}

export async function getGameState(gameId: string): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games/${gameId}`);
  if (!response.ok) throw new Error('Failed to get game state');
  return response.json();
}

export async function sendAction(
  gameId: string,
  action: string,
  target?: string,
  save?: boolean,
  kill?: string
): Promise<ActionResult> {
  const response = await fetch(`${API_BASE}/games/${gameId}/actions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, target, save, kill }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send action');
  }
  return response.json();
}

export async function getDiscussions(gameId: string): Promise<Discussion[]> {
  const response = await fetch(`${API_BASE}/games/${gameId}/discussions`);
  if (!response.ok) throw new Error('Failed to get discussions');
  const data = await response.json();
  return data.discussions;
}
