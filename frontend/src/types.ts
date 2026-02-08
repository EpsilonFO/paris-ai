export interface Player {
  name: string;
  is_alive: boolean;
  is_human: boolean;
  role?: string;
  personality?: string;
  voice_id?: string;
}

export interface GameState {
  game_id: string;
  phase: 'nuit' | 'jour';
  day_number: number;
  status: 'en_cours' | 'victoire_village' | 'victoire_loups';
  players: Player[];
  alive_count: number;
  pending_action: string | null;
}

export interface Discussion {
  player: string;
  message: string;
  personality?: string;
}

export interface CreateGameResponse {
  game_id: string;
  your_role: string;
  your_faction: string;
  players: Player[];
  message: string;
  fellow_wolves?: string[];
}

export interface ActionResult {
  success: boolean;
  messages: string[];
  night_events?: {
    deaths: Array<{ name: string; role: string; cause: string }>;
    saved: string | null;
  };
  votes?: Record<string, string>;
  vote_counts?: Record<string, number>;
  eliminated?: { name: string; role: string; votes: number };
  tie?: boolean;
  seer_result?: { target: string; role: string; is_wolf: boolean };
  witch_victim?: string;
  game_over?: { winner: string; status: string };
}
