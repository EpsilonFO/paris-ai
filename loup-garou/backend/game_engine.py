"""
Moteur de jeu du Loup-Garou
"""
import random
from typing import Optional
from .models import (
    GameState, Player, Role, Phase, GameStatus,
    WitchPotions, NightActions, VoteResult
)
from .ai_players import AIBrain, AIPersonality, assign_personalities, AI_PERSONALITIES


class GameEngine:
    """Gère la logique du jeu du Loup-Garou"""

    def __init__(self):
        self.games: dict[str, GameState] = {}
        self.ai_brains: dict[str, dict[str, AIBrain]] = {}  # game_id -> {player_name -> brain}
        self.personalities: dict[str, dict[str, AIPersonality]] = {}

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

        # Créer les cerveaux IA
        self._init_ai_brains(game)

        # Log de création
        game.history.append({
            "type": "game_start",
            "day": 1,
            "players": [p.name for p in players],
            "human_role": human_role.display_name
        })

        return game

    def _init_ai_brains(self, game: GameState):
        """Initialise les cerveaux IA pour tous les joueurs non-humains"""
        self.ai_brains[game.game_id] = {}
        for player in game.players:
            if not player.is_human:
                personality = self.personalities[game.game_id].get(player.name)
                if personality:
                    self.ai_brains[game.game_id][player.name] = AIBrain(
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

    def process_human_action(self, game_id: str, action: dict) -> dict:
        """Traite une action du joueur humain"""
        game = self.get_game(game_id)
        if not game:
            return {"error": "Partie non trouvée"}

        if game.status != GameStatus.EN_COURS:
            return {"error": "La partie est terminée"}

        human = next((p for p in game.players if p.is_human), None)
        if not human or not human.is_alive:
            return {"error": "Vous êtes mort"}

        action_type = action.get("action")

        if game.phase == Phase.NUIT:
            return self._process_night_action(game, human, action)
        else:
            return self._process_day_action(game, human, action)

    def _process_night_action(self, game: GameState, human: Player, action: dict) -> dict:
        """Traite une action nocturne"""
        action_type = action.get("action")
        result = {"success": True, "messages": []}

        if human.role == Role.LOUP_GAROU and action_type == "wolf_vote":
            target_name = action.get("target")
            target = game.get_player(target_name)

            if not target or not target.is_alive:
                return {"error": "Cible invalide"}
            if target.role == Role.LOUP_GAROU:
                return {"error": "Vous ne pouvez pas attaquer un autre loup"}

            game.night_actions.wolf_victim = target_name
            result["messages"].append(f"Les loups ont choisi {target_name} comme victime.")

        elif human.role == Role.VOYANTE and action_type == "seer_check":
            target_name = action.get("target")
            target = game.get_player(target_name)

            if not target or not target.is_alive:
                return {"error": "Cible invalide"}

            game.night_actions.seer_target = target_name
            game.night_actions.seer_result = target.role.display_name
            result["messages"].append(f"Vous découvrez que {target_name} est {target.role.display_name}.")
            result["seer_result"] = {
                "target": target_name,
                "role": target.role.display_name,
                "is_wolf": target.role == Role.LOUP_GAROU
            }

        elif human.role == Role.SORCIERE and action_type == "witch_choice":
            if action.get("save") and game.witch_potions.has_life_potion:
                game.night_actions.witch_save = True
                game.witch_potions.has_life_potion = False
                result["messages"].append("Vous utilisez votre potion de vie.")

            if action.get("kill"):
                kill_target = action.get("kill")
                target = game.get_player(kill_target)
                if target and target.is_alive and game.witch_potions.has_death_potion:
                    game.night_actions.witch_kill = kill_target
                    game.witch_potions.has_death_potion = False
                    result["messages"].append(f"Vous utilisez votre potion de mort sur {kill_target}.")

        elif action_type == "wait_night":
            result["messages"].append("Vous attendez que la nuit passe...")

        # Exécuter les actions IA et résoudre la nuit
        self._execute_ai_night_actions(game)
        night_result = self._resolve_night(game)
        result["night_events"] = night_result

        # Vérifier la victoire
        victory = game.check_victory()
        if victory:
            game.status = victory
            result["game_over"] = {
                "winner": "Village" if victory == GameStatus.VICTOIRE_VILLAGE else "Loups-Garous",
                "status": victory.value
            }
        else:
            # Passer au jour
            game.phase = Phase.JOUR
            game.pending_action = "day_vote" if human.is_alive else None

        return result

    def _execute_ai_night_actions(self, game: GameState):
        """Exécute les actions nocturnes des IA"""
        brains = self.ai_brains.get(game.game_id, {})

        # Actions des loups IA (si pas déjà votée par humain loup)
        if not game.night_actions.wolf_victim:
            wolf_votes = []
            for player in game.get_wolves():
                if not player.is_human:
                    brain = brains.get(player.name)
                    if brain:
                        action = brain.generate_night_action()
                        if action and action.get("target"):
                            wolf_votes.append(action["target"])

            if wolf_votes:
                # Vote majoritaire des loups
                from collections import Counter
                vote_count = Counter(wolf_votes)
                game.night_actions.wolf_victim = vote_count.most_common(1)[0][0]

        # Action de la voyante IA
        seer = next((p for p in game.players if p.role == Role.VOYANTE and p.is_alive and not p.is_human), None)
        if seer and not game.night_actions.seer_target:
            brain = brains.get(seer.name)
            if brain:
                action = brain.generate_night_action()
                if action:
                    target = game.get_player(action["target"])
                    if target:
                        game.night_actions.seer_target = target.name
                        game.night_actions.seer_result = target.role.display_name

        # Action de la sorcière IA
        witch = next((p for p in game.players if p.role == Role.SORCIERE and p.is_alive and not p.is_human), None)
        if witch:
            brain = brains.get(witch.name)
            if brain:
                action = brain.generate_night_action()
                if action:
                    if action.get("save") and game.witch_potions.has_life_potion:
                        game.night_actions.witch_save = True
                        game.witch_potions.has_life_potion = False
                    if action.get("kill") and game.witch_potions.has_death_potion:
                        game.night_actions.witch_kill = action["kill"]
                        game.witch_potions.has_death_potion = False

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

    def _process_day_action(self, game: GameState, human: Player, action: dict) -> dict:
        """Traite une action de jour"""
        action_type = action.get("action")
        result = {"success": True, "messages": []}

        if action_type == "day_vote":
            target_name = action.get("target")

            # Collecter les votes
            votes = {human.name: target_name}

            # Générer les votes IA
            brains = self.ai_brains.get(game.game_id, {})
            for player in game.get_alive_players():
                if not player.is_human:
                    brain = brains.get(player.name)
                    if brain:
                        vote = brain.generate_vote()
                        if vote.get("vote"):
                            votes[player.name] = vote["vote"]

            # Compter les votes
            from collections import Counter
            vote_counts = Counter(votes.values())
            result["votes"] = dict(votes)
            result["vote_counts"] = dict(vote_counts)

            # Déterminer le résultat
            if vote_counts:
                max_votes = max(vote_counts.values())
                top_voted = [name for name, count in vote_counts.items() if count == max_votes]

                if len(top_voted) == 1:
                    eliminated_name = top_voted[0]
                    eliminated = game.get_player(eliminated_name)
                    if eliminated:
                        eliminated.is_alive = False
                        result["eliminated"] = {
                            "name": eliminated_name,
                            "role": eliminated.role.display_name,
                            "votes": max_votes
                        }
                        result["messages"].append(
                            f"{eliminated_name} a été éliminé avec {max_votes} votes. "
                            f"C'était un(e) {eliminated.role.display_name}."
                        )
                else:
                    result["tie"] = True
                    result["messages"].append(
                        f"Égalité entre {', '.join(top_voted)}. Personne n'est éliminé."
                    )

            # Log
            game.history.append({
                "type": "day_vote",
                "day": game.day_number,
                "votes": votes,
                "result": result.get("eliminated") or {"tie": True}
            })

            # Vérifier la victoire
            victory = game.check_victory()
            if victory:
                game.status = victory
                result["game_over"] = {
                    "winner": "Village" if victory == GameStatus.VICTOIRE_VILLAGE else "Loups-Garous",
                    "status": victory.value
                }
            else:
                # Passer à la nuit suivante
                game.day_number += 1
                game.phase = Phase.NUIT
                human_player = next((p for p in game.players if p.is_human), None)
                if human_player and human_player.is_alive:
                    game.pending_action = self._get_pending_action(
                        game.players, Phase.NUIT, human_player.role
                    )
                else:
                    game.pending_action = None

        return result

    def generate_ai_discussion(self, game_id: str) -> list[dict]:
        """Génère les discussions des joueurs IA pendant le jour"""
        game = self.get_game(game_id)
        if not game or game.phase != Phase.JOUR:
            return []

        discussions = []
        brains = self.ai_brains.get(game_id, {})

        for player in game.get_alive_players():
            if not player.is_human:
                brain = brains.get(player.name)
                if brain:
                    message = brain.generate_discussion([])
                    personality = self.personalities[game_id].get(player.name)
                    discussions.append({
                        "player": player.name,
                        "message": message,
                        "personality": personality.description if personality else None
                    })

        return discussions

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
