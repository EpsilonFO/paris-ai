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

        # Si le joueur est mort, automatiser les actions
        if not human or not human.is_alive:
            if phase == Phase.NUIT:
                return "auto_night"  # Automatiser la nuit
            else:
                return "auto_day"  # Automatiser le jour

        if phase == Phase.NUIT:
            if human_role == Role.LOUP_GAROU:
                return "wolf_vote"
            elif human_role == Role.VOYANTE:
                return "seer_check"
            elif human_role == Role.SORCIERE:
                return "wait_night"  # La sorcière attend que les loups choisissent d'abord
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

        # Permettre les actions automatiques même si le joueur est mort
        auto_actions = {"skip_day_vote", "auto_night", "auto_day"}
        if not human or (not human.is_alive and action.get("action") not in auto_actions):
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
        print(f"\n[NIGHT_LOG] === DÉBUT traitement action nocturne: {action_type} pour {human.name} (jour {game.day_number}) ===")

        # Automatiser la nuit si le joueur est mort
        if action_type == "auto_night":
            print(f"[NIGHT_LOG] {human.name} est mort, automatisation complète de la nuit")
            result["messages"].append("Le joueur est mort. Les IA agissent automatiquement...")
            # Les IA exécutent leurs actions
            await self._execute_ai_night_actions_async(game)
            print(f"[NIGHT_LOG] Actions IA terminées, résolution de la nuit...")
            night_result = self._resolve_night(game)
            result["night_events"] = night_result
            print(f"[NIGHT_LOG] Nuit résolue. Événements: {night_result}")

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
                print(f"[NIGHT_LOG] FIN DE PARTIE: {result['game_over']['winner']} gagne")
            else:
                # Passer au jour
                game.phase = Phase.JOUR
                game.pending_action = "auto_day"
                print(f"[NIGHT_LOG] Passage au jour {game.day_number}")
                # Sauvegarder et réinitialiser le cache des discussions
                self._save_discussions_history(game)
                self.discussions_cache[game.game_id] = []

            print(f"[NIGHT_LOG] === FIN traitement auto_night ===\n")
            return result

        if human.role == Role.LOUP_GAROU and action_type == "wolf_vote":
            target_name = action.get("target")
            target = game.get_player(target_name)
            print(f"[NIGHT_LOG] Loup humain {human.name} vote pour {target_name}")

            if not target or not target.is_alive:
                print(f"[NIGHT_LOG] ERREUR: Cible invalide {target_name}")
                return {"error": "Cible invalide"}
            if target.role == Role.LOUP_GAROU:
                print(f"[NIGHT_LOG] ERREUR: {target_name} est un loup")
                return {"error": "Vous ne pouvez pas attaquer un autre loup"}

            # Générer les discussions des autres loups IA
            print(f"[NIGHT_LOG] Génération des discussions des loups IA...")
            wolf_discussions = await self._generate_wolf_discussions(game, target_name)
            result["wolf_discussions"] = wolf_discussions
            print(f"[NIGHT_LOG] Discussions des loups générées: {len(wolf_discussions)} messages")

            game.night_actions.wolf_victim = target_name
            result["messages"].append(f"Les loups ont choisi {target_name} comme victime.")

        elif human.role == Role.VOYANTE and action_type == "seer_check":
            target_name = action.get("target")
            target = game.get_player(target_name)
            print(f"[NIGHT_LOG] Voyante humaine {human.name} scrute {target_name}")

            if not target or not target.is_alive:
                print(f"[NIGHT_LOG] ERREUR: Cible invalide {target_name}")
                return {"error": "Cible invalide"}

            game.night_actions.seer_target = target_name
            game.night_actions.seer_result = target.role.display_name
            # Ajouter à la liste des découvertes permanentes de la voyante
            game.seer_discoveries[target_name] = target.role.display_name
            result["messages"].append(f"Vous découvrez que {target_name} est {target.role.display_name}.")
            result["seer_result"] = {
                "target": target_name,
                "role": target.role.display_name,
                "is_wolf": target.role == Role.LOUP_GAROU
            }
            print(f"[NIGHT_LOG] Résultat: {target_name} est {target.role.display_name}")

        elif human.role == Role.SORCIERE and action_type == "witch_choice":
            print(f"[NIGHT_LOG] Sorcière humaine {human.name} fait ses choix")
            if action.get("save") and game.witch_potions.has_life_potion:
                game.night_actions.witch_save = True
                game.witch_potions.has_life_potion = False
                result["messages"].append("Vous utilisez votre potion de vie.")
                print(f"[NIGHT_LOG] Sorcière sauve {game.night_actions.wolf_victim}")

            if action.get("kill"):
                kill_target = action.get("kill")
                target = game.get_player(kill_target)
                if target and target.is_alive and game.witch_potions.has_death_potion:
                    game.night_actions.witch_kill = kill_target
                    game.witch_potions.has_death_potion = False
                    result["messages"].append(f"Vous utilisez votre potion de mort sur {kill_target}.")
                    print(f"[NIGHT_LOG] Sorcière tue {kill_target}")

        elif action_type == "wait_night":
            print(f"[NIGHT_LOG] {human.name} attend que la nuit passe...")
            result["messages"].append("Vous attendez que la nuit passe...")

        # Exécuter les actions IA ET ATTENDRE QUE TOUS LES APPELS API SOIENT TERMINÉS
        print(f"[NIGHT_LOG] Avant actions IA - état nuit: wolf_victim={game.night_actions.wolf_victim}, seer_target={game.night_actions.seer_target}, witch_save={game.night_actions.witch_save}, witch_kill={game.night_actions.witch_kill}")
        await self._execute_ai_night_actions_async(game)
        print(f"[NIGHT_LOG] Après actions IA - état nuit: wolf_victim={game.night_actions.wolf_victim}, seer_target={game.night_actions.seer_target}, witch_save={game.night_actions.witch_save}, witch_kill={game.night_actions.witch_kill}")

        # Si la Sorcière est humaine et n'a pas encore choisi, l'arrêter ici et lui montrer la victime
        witch = next((p for p in game.players if p.role == Role.SORCIERE and p.is_alive and p.is_human), None)
        if witch and action_type != "witch_choice":
            print(f"[NIGHT_LOG] Sorcière humaine n'a pas encore choisi, mise en attente")
            # Afficher qui s'est fait manger
            if game.night_actions.wolf_victim:
                victim = game.get_player(game.night_actions.wolf_victim)
                if victim:
                    result["messages"].append(f"\n⚠️ {game.night_actions.wolf_victim} s'est fait attaquer par les loups!")
                    result["witch_victim"] = game.night_actions.wolf_victim

            # Mettre l'action en attente pour la Sorcière
            game.pending_action = "witch_choice"
            print(f"[NIGHT_LOG] === FIN traitement (witch_choice en attente) ===\n")
            return result

        print(f"[NIGHT_LOG] Résolution de la nuit...")
        night_result = self._resolve_night(game)
        result["night_events"] = night_result
        print(f"[NIGHT_LOG] Nuit résolue. Événements: {night_result}")

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
            print(f"[NIGHT_LOG] FIN DE PARTIE: {result['game_over']['winner']} gagne")
        else:
            # Passer au jour
            game.phase = Phase.JOUR
            # Toujours mettre pending_action à day_vote (mort ou vivant)
            # Le frontend déterminera si le joueur peut voter ou doit passer son tour
            game.pending_action = "day_vote"
            print(f"[NIGHT_LOG] Passage au jour {game.day_number}")
            # Sauvegarder et réinitialiser le cache des discussions
            self._save_discussions_history(game)
            self.discussions_cache[game.game_id] = []

        print(f"[NIGHT_LOG] === FIN traitement {action_type} ===\n")
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
        """Exécute les actions nocturnes des IA (loups et voyante seulement)"""
        print(f"\n[NIGHT_LOG] === Exécution des actions nocturnes IA pour le jour {game.day_number} ===")
        agents = self.ai_agents.get(game.game_id, {})

        # Actions des loups IA (si pas déjà votée par humain loup)
        if not game.night_actions.wolf_victim:
            print(f"[NIGHT_LOG] Aucune victime loup définie, générant les votes des loups IA...")
            wolf_votes = []
            wolf_tasks = []

            for player in game.get_wolves():
                if not player.is_human and player.is_alive:
                    agent = agents.get(player.name)
                    if agent:
                        fellow_wolves = [p.name for p in game.get_wolves() if p.name != player.name]
                        print(f"[NIGHT_LOG] Appel API pour {player.name} (loup IA) - autres loups: {fellow_wolves}")
                        wolf_tasks.append(agent.generate_wolf_vote(fellow_wolves))

            # Attendre TOUS les appels API en parallèle
            if wolf_tasks:
                print(f"[NIGHT_LOG] Attente de {len(wolf_tasks)} appels API pour les loups IA...")
                wolf_results = await asyncio.gather(*wolf_tasks, return_exceptions=True)

                for i, result in enumerate(wolf_results):
                    if isinstance(result, Exception):
                        print(f"[NIGHT_LOG] ERREUR pour loup IA {i}: {result}")
                    elif result.get("target"):
                        print(f"[NIGHT_LOG] Loup IA {i} vote pour {result.get('target')}")
                        wolf_votes.append(result["target"])

            if wolf_votes:
                vote_count = Counter(wolf_votes)
                game.night_actions.wolf_victim = vote_count.most_common(1)[0][0]
                print(f"[NIGHT_LOG] Victime des loups définie: {game.night_actions.wolf_victim} (votes: {dict(vote_count)})")
        else:
            print(f"[NIGHT_LOG] Victime loup déjà définie: {game.night_actions.wolf_victim}")

        # Action de la voyante IA (seulement si pas humain)
        seer = next((p for p in game.players if p.role == Role.VOYANTE and p.is_alive and not p.is_human), None)
        if seer and not game.night_actions.seer_target:
            print(f"[NIGHT_LOG] Appel API pour {seer.name} (voyante IA)...")
            agent = agents.get(seer.name)
            if agent:
                try:
                    choice = await agent.generate_seer_choice()
                    target_name = choice.get("target")
                    target = game.get_player(target_name)
                    if target:
                        game.night_actions.seer_target = target.name
                        game.night_actions.seer_result = target.role.display_name
                        # Ajouter à la liste des découvertes permanentes de la voyante
                        game.seer_discoveries[target.name] = target.role.display_name
                        print(f"[NIGHT_LOG] Voyante IA a choisi: {target.name} ({target.role.display_name})")
                        # L'agent mémorise le rôle découvert
                        agent.update_memory("role_revealed", {"player": target.name, "role": target.role.display_name})
                except Exception as e:
                    print(f"[NIGHT_LOG] ERREUR voyante IA: {e}")
        else:
            if seer:
                print(f"[NIGHT_LOG] Cible voyante IA déjà définie: {game.night_actions.seer_target}")
            else:
                print(f"[NIGHT_LOG] Pas de voyante IA en vie")

        # Action de la sorcière IA (seulement si pas humain ET pas de sorcière humaine)
        witch = next((p for p in game.players if p.role == Role.SORCIERE and p.is_alive and not p.is_human), None)
        if witch:
            print(f"[NIGHT_LOG] Appel API pour {witch.name} (sorcière IA)...")
            agent = agents.get(witch.name)
            if agent:
                try:
                    choice = await agent.generate_witch_choice(
                        game.night_actions.wolf_victim,
                        game.witch_potions.has_life_potion,
                        game.witch_potions.has_death_potion
                    )
                    if choice.get("save") and game.witch_potions.has_life_potion:
                        game.night_actions.witch_save = True
                        game.witch_potions.has_life_potion = False
                        print(f"[NIGHT_LOG] Sorcière IA sauve: {game.night_actions.wolf_victim}")
                    if choice.get("kill") and game.witch_potions.has_death_potion:
                        game.night_actions.witch_kill = choice["kill"]
                        game.witch_potions.has_death_potion = False
                        print(f"[NIGHT_LOG] Sorcière IA tue: {choice['kill']}")
                except Exception as e:
                    print(f"[NIGHT_LOG] ERREUR sorcière IA: {e}")
        else:
            print(f"[NIGHT_LOG] Pas de sorcière IA en vie")

        print(f"[NIGHT_LOG] === Fin des actions nocturnes IA ===")

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
                    # Ajouter à l'historique texte
                    game.history.append({
                        "type": "death",
                        "day": game.day_number,
                        "message": f"{victim_name} a été tué et était {victim.role.display_name}"
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
                # Ajouter à l'historique texte
                game.history.append({
                    "type": "death",
                    "day": game.day_number,
                    "message": f"{witch_kill} a été tué et était {target.role.display_name}"
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

    def _save_discussions_history(self, game: GameState):
        """Sauvegarde les discussions du jour courant dans l'historique"""
        discussions = self.discussions_cache.get(game.game_id, [])
        if discussions:
            game.discussions_history[game.day_number] = discussions

    async def _process_day_action_async(self, game: GameState, human: Player, action: dict) -> dict:
        """Traite une action de jour"""
        action_type = action.get("action")
        result = {"success": True, "messages": []}
        print(f"\n[DAY_LOG] === DÉBUT traitement action jour: {action_type} pour {human.name} (jour {game.day_number}) ===")

        # Automatiser le jour si le joueur est mort
        if action_type == "auto_day":
            print(f"[DAY_LOG] {human.name} est mort, automatisation complète du jour")
            result["messages"].append("Le joueur est mort. Les IA discutent et votent automatiquement...")

            # Générer les discussions IA même si le joueur est mort
            print(f"[DAY_LOG] Génération automatique des discussions...")
            await self.generate_ai_discussion_async(game.game_id)
            discussions = self.discussions_cache.get(game.game_id, [])
            print(f"[DAY_LOG] {len(discussions)} messages de discussion générés")

            votes = {}

            # Générer les votes IA en parallèle (après les discussions)
            agents = self.ai_agents.get(game.game_id, {})
            vote_tasks = []
            alive_ias = []

            for player in game.get_alive_players():
                if not player.is_human:
                    agent = agents.get(player.name)
                    if agent:
                        alive_ias.append(player.name)
                        vote_tasks.append(agent.generate_vote(discussions))

            # Attendre TOUS les appels API en parallèle
            if vote_tasks:
                print(f"[DAY_LOG] Génération des votes pour {len(vote_tasks)} IA en parallèle...")
                vote_results = await asyncio.gather(*vote_tasks, return_exceptions=True)

                for result_vote, ia_name in zip(vote_results, alive_ias):
                    if isinstance(result_vote, Exception):
                        print(f"[DAY_LOG] ERREUR pour {ia_name}: {result_vote}")
                    elif result_vote.get("vote"):
                        votes[ia_name] = result_vote["vote"]
                        print(f"[DAY_LOG] {ia_name} vote pour {result_vote['vote']}")
                        # Mettre à jour la mémoire
                        agents[ia_name].update_memory("vote", {"voter": ia_name, "target": result_vote["vote"]})

            # Compter les votes
            vote_counts = Counter(votes.values())
            result["votes"] = dict(votes)
            result["vote_counts"] = dict(vote_counts)
            print(f"[DAY_LOG] Votes comptés: {dict(vote_counts)}")

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
                        print(f"[DAY_LOG] {eliminated_name} éliminé ({eliminated.role.display_name})")
                        # Mettre à jour la mémoire des agents
                        for agent in agents.values():
                            agent.update_memory("death", {
                                "name": eliminated_name,
                                "role": eliminated.role.display_name,
                                "cause": "vote"
                            })
                        # Ajouter à l'historique texte
                        game.history.append({
                            "type": "death",
                            "day": game.day_number,
                            "message": f"{eliminated_name} a été éliminé et était {eliminated.role.display_name}"
                        })
                else:
                    result["tie"] = True
                    result["messages"].append(
                        f"Égalité entre {', '.join(top_voted)}. Personne n'est éliminé."
                    )
                    print(f"[DAY_LOG] Égalité entre {', '.join(top_voted)}")

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
                # Sauvegarder les discussions avant de passer à la nuit suivante
                self._save_discussions_history(game)
                # Passer à la nuit suivante
                game.day_number += 1
                game.phase = Phase.NUIT
                game.pending_action = "auto_night"

            return result

        elif action_type == "day_vote" or action_type == "skip_day_vote":
            target_name = action.get("target")
            print(f"[DAY_LOG] Joueur humain {human.name} vote pour {target_name}")

            # Collecter les votes
            votes = {human.name: target_name}

            # Récupérer les discussions pour contexte
            discussions = self.discussions_cache.get(game.game_id, [])
            print(f"[DAY_LOG] Contexte: {len(discussions)} messages de discussion")

            # Générer les votes IA en parallèle
            agents = self.ai_agents.get(game.game_id, {})
            vote_tasks = []
            alive_ias = []

            for player in game.get_alive_players():
                if not player.is_human:
                    agent = agents.get(player.name)
                    if agent:
                        alive_ias.append(player.name)
                        vote_tasks.append(agent.generate_vote(discussions))

            # Attendre TOUS les appels API en parallèle
            if vote_tasks:
                print(f"[DAY_LOG] Génération des votes pour {len(vote_tasks)} IA en parallèle...")
                vote_results = await asyncio.gather(*vote_tasks, return_exceptions=True)

                for result_vote, ia_name in zip(vote_results, alive_ias):
                    if isinstance(result_vote, Exception):
                        print(f"[DAY_LOG] ERREUR pour {ia_name}: {result_vote}")
                    elif result_vote.get("vote"):
                        votes[ia_name] = result_vote["vote"]
                        print(f"[DAY_LOG] {ia_name} vote pour {result_vote['vote']}")
                        # Mettre à jour la mémoire
                        agents[ia_name].update_memory("vote", {"voter": ia_name, "target": result_vote["vote"]})

            # Compter les votes
            vote_counts = Counter(votes.values())
            result["votes"] = dict(votes)
            result["vote_counts"] = dict(vote_counts)
            print(f"[DAY_LOG] Votes comptés: {dict(vote_counts)}")

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
                        print(f"[DAY_LOG] {eliminated_name} éliminé ({eliminated.role.display_name})")
                        # Mettre à jour la mémoire des agents
                        for agent in agents.values():
                            agent.update_memory("death", {
                                "name": eliminated_name,
                                "role": eliminated.role.display_name,
                                "cause": "vote"
                            })
                        # Ajouter à l'historique texte
                        game.history.append({
                            "type": "death",
                            "day": game.day_number,
                            "message": f"{eliminated_name} a été éliminé et était {eliminated.role.display_name}"
                        })
                else:
                    result["tie"] = True
                    result["messages"].append(
                        f"Égalité entre {', '.join(top_voted)}. Personne n'est éliminé."
                    )
                    print(f"[DAY_LOG] Égalité entre {', '.join(top_voted)}")

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
                print(f"[DAY_LOG] FIN DE PARTIE: {result['game_over']['winner']} gagne")
            else:
                # Sauvegarder les discussions avant de passer à la nuit suivante
                self._save_discussions_history(game)
                # Passer à la nuit suivante
                game.day_number += 1
                game.phase = Phase.NUIT
                human_player = next((p for p in game.players if p.is_human), None)
                if human_player and human_player.is_alive:
                    game.pending_action = self._get_pending_action(
                        game.players, Phase.NUIT, human_player.role
                    )
                else:
                    # Le joueur est mort, automatiser la nuit
                    game.pending_action = "auto_night"
                print(f"[DAY_LOG] Passage à la nuit {game.day_number}")

        print(f"[DAY_LOG] === FIN traitement {action_type} ===\n")
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
                    if game.get_player(nom_agent_2).is_human :
                        game.pending_action = "human_discussion"
                        print(f"C'est au tour de {current_player_name} (humain) de parler")
                        break

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