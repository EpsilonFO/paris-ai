"""
Moteur de jeu du Loup-Garou avec agents IA OpenAI
"""
import asyncio
import random
from typing import Optional
from collections import Counter

from .models import (
    GameState, Player, Role, Phase, GameStatus,
    WitchPotions, NightActions, VoteResult,
    DiscussionState, DiscussionMessage
)
from .ai_players import AIAgent, AIPersonality, assign_personalities, AI_PERSONALITIES


class GameEngine:
    """Gère la logique du jeu du Loup-Garou"""

    def __init__(self):
        self.games: dict[str, GameState] = {}
        self.ai_agents: dict[str, dict[str, AIAgent]] = {}  # game_id -> {player_name -> agent}
        self.personalities: dict[str, dict[str, AIPersonality]] = {}
        self.discussions_cache: dict[str, list[dict]] = {}  # game_id -> discussions

    def create_game(
        self,
        human_name: str,
        num_players: int = 6,
        num_wolves: int = 2,
        include_seer: bool = True,
        include_witch: bool = True
    ) -> GameState:
        """Crée une nouvelle partie"""
        game_id = GameState.generate_id()

        # Créer la liste des rôles
        roles = [Role.LOUP_GAROU] * num_wolves

        if include_seer:
            roles.append(Role.VOYANTE)
        if include_witch:
            roles.append(Role.SORCIERE)

        # Compléter avec des villageois
        while len(roles) < num_players:
            roles.append(Role.VILLAGEOIS)

        random.shuffle(roles)

        # Créer les joueurs
        players = []
        human_role = roles.pop()
        players.append(Player(
            name=human_name,
            role=human_role,
            is_human=True
        ))

        # Créer les joueurs IA
        for role in roles:
            players.append(Player(
                name=f"IA_{len(players)}",  # Nom temporaire
                role=role,
                is_human=False
            ))

        # Assigner les personnalités (renomme les joueurs IA)
        self.personalities[game_id] = assign_personalities(players)

        # Créer l'état du jeu
        game = GameState(
            game_id=game_id,
            players=players,
            phase=Phase.NUIT,
            day_number=1,
            status=GameStatus.EN_COURS,
            witch_potions=WitchPotions(),
            night_actions=NightActions(),
            history=[],
            pending_action=self._get_pending_action(players, Phase.NUIT, human_role)
        )

        self.games[game_id] = game
        self.discussions_cache[game_id] = []

        # Créer les agents IA
        self._init_ai_agents(game)

        # Log de création
        game.history.append({
            "type": "game_start",
            "day": 1,
            "players": [p.name for p in players],
            "human_role": human_role.display_name
        })

        return game

    def _init_ai_agents(self, game: GameState):
        """Initialise les agents IA pour tous les joueurs non-humains"""
        self.ai_agents[game.game_id] = {}
        for player in game.players:
            if not player.is_human:
                personality = self.personalities[game.game_id].get(player.name)
                if personality:
                    self.ai_agents[game.game_id][player.name] = AIAgent(
                        player, personality, game
                    )

    def _get_pending_action(self, players: list[Player], phase: Phase, human_role: Role) -> Optional[str]:
        """Détermine l'action en attente pour le joueur humain"""
        human = next((p for p in players if p.is_human), None)
        if not human or not human.is_alive:
            return None

        if phase == Phase.NUIT:
            if human_role == Role.LOUP_GAROU:
                return "wolf_vote"
            elif human_role == Role.VOYANTE:
                return "seer_check"
            elif human_role == Role.SORCIERE:
                return "witch_choice"
            else:
                return "wait_night"  # Les villageois attendent
        else:
            return "day_vote"

    def get_game(self, game_id: str) -> Optional[GameState]:
        """Récupère une partie par son ID"""
        return self.games.get(game_id)

    def _resolve_night(self, game: GameState) -> dict:
        """Résout les événements de la nuit"""
        events = {"deaths": [], "saved": None}

        # Victime des loups
        victim_name = game.night_actions.wolf_victim
        if victim_name:
            if game.night_actions.witch_save:
                events["saved"] = victim_name
            else:
                victim = game.get_player(victim_name)
                if victim:
                    victim.is_alive = False
                    events["deaths"].append({
                        "name": victim_name,
                        "role": victim.role.display_name,
                        "cause": "loups"
                    })

        # Victime de la sorcière
        witch_kill = game.night_actions.witch_kill
        if witch_kill:
            target = game.get_player(witch_kill)
            if target and target.is_alive:
                target.is_alive = False
                events["deaths"].append({
                    "name": witch_kill,
                    "role": target.role.display_name,
                    "cause": "sorcière"
                })

        # Log dans l'historique
        game.history.append({
            "type": "night_end",
            "day": game.day_number,
            "events": events
        })

        # Reset des actions nocturnes
        game.night_actions = NightActions()

        return events



    def get_game_summary(self, game_id: str, player_name: str) -> dict:
        """Génère un résumé de l'état du jeu pour un joueur"""
        game = self.get_game(game_id)
        if not game:
            return {"error": "Partie non trouvée"}

        player = game.get_player(player_name)
        if not player:
            return {"error": "Joueur non trouvé"}

        summary = game.to_dict(player_perspective=player_name)

        # Ajouter les informations spécifiques au joueur
        summary["your_role"] = player.role.display_name
        summary["your_faction"] = player.role.faction.value
        summary["you_are_alive"] = player.is_alive

        # Si loup, montrer les autres loups
        if player.role == Role.LOUP_GAROU:
            other_wolves = [p.name for p in game.get_wolves() if p.name != player_name]
            summary["fellow_wolves"] = other_wolves

        # Informations sur les potions de la sorcière
        if player.role == Role.SORCIERE:
            summary["potions"] = {
                "life": game.witch_potions.has_life_potion,
                "death": game.witch_potions.has_death_potion
            }
            if game.phase == Phase.NUIT and game.night_actions.wolf_victim:
                summary["wolf_victim"] = game.night_actions.wolf_victim

        return summary


# Instance globale du moteur
engine = GameEngine()
