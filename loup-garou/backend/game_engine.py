"""
Moteur de jeu du Loup-Garou avec agents IA OpenAI
"""
import asyncio
import random
from typing import Optional
from collections import Counter
import json
import re

from .models import (
    GameState, Player, Role, Phase, GameStatus,
    WitchPotions, NightActions, VoteResult
)
from .ai_players import AIAgent, AIPersonality, assign_personalities, AI_PERSONALITIES


class GameEngine:
    """Gère la logique du jeu du Loup-Garou"""

    def __init__(self):
        self.games: dict[str, GameState] = {}
        self.ai_agents: dict[str, dict[str, AIAgent]] = {}  # game_id -> {player_name -> agent}
        self.personalities: dict[str, dict[str, AIPersonality]] = {}
        self.discussions_cache: dict[str, list[dict]] = {}  # game_id -> discussions
        self.discussion_state: dict[str, dict] = {}  # game_id -> {order: list, current_index: int, completed: bool}

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

    async def process_human_action_async(self, game_id: str, action: dict) -> dict:
        """Traite une action du joueur humain (version async)"""
        game = self.get_game(game_id)
        if not game:
            return {"error": "Partie non trouvée"}

        if game.status != GameStatus.EN_COURS:
            return {"error": "La partie est terminée"}

        human = next((p for p in game.players if p.is_human), None)

        # Permettre l'action "skip_day_vote" même si le joueur est mort
        if not human or (not human.is_alive and action.get("action") != "skip_day_vote"):
            return {"error": "Vous êtes mort"}

        if game.phase == Phase.NUIT:
            return await self._process_night_action_async(game, human, action)
        else:
            return await self._process_day_action_async(game, human, action)

    def process_human_action(self, game_id: str, action: dict) -> dict:
        """Traite une action du joueur humain (wrapper sync)"""
        return asyncio.get_event_loop().run_until_complete(
            self.process_human_action_async(game_id, action)
        )

    async def _process_night_action_async(self, game: GameState, human: Player, action: dict) -> dict:
        """Traite une action nocturne"""
        action_type = action.get("action")
        result = {"success": True, "messages": [], "wolf_discussions": []}

        if human.role == Role.LOUP_GAROU and action_type == "wolf_vote":
            target_name = action.get("target")
            target = game.get_player(target_name)

            if not target or not target.is_alive:
                return {"error": "Cible invalide"}
            if target.role == Role.LOUP_GAROU:
                return {"error": "Vous ne pouvez pas attaquer un autre loup"}

            # Générer les discussions des autres loups IA
            wolf_discussions = await self._generate_wolf_discussions(game, target_name)
            result["wolf_discussions"] = wolf_discussions

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
        await self._execute_ai_night_actions_async(game)
        night_result = self._resolve_night(game)
        result["night_events"] = night_result

        # Mettre à jour la mémoire des agents avec les morts
        for death in night_result.get("deaths", []):
            for agent in self.ai_agents.get(game.game_id, {}).values():
                agent.update_memory("death", death)

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
            # Toujours mettre pending_action à day_vote (mort ou vivant)
            # Le frontend déterminera si le joueur peut voter ou doit passer son tour
            game.pending_action = "day_vote"
            # Réinitialiser le cache des discussions
            self.discussions_cache[game.game_id] = []

        return result

    async def _generate_wolf_discussions(self, game: GameState, human_target: str) -> list[dict]:
        """Génère les réponses des autres loups IA au choix de l'humain"""
        discussions = []
        agents = self.ai_agents.get(game.game_id, {})

        for player in game.get_wolves():
            if not player.is_human and player.is_alive:
                agent = agents.get(player.name)
                if agent:
                    fellow_wolves = [p.name for p in game.get_wolves() if p.name != player.name]
                    # Générer une réaction au choix
                    try:
                        vote_result = await agent.generate_wolf_vote(fellow_wolves)
                        message = f"Je suis d'accord pour {human_target}." if vote_result.get("target") == human_target else f"Je préférerais {vote_result.get('target')}, mais je te suis."
                        discussions.append({
                            "player": player.name,
                            "message": message,
                            "vote": vote_result.get("target")
                        })
                    except Exception:
                        discussions.append({
                            "player": player.name,
                            "message": "D'accord, allons-y.",
                            "vote": human_target
                        })

        return discussions

    async def _execute_ai_night_actions_async(self, game: GameState):
        """Exécute les actions nocturnes des IA"""
        agents = self.ai_agents.get(game.game_id, {})

        # Actions des loups IA (si pas déjà votée par humain loup)
        if not game.night_actions.wolf_victim:
            wolf_votes = []
            for player in game.get_wolves():
                if not player.is_human and player.is_alive:
                    agent = agents.get(player.name)
                    if agent:
                        fellow_wolves = [p.name for p in game.get_wolves() if p.name != player.name]
                        vote_result = await agent.generate_wolf_vote(fellow_wolves)
                        if vote_result.get("target"):
                            wolf_votes.append(vote_result["target"])

            if wolf_votes:
                vote_count = Counter(wolf_votes)
                game.night_actions.wolf_victim = vote_count.most_common(1)[0][0]

        # Action de la voyante IA
        seer = next((p for p in game.players if p.role == Role.VOYANTE and p.is_alive and not p.is_human), None)
        if seer and not game.night_actions.seer_target:
            agent = agents.get(seer.name)
            if agent:
                choice = await agent.generate_seer_choice()
                target_name = choice.get("target")
                target = game.get_player(target_name)
                if target:
                    game.night_actions.seer_target = target.name
                    game.night_actions.seer_result = target.role.display_name
                    # L'agent mémorise le rôle découvert
                    agent.update_memory("role_revealed", {"player": target.name, "role": target.role.display_name})

        # Action de la sorcière IA
        witch = next((p for p in game.players if p.role == Role.SORCIERE and p.is_alive and not p.is_human), None)
        if witch:
            agent = agents.get(witch.name)
            if agent:
                choice = await agent.generate_witch_choice(
                    game.night_actions.wolf_victim,
                    game.witch_potions.has_life_potion,
                    game.witch_potions.has_death_potion
                )
                if choice.get("save") and game.witch_potions.has_life_potion:
                    game.night_actions.witch_save = True
                    game.witch_potions.has_life_potion = False
                if choice.get("kill") and game.witch_potions.has_death_potion:
                    game.night_actions.witch_kill = choice["kill"]
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

    async def _process_day_action_async(self, game: GameState, human: Player, action: dict) -> dict:
        """Traite une action de jour"""
        action_type = action.get("action")
        result = {"success": True, "messages": []}

        if action_type == "skip_day_vote":
            # Le joueur humain est mort, les IA votent seules
            votes = {}
        elif action_type == "day_vote":
            target_name = action.get("target")

            # Collecter les votes
            votes = {human.name: target_name}

            # Récupérer les discussions pour contexte
            discussions = self.discussions_cache.get(game.game_id, [])

            # Générer les votes IA
            agents = self.ai_agents.get(game.game_id, {})
            for player in game.get_alive_players():
                if not player.is_human:
                    agent = agents.get(player.name)
                    if agent:
                        vote_result = await agent.generate_vote(discussions)
                        if vote_result.get("vote"):
                            votes[player.name] = vote_result["vote"]
                            # Mettre à jour la mémoire
                            agent.update_memory("vote", {"voter": player.name, "target": vote_result["vote"]})

            # Compter les votes
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
                        # Mettre à jour la mémoire des agents
                        for agent in agents.values():
                            agent.update_memory("death", {
                                "name": eliminated_name,
                                "role": eliminated.role.display_name,
                                "cause": "vote"
                            })
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

    async def generate_ai_discussion_async(self, game_id: str) -> list[dict]:
        """Génère les discussions des joueurs IA pendant le jour"""
        game = self.get_game(game_id)
        if not game or game.phase != Phase.JOUR:
            return []

        agents = self.ai_agents.get(game_id, {})
        existing_discussions = self.discussions_cache.get(game_id, [])

        # Initialiser l'ordre de passage si ce n'est pas déjà fait
        if game_id not in self.discussion_state or self.discussion_state[game_id].get("completed", False):
            alive_players = game.get_alive_players()
            random.shuffle(alive_players)  # Ordre aléatoire
            self.discussion_state[game_id] = {
                "order": [p.name for p in alive_players],
                "current_index": 0,
                "completed": False
            }
            print(f"Ordre de discussion : {self.discussion_state[game_id]['order']}")

        state = self.discussion_state[game_id]
        discussions = []

        # Faire parler les joueurs dans l'ordre jusqu'à rencontrer l'humain ou finir
        while state["current_index"] < len(state["order"]):
            current_player_name = state["order"][state["current_index"]]
            current_player = game.get_player(current_player_name)

            if not current_player or not current_player.is_alive:
                # Joueur mort entre temps, passer au suivant
                state["current_index"] += 1
                continue

            # Si c'est le tour de l'humain, mettre à jour pending_action et attendre
            if current_player.is_human:
                game.pending_action = "human_discussion"
                print(f"C'est au tour de {current_player_name} (humain) de parler")
                break

            # Faire parler l'IA
            agent = agents.get(current_player_name)
            if agent:
                message = await agent.generate_discussion(existing_discussions)
                data = json.loads(format_json(message))
                nom_agent_2 = data.get("name", "")
                message_texte = data.get("content", "")

                discussion = {
                    "player": current_player_name,
                    "message": message_texte,
                }
                discussions.append(discussion)
                existing_discussions.append(discussion)
                print(f"{current_player_name} : {message_texte}")

                # Si l'IA cible quelqu'un, gérer la réponse
                if nom_agent_2:
                    print(f"je veux viser {nom_agent_2}")
                    print("="*100)
                    print(message)
                    print("="*100)

                    target_player = game.get_player(nom_agent_2)
                    if target_player and target_player.is_alive:
                        # Si la cible est l'humain, l'humain répondra à son tour
                        if not target_player.is_human:
                            agent_2 = agents.get(nom_agent_2)
                            if agent_2:
                                message_2 = await agent_2.generate_discussion(existing_discussions)
                                data2 = json.loads(format_json(message_2))
                                message_texte_2 = data2.get("content", "")

                                discussion_2 = {
                                    "player": nom_agent_2,
                                    "message": message_texte_2,
                                }
                                discussions.append(discussion_2)
                                existing_discussions.append(discussion_2)
                                print(f"Réponse de {nom_agent_2} à {current_player_name} : {message_texte_2}")

            state["current_index"] += 1

        # Vérifier si tous les joueurs ont parlé
        if state["current_index"] >= len(state["order"]):
            state["completed"] = True
            game.pending_action = "day_vote"  # Passer au vote
            print("Tous les joueurs ont parlé, passage au vote")

        # Mettre en cache
        self.discussions_cache[game_id] = existing_discussions

        return discussions

    def generate_ai_discussion(self, game_id: str) -> list[dict]:
        """Génère les discussions (wrapper sync)"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.generate_ai_discussion_async(game_id))

    async def send_human_message_async(self, game_id: str, message: str) -> dict:
        """Traite le message du joueur humain pendant les discussions"""
        game = self.get_game(game_id)
        if not game:
            return {"error": "Partie non trouvée"}

        if game.phase != Phase.JOUR:
            return {"error": "Pas en phase de jour"}

        human = next((p for p in game.players if p.is_human), None)
        if not human or not human.is_alive:
            return {"error": "Joueur humain non trouvé ou mort"}

        # Vérifier que c'est bien le tour de l'humain
        if game.pending_action != "human_discussion":
            return {"error": "Ce n'est pas votre tour de parler"}

        existing_discussions = self.discussions_cache.get(game_id, [])

        # Ajouter le message de l'humain
        discussion = {
            "player": human.name,
            "message": message,
        }
        existing_discussions.append(discussion)
        self.discussions_cache[game_id] = existing_discussions
        print(f"{human.name} (humain) : {message}")

        # Passer au joueur suivant dans l'ordre
        state = self.discussion_state.get(game_id)
        if state:
            state["current_index"] += 1

        # Continuer les discussions avec les IA restantes
        new_discussions = await self.generate_ai_discussion_async(game_id)

        return {
            "success": True,
            "message": "Message envoyé",
            "discussions": new_discussions
        }

    def send_human_message(self, game_id: str, message: str) -> dict:
        """Wrapper sync pour send_human_message_async"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.send_human_message_async(game_id, message))

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
def format_json(chaine_sale):
    try:
        propre = re.sub(r'```(?:json)?|```', '', chaine_sale).strip()
        if propre.startswith("json"):
            propre = propre[4:].strip()
        donnees = json.loads(propre)
        return json.dumps(donnees, indent=4, ensure_ascii=False)

    except Exception as e:
        return f"Erreur de formatage : {e}"