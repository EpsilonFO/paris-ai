"""
Agents IA pour le jeu du Loup-Garou avec Anthropic Claude
"""
import os
import json
import random
from dataclasses import dataclass, field
from typing import Optional
import anthropic

from .models import Player, Role, GameState, Phase


# Client Anthropic (initialisé avec la clé API)
_anthropic_client: Optional[anthropic.Anthropic] = None


def get_anthropic_client() -> anthropic.Anthropic:
    """Récupère ou crée le client Anthropic"""
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


def set_anthropic_api_key(api_key: str):
    """Configure la clé API Anthropic"""
    global _anthropic_client
    _anthropic_client = anthropic.Anthropic(api_key=api_key)


@dataclass
class AIPersonality:
    name: str
    description: str
    traits: list[str]
    speech_style: str  # Comment l'IA doit parler


# Personnalités prédéfinies pour les joueurs IA
AI_PERSONALITIES = [
    AIPersonality(
        name="Marie",
        description="Institutrice à la retraite, observatrice et méthodique",
        traits=["analytique", "patiente", "méfiante"],
        speech_style="Parle de manière posée et réfléchie, utilise des métaphores éducatives"
    ),
    AIPersonality(
        name="Pierre",
        description="Ancien militaire, direct et pragmatique",
        traits=["impulsif", "courageux", "franc"],
        speech_style="Parle de manière directe et sans détour, parfois brusque"
    ),
    AIPersonality(
        name="Sophie",
        description="Étudiante en psychologie, manipulatrice subtile",
        traits=["charmante", "intelligente", "rusée"],
        speech_style="Parle de manière douce et persuasive, pose beaucoup de questions"
    ),
    AIPersonality(
        name="Jean",
        description="Boulanger du village, jovial mais naïf",
        traits=["sympathique", "confiant", "honnête"],
        speech_style="Parle simplement avec des expressions populaires, fait des blagues"
    ),
    AIPersonality(
        name="Élise",
        description="Médecin légiste, froide et logique",
        traits=["rationnelle", "détachée", "précise"],
        speech_style="Parle de manière clinique et factuelle, analyse les comportements"
    ),
    AIPersonality(
        name="Lucas",
        description="Adolescent rebelle, imprévisible",
        traits=["provocateur", "instinctif", "changeant"],
        speech_style="Parle de manière décontractée avec du slang, provoque les autres"
    ),
    AIPersonality(
        name="Margot",
        description="Libraire mystérieuse, silencieuse mais perspicace",
        traits=["discrète", "observatrice", "énigmatique"],
        speech_style="Parle peu mais chaque mot compte, fait des remarques cryptiques"
    ),
    AIPersonality(
        name="Henri",
        description="Maire du village, politique et calculateur",
        traits=["diplomate", "influent", "opportuniste"],
        speech_style="Parle de manière politique, essaie de rallier les gens à sa cause"
    ),
]


@dataclass
class AIMemory:
    """Mémoire d'un agent IA pour le jeu"""
    known_roles: dict[str, str] = field(default_factory=dict)  # joueur -> rôle connu
    suspicions: dict[str, float] = field(default_factory=dict)  # joueur -> niveau de suspicion
    accusations_made: list[dict] = field(default_factory=list)
    accusations_received: list[dict] = field(default_factory=list)
    votes_history: list[dict] = field(default_factory=list)
    deaths_witnessed: list[dict] = field(default_factory=list)
    conversations: list[dict] = field(default_factory=list)


