"""
Agents IA pour le jeu du Loup-Garou avec Anthropic Claude
"""
import os
import json
import random
from dataclasses import dataclass, field
from typing import Optional
import anthropic
import re
from dotenv import load_dotenv
load_dotenv()

from .models import Player, Role, GameState, Phase


# Client Anthropic (initialisé avec la clé API)
_anthropic_client: Optional[anthropic.Anthropic] = None

MALE_VOICES = ["axlOaUiFyOZhy4nv", "Hdf5cdfaGrLDTD63", "IB53xJtufx1sbfbt", "B09t5S64xLaKwXeW"]
FEMALE_VOICES = ["1VAVLmmbQFDw7TMn", "GmGF_3ETsY2Zq7_w", "p1fSBpcmVWngBqVd", "3mM3xaoFjNMQa22C"]

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
    gender: str  # "male" ou "female"
    voice_id: str = ""  # ID de la voix utilisée par l'IA


# Predefined personalities for AI players
AI_PERSONALITIES = [
    AIPersonality(
        name="Marie",
        description="Retired teacher, observant and methodical",
        traits=["analytical", "patient", "suspicious"],
        speech_style="Speaks in a measured and thoughtful manner, uses educational metaphors",
        gender="female",
        voice_id="1VAVLmmbQFDw7TMn"
    ),
    AIPersonality(
        name="Pierre",
        description="Former soldier, direct and pragmatic",
        traits=["impulsive", "courageous", "frank"],
        speech_style="Speaks directly and bluntly, sometimes harsh",
        gender="male",
        voice_id="axlOaUiFyOZhy4nv"
    ),
    AIPersonality(
        name="Sophie",
        description="Psychology student, subtle manipulator",
        traits=["charming", "intelligent", "cunning"],
        speech_style="Speaks softly and persuasively, asks many questions",
        gender="female",
        voice_id="GmGF_3ETsY2Zq7_w"
    ),
    AIPersonality(
        name="Jean",
        description="Village baker, jovial but naive",
        traits=["friendly", "confident", "honest"],
        speech_style="Speaks simply with popular expressions, makes jokes",
        gender="male",
        voice_id="Hdf5cdfaGrLDTD63"
    ),
    AIPersonality(
        name="Élise",
        description="Forensic doctor, cold and logical",
        traits=["rational", "detached", "precise"],
        speech_style="Speaks in a clinical and factual manner, analyzes behaviors",
        gender="female",
        voice_id="3mM3xaoFjNMQa22C"
    ),
    AIPersonality(
        name="Lucas",
        description="Rebellious teenager, unpredictable",
        traits=["provocative", "instinctive", "changeable"],
        speech_style="Speaks casually with slang, provokes others",
        gender="male",
        voice_id="IB53xJtufx1sbfbt"
    ),
    AIPersonality(
        name="Margot",
        description="Mysterious librarian, silent but insightful",
        traits=["discrete", "observant", "enigmatic"],
        speech_style="Speaks little but each word counts, makes cryptic remarks",
        gender="female",
        voice_id="p1fSBpcmVWngBqVd"
    ),
    AIPersonality(
        name="Henri",
        description="Village mayor, political and calculating",
        traits=["diplomat", "influential", "opportunist"],
        speech_style="Speaks in a political manner, tries to rally people to his cause",
        gender="male",
        voice_id="B09t5S64xLaKwXeW"
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
        """Build the system prompt for the agent"""
        role_info = self._get_role_info()

        return f"""You are {self.personality.name}, a player in a Werewolf game.

PERSONALITY:
- Description: {self.personality.description}
- Traits: {', '.join(self.personality.traits)}
- Speech style: {self.personality.speech_style}

YOUR SECRET ROLE: {self.player.role.display_name}
{role_info}

IMPORTANT RULES:
1. You must ALWAYS stay in character
2. Your responses must be SHORT (1-2 sentences max for discussions)
3. You must NEVER reveal your role directly (except if you're the Seer and want to help the village)
4. If you're a Werewolf, you must lie and divert suspicion
5. Analyze others' behaviors to make decisions

IMPORTANT: Always respond in English."""

    def _get_role_info(self) -> str:
        """Return role-specific information"""
        if self.player.role == Role.LOUP_GAROU:
            wolves = [p.name for p in self.game_state.get_wolves() if p.name != self.player.name]
            wolves_str = ", ".join(wolves) if wolves else "none"
            return f"""You are a WEREWOLF.
Your werewolf allies: {wolves_str}
Objective: Eliminate all villagers without being exposed.
At night, you vote to devour a villager.
During the day, you must appear innocent and accuse others."""

        elif self.player.role == Role.VOYANTE:
            return """You are the SEER.
Objective: Help the village identify the werewolves.
Each night, you can discover a player's true role.
Use this information carefully - revealing your role puts you in danger."""

        elif self.player.role == Role.SORCIERE:
            return """You are the WITCH.
Objective: Help the village with your potions.
You have a life potion (save the werewolves' victim) and a death potion (kill someone).
Each potion can only be used once."""

        else:
            return """You are a VILLAGER.
Objective: Identify and eliminate the werewolves.
You have no special power but your vote counts.
Observe suspicious behaviors."""

    def _build_game_context(self) -> str:
        """Build current game context"""
        game = self.game_state

        alive_players = [p.name for p in game.get_alive_players()]
        dead_players = [(p.name, p.role.display_name) for p in game.players if not p.is_alive]

        context = f"""GAME STATE:
- Phase: {game.phase.value} (Day {game.day_number})
- Alive players: {', '.join(alive_players)}
- Dead players: {', '.join([f"{n} ({r})" for n, r in dead_players]) if dead_players else 'none'}
"""

        # Add memory information
        if self.memory.known_roles:
            known = [f"{n}: {r}" for n, r in self.memory.known_roles.items()]
            context += f"- Roles you know: {', '.join(known)}\n"

        if self.memory.conversations:
            recent = self.memory.conversations[-5:]  # Last 5 messages
            context += "- Recent discussions:\n"
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

It's the day discussion phase. You must participate in the discussion to:
1. Express your suspicions (true or false based on your role)
2. Defend yourself if necessary
3. Influence the vote

Generate ONE short reply (2-3 sentences) while staying in character.
Don't automatically target the first person who speaks loudly - they may have good reasons.
If there have been no previous discussions, you don't need to invent ones, you can start the conversation.
If your response targets a specific person you want to confront, put their name in the "name" field of the output JSON.
Otherwise leave the "name" field empty.
Your response must be in the following JSON format:
  "content": "your message here",
  "name": "target name or empty"

"""

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
        """Fallback message if API fails"""
        fallbacks = [
            "I'm still thinking about this...",
            "Hmm, something seems suspicious here.",
            "We should observe more carefully.",
            "I'm not sure who to vote for.",
        ]
        return random.choice(fallbacks)

    async def generate_vote(self, discussions: list[dict]) -> dict:
        """Génère le vote du jour"""
        system_prompt = self._build_system_prompt()
        game_context = self._build_game_context()

        candidates = [p.name for p in self.game_state.get_alive_players() if p.name != self.player.name]

        user_prompt = f"""{game_context}

Today's discussions:
{chr(10).join([f"- {d['player']}: {d['message']}" for d in discussions])}

It's time to vote. You must choose ONE player to eliminate from: {', '.join(candidates)}

IMPORTANT:
- If you're a Werewolf, vote in your own interest
- If you're a Villager/Seer/Witch, vote against the one you suspect most

Respond ONLY with a JSON in this form:
{{"vote": "PlayerName", "reasoning": "Brief explanation"}}"""

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
                result = json.loads(format_json(content))
                # Vérifier que le vote est valide
                if result.get("vote") in candidates:
                    return result
            except json.JSONDecodeError:
                pass

            # Si parsing échoue, extraire le nom
            for candidate in candidates:
                if candidate.lower() in content.lower():
                    return {"vote": candidate, "reasoning": "Vote basé sur les discussions"}
                else : 
                    print("Mauvais format Json !!!!")
                    print(candidate)

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

It's night time. You and your werewolf allies ({', '.join(fellow_wolves)}) must choose a victim.

Possible targets: {', '.join(targets)}

Recommended strategy:
- Eliminate the Seer or Witch first if you suspect them
- Eliminate the most active/dangerous players for you
- Avoid creating an obvious pattern

Respond ONLY with a JSON:
{{"target": "PlayerName"}}"""

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
                result = json.loads(format_json(content))
                if result.get("target") in targets:
                    return result
            except json.JSONDecodeError:
                print("Erreur 336")
                pass

            # Chercher le nom du joueur dans la réponse
            found_targets = [target for target in targets if target.lower() in content.lower()]
            if found_targets:
                # Si plusieurs cibles trouvées, choisir aléatoirement pour éviter un pattern
                chosen_target = random.choice(found_targets)
                return {"target": chosen_target, "reasoning": "Cible stratégique"}

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

You are the Seer. Tonight, you can discover a player's true role.

Players you can observe: {', '.join(targets)}
Players whose roles you already know: {', '.join(self.memory.known_roles.keys()) if self.memory.known_roles else 'none'}

Respond ONLY with a JSON:
{{"target": "PlayerName"}}"""

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
                result = json.loads(format_json(content))
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
Available potions:
- Life potion: {'YES' if has_life else 'NO (already used)'}
- Death potion: {'YES' if has_death else 'NO (already used)'}

{"The werewolves attacked: " + wolf_victim if wolf_victim else "No one was attacked tonight."}
"""

        user_prompt = f"""{game_context}

{potions_info}

You must decide:
1. Use your life potion to save {wolf_victim}? (if available)
2. Use your death potion on someone? (targets: {', '.join(targets)})
You're not forced to use them immediately, you can wait until you need to protect someone important, or yourself.
Only use your death potion as a last resort when you're sure the person you're killing is a werewolf - don't risk killing a villager.
Respond ONLY with a JSON:
{{"save": true/false, "kill": "PlayerName" or null, "reasoning": "Explanation"}}"""

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
                result = json.loads(format_json(content))
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
def format_json(chaine_sale):
    try:
        propre = re.sub(r'```(?:json)?|```', '', chaine_sale).strip()
        if propre.startswith("json"):
            propre = propre[4:].strip()
        donnees = json.loads(propre)
        return json.dumps(donnees, indent=4, ensure_ascii=False)

    except Exception as e:
        return f"Erreur de formatage : {e}"

def assign_personalities(players: list[Player]) -> dict[str, AIPersonality]:
    """Assigne des personnalités aux joueurs IA"""
    available = AI_PERSONALITIES.copy()
    random.shuffle(available)
    available_male_voices = MALE_VOICES.copy()
    available_female_voices = FEMALE_VOICES.copy()
    random.shuffle(available_male_voices)
    random.shuffle(available_female_voices)

    assignments = {}
    for player in players:
        if not player.is_human:
            if available:
                personality = available.pop()
                if personality.gender == "male" and available_male_voices:
                    personality.voice_id = available_male_voices.pop()
                elif personality.gender == "female" and available_female_voices:
                    personality.voice_id = available_female_voices.pop()
                else:
                    # Fallback si on manque de voix (utilise la première voix disponible)
                    personality.voice_id = MALE_VOICES[0] if personality.gender == "male" else FEMALE_VOICES[0]
                player.name = personality.name
                player.personality = personality.description
                player.voice_id = personality.voice_id
                assignments[player.name] = personality

    return assignments