class AIAgent:
    """Agent IA pour un joueur du Loup-Garou utilisant Anthropic Claude"""

    def __init__(self, player: Player, personality: AIPersonality, game_state: GameState):
        self.player = player
        self.personality = personality
        self.game_state = game_state
        self.memory = AIMemory()
        self.model = "claude-haiku-4-5-20251001"

    def _build_system_prompt(self) -> str:
        """Construit le prompt système pour l'agent"""
        role_info = self._get_role_info()

        return f"""Tu es {self.personality.name}, un joueur dans une partie de Loup-Garou.

PERSONNALITÉ:
- Description: {self.personality.description}
- Traits: {', '.join(self.personality.traits)}
- Style de parole: {self.personality.speech_style}

TON RÔLE SECRET: {self.player.role.display_name}
{role_info}

RÈGLES IMPORTANTES:
1. Tu dois TOUJOURS rester dans ton personnage
2. Tes réponses doivent être COURTES (1-2 phrases max pour les discussions)
3. Tu ne dois JAMAIS révéler ton rôle directement (sauf si tu es Voyante et que tu veux aider le village)
4. Si tu es Loup-Garou, tu dois mentir et détourner les soupçons
5. Analyse les comportements des autres pour tes décisions

IMPORTANT: Réponds toujours en français."""

    def _get_role_info(self) -> str:
        """Retourne les informations spécifiques au rôle"""
        if self.player.role == Role.LOUP_GAROU:
            wolves = [p.name for p in self.game_state.get_wolves() if p.name != self.player.name]
            wolves_str = ", ".join(wolves) if wolves else "aucun"
            return f"""Tu es un LOUP-GAROU.
Tes alliés loups: {wolves_str}
Objectif: Éliminer tous les villageois sans te faire démasquer.
La nuit, tu votes pour dévorer un villageois.
Le jour, tu dois paraître innocent et accuser les autres."""

        elif self.player.role == Role.VOYANTE:
            return """Tu es la VOYANTE.
Objectif: Aider le village à identifier les loups.
Chaque nuit, tu peux découvrir le rôle d'un joueur.
Utilise cette information avec prudence - révéler ton rôle te met en danger."""

        elif self.player.role == Role.SORCIERE:
            return """Tu es la SORCIÈRE.
Objectif: Aider le village avec tes potions.
Tu as une potion de vie (sauver la victime des loups) et une potion de mort (tuer quelqu'un).
Chaque potion ne peut être utilisée qu'une fois."""

        else:
            return """Tu es un VILLAGEOIS.
Objectif: Identifier et éliminer les loups-garous.
Tu n'as pas de pouvoir spécial mais ton vote compte.
Observe les comportements suspects."""

    def _build_game_context(self) -> str:
        """Construit le contexte actuel du jeu"""
        game = self.game_state

        alive_players = [p.name for p in game.get_alive_players()]
        dead_players = [(p.name, p.role.display_name) for p in game.players if not p.is_alive]

        context = f"""ÉTAT DU JEU:
- Phase: {game.phase.value} (Jour {game.day_number})
- Joueurs vivants: {', '.join(alive_players)}
- Joueurs morts: {', '.join([f"{n} ({r})" for n, r in dead_players]) if dead_players else 'aucun'}
"""

        # Ajouter les informations de mémoire
        if self.memory.known_roles:
            known = [f"{n}: {r}" for n, r in self.memory.known_roles.items()]
            context += f"- Rôles que tu connais: {', '.join(known)}\n"

        if self.memory.conversations:
            recent = self.memory.conversations[-5:]  # 5 derniers messages
            context += "- Discussions récentes:\n"
            for conv in recent:
                context += f"  * {conv['player']}: {conv['message']}\n"

        return context

    async def generate_discussion(self, recent_messages: list[dict]) -> str:
        """Génère une contribution à la discussion de jour"""
        # Mettre à jour la mémoire avec les messages récents
        for msg in recent_messages:
            if msg not in self.memory.conversations:
                self.memory.conversations.append(msg)

        system_prompt = self._build_system_prompt()
        game_context = self._build_game_context()

        user_prompt = f"""{game_context}

C'est la phase de discussion du jour. Tu dois participer à la discussion pour:
1. Exprimer tes suspicions (vraies ou fausses selon ton rôle)
2. Te défendre si nécessaire
3. Orienter le vote

Génère UNE réplique courte (1-2 phrases) en restant dans ton personnage.
Ne mets pas de guillemets autour de ta réponse."""

        try:
            client = get_anthropic_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=150,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            # Fallback en cas d'erreur
            return self._fallback_discussion()

    def _fallback_discussion(self) -> str:
        """Message de fallback si l'API échoue"""
        fallbacks = [
            "Je réfléchis encore...",
            "Hmm, c'est suspect tout ça.",
            "On devrait observer plus attentivement.",
            "Je ne suis pas sûr de qui voter.",
        ]
        return random.choice(fallbacks)

    async def generate_vote(self, discussions: list[dict]) -> dict:
        """Génère le vote du jour"""
        system_prompt = self._build_system_prompt()
        game_context = self._build_game_context()

        candidates = [p.name for p in self.game_state.get_alive_players() if p.name != self.player.name]

        user_prompt = f"""{game_context}

Discussions du jour:
{chr(10).join([f"- {d['player']}: {d['message']}" for d in discussions])}

C'est le moment de voter. Tu dois choisir UN joueur à éliminer parmi: {', '.join(candidates)}

IMPORTANT:
- Si tu es Loup-Garou, vote contre un villageois (évite de voter contre tes alliés loups)
- Si tu es Villageois/Voyante/Sorcière, vote contre celui que tu suspectes le plus

Réponds UNIQUEMENT avec un JSON de cette forme:
{{"vote": "NomDuJoueur", "reasoning": "Explication courte"}}"""

        try:
            client = get_anthropic_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=100,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            content = response.content[0].text.strip()
            # Parser le JSON
            try:
                result = json.loads(content)
                # Vérifier que le vote est valide
                if result.get("vote") in candidates:
                    return result
            except json.JSONDecodeError:
                pass

            # Si parsing échoue, extraire le nom
            for candidate in candidates:
                if candidate.lower() in content.lower():
                    return {"vote": candidate, "reasoning": "Vote basé sur les discussions"}

            # Fallback
            return {"vote": random.choice(candidates), "reasoning": "Vote aléatoire"}

        except Exception as e:
            return {"vote": random.choice(candidates), "reasoning": f"Erreur: {str(e)}"}

    async def generate_wolf_vote(self, fellow_wolves: list[str]) -> dict:
        """Génère le vote nocturne des loups"""
        system_prompt = self._build_system_prompt()
        game_context = self._build_game_context()

        # Cibles potentielles (non-loups vivants)
        targets = [p.name for p in self.game_state.get_alive_players()
                   if p.role != Role.LOUP_GAROU]

        user_prompt = f"""{game_context}

C'est la nuit. Toi et tes alliés loups ({', '.join(fellow_wolves)}) devez choisir une victime.

Cibles possibles: {', '.join(targets)}

Stratégie recommandée:
- Éliminer la Voyante ou la Sorcière en priorité si tu les suspectes
- Éliminer les joueurs les plus actifs/dangereux pour vous
- Éviter de créer un pattern trop évident

Réponds UNIQUEMENT avec un JSON:
{{"target": "NomDuJoueur"}}"""

        try:
            client = get_anthropic_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=100,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            content = response.content[0].text.strip()
            try:
                result = json.loads(content)
                if result.get("target") in targets:
                    return result
            except json.JSONDecodeError:
                pass

            for target in targets:
                if target.lower() in content.lower():
                    return {"target": target, "reasoning": "Cible stratégique"}

            return {"target": random.choice(targets), "reasoning": "Choix aléatoire"}

        except Exception as e:
            return {"target": random.choice(targets), "reasoning": f"Erreur: {str(e)}"}

    async def generate_seer_choice(self) -> dict:
        """Génère le choix de la voyante"""
        targets = [p.name for p in self.game_state.get_alive_players()
                   if p.name != self.player.name and p.name not in self.memory.known_roles]

        if not targets:
            targets = [p.name for p in self.game_state.get_alive_players()
                       if p.name != self.player.name]

        system_prompt = self._build_system_prompt()
        game_context = self._build_game_context()

        user_prompt = f"""{game_context}

Tu es la Voyante. Cette nuit, tu peux découvrir le rôle d'un joueur.

Joueurs que tu peux observer: {', '.join(targets)}
Joueurs dont tu connais déjà le rôle: {', '.join(self.memory.known_roles.keys()) if self.memory.known_roles else 'aucun'}

Réponds UNIQUEMENT avec un JSON:
{{"target": "NomDuJoueur"}}"""

        try:
            client = get_anthropic_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=100,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            content = response.content[0].text.strip()
            try:
                result = json.loads(content)
                if result.get("target") in targets:
                    return result
            except json.JSONDecodeError:
                pass

            return {"target": random.choice(targets), "reasoning": "Observation aléatoire"}

        except Exception as e:
            return {"target": random.choice(targets), "reasoning": f"Erreur: {str(e)}"}

    async def generate_witch_choice(self, wolf_victim: Optional[str], has_life: bool, has_death: bool) -> dict:
        """Génère les choix de la sorcière"""
        system_prompt = self._build_system_prompt()
        game_context = self._build_game_context()

        targets = [p.name for p in self.game_state.get_alive_players()
                   if p.name != self.player.name]

        potions_info = f"""
Potions disponibles:
- Potion de vie: {'OUI' if has_life else 'NON (déjà utilisée)'}
- Potion de mort: {'OUI' if has_death else 'NON (déjà utilisée)'}

{"Les loups ont attaqué: " + wolf_victim if wolf_victim else "Personne n'a été attaqué cette nuit."}
"""

        user_prompt = f"""{game_context}

{potions_info}

Tu dois décider:
1. Utiliser la potion de vie pour sauver {wolf_victim}? (si disponible)
2. Utiliser la potion de mort sur quelqu'un? (cibles: {', '.join(targets)})

Réponds UNIQUEMENT avec un JSON:
{{"save": true/false, "kill": "NomDuJoueur" ou null, "reasoning": "Explication"}}"""

        try:
            client = get_anthropic_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=100,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            content = response.content[0].text.strip()
            try:
                result = json.loads(content)
                return {
                    "save": bool(result.get("save", False)) and has_life and wolf_victim,
                    "kill": result.get("kill") if result.get("kill") in targets and has_death else None,
                    "reasoning": result.get("reasoning", "")
                }
            except json.JSONDecodeError:
                pass

            return {"save": False, "kill": None, "reasoning": "Pas d'action"}

        except Exception as e:
            return {"save": False, "kill": None, "reasoning": f"Erreur: {str(e)}"}

    def update_memory(self, event_type: str, data: dict):
        """Met à jour la mémoire de l'agent"""
        if event_type == "role_revealed":
            self.memory.known_roles[data["player"]] = data["role"]
        elif event_type == "death":
            self.memory.deaths_witnessed.append(data)
        elif event_type == "vote":
            self.memory.votes_history.append(data)
        elif event_type == "accusation":
            if data.get("target") == self.player.name:
                self.memory.accusations_received.append(data)
            elif data.get("accuser") == self.player.name:
                self.memory.accusations_made.append(data)


# Alias pour compatibilité
AIBrain = AIAgent


def assign_personalities(players: list[Player]) -> dict[str, AIPersonality]:
    """Assigne des personnalités aux joueurs IA"""
    available = AI_PERSONALITIES.copy()
    random.shuffle(available)

    assignments = {}
    for player in players:
        if not player.is_human:
            if available:
                personality = available.pop()
                player.name = personality.name
                player.personality = personality.description
                assignments[player.name] = personality

    return assignments
