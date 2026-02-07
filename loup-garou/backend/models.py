"""
Modèles de données pour le jeu du Loup-Garou
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import random
import string


class Faction(Enum):
    VILLAGE = "village"
    LOUPS_GAROUS = "loups_garous"


class Role(Enum):
    VILLAGEOIS = "villageois"
    LOUP_GAROU = "loup_garou"
    VOYANTE = "voyante"
    SORCIERE = "sorciere"

    @property
    def faction(self) -> Faction:
        if self == Role.LOUP_GAROU:
            return Faction.LOUPS_GAROUS
        return Faction.VILLAGE

    @property
    def display_name(self) -> str:
        names = {
            Role.VILLAGEOIS: "Villageois",
            Role.LOUP_GAROU: "Loup-Garou",
            Role.VOYANTE: "Voyante",
            Role.SORCIERE: "Sorcière",
        }
        return names[self]


class Phase(Enum):
    NUIT = "nuit"
    JOUR = "jour"


class GameStatus(Enum):
    EN_COURS = "en_cours"
    VICTOIRE_VILLAGE = "victoire_village"
    VICTOIRE_LOUPS = "victoire_loups"


@dataclass
class Player:
    name: str
    role: Role
    is_alive: bool = True
    is_human: bool = False
    personality: Optional[str] = None

    def to_dict(self, reveal_role: bool = False) -> dict:
        data = {
            "name": self.name,
            "is_alive": self.is_alive,
            "is_human": self.is_human,
        }
        if reveal_role or not self.is_alive:
            data["role"] = self.role.display_name
        return data


@dataclass
class WitchPotions:
    has_life_potion: bool = True
    has_death_potion: bool = True


@dataclass
class NightActions:
    wolf_victim: Optional[str] = None
    seer_target: Optional[str] = None
    seer_result: Optional[str] = None
    witch_save: bool = False
    witch_kill: Optional[str] = None


@dataclass
class VoteResult:
    votes: dict[str, str] = field(default_factory=dict)  # voter -> target
    eliminated: Optional[str] = None
    is_tie: bool = False


@dataclass
class DiscussionMessage:
    """Message d'un joueur pendant la phase de discussion"""
    player: str
    message: str
    question_to: Optional[str] = None  # Nom du joueur interpellé (si question)
    is_response: bool = False  # True si c'est une réponse à une question


@dataclass
class DiscussionState:
    """État de la discussion du jour"""
    messages: list[DiscussionMessage] = field(default_factory=list)
    speaking_order: list[str] = field(default_factory=list)  # Ordre de parole
    current_speaker_index: int = 0
    questions_asked_by: dict[str, bool] = field(default_factory=dict)  # joueur -> a posé une question
    rounds_completed: int = 0
    max_rounds: int = 1
    is_complete: bool = False

    def get_current_speaker(self) -> Optional[str]:
        """Retourne le joueur dont c'est le tour de parler"""
        if self.is_complete or not self.speaking_order:
            return None
        if self.current_speaker_index >= len(self.speaking_order):
            return None
        return self.speaking_order[self.current_speaker_index]

    def advance_speaker(self):
        """Passe au joueur suivant"""
        self.current_speaker_index += 1
        if self.current_speaker_index >= len(self.speaking_order):
            # Fin d'un tour
            self.rounds_completed += 1
            if self.rounds_completed >= self.max_rounds:
                self.is_complete = True
            else:
                self.current_speaker_index = 0
                self.questions_asked_by.clear()  # Reset des questions pour le prochain tour

    def has_asked_question(self, player: str) -> bool:
        """Vérifie si un joueur a déjà posé une question ce tour"""
        return self.questions_asked_by.get(player, False)

    def mark_question_asked(self, player: str):
        """Marque qu'un joueur a posé une question"""
        self.questions_asked_by[player] = True


@dataclass
class GameState:
    game_id: str
    players: list[Player]
    phase: Phase
    day_number: int
    status: GameStatus
    witch_potions: WitchPotions
    night_actions: NightActions
    history: list[dict]
    pending_action: Optional[str] = None
    discussion_state: Optional["DiscussionState"] = None

    @classmethod
    def generate_id(cls) -> str:
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    def get_player(self, name: str) -> Optional[Player]:
        for player in self.players:
            if player.name.lower() == name.lower():
                return player
        return None

    def get_alive_players(self) -> list[Player]:
        return [p for p in self.players if p.is_alive]

    def get_wolves(self) -> list[Player]:
        return [p for p in self.players if p.role == Role.LOUP_GAROU and p.is_alive]

    def get_villagers(self) -> list[Player]:
        return [p for p in self.players if p.role.faction == Faction.VILLAGE and p.is_alive]

    def count_by_faction(self) -> dict[Faction, int]:
        counts = {Faction.VILLAGE: 0, Faction.LOUPS_GAROUS: 0}
        for player in self.get_alive_players():
            counts[player.role.faction] += 1
        return counts

    def check_victory(self) -> Optional[GameStatus]:
        counts = self.count_by_faction()

        if counts[Faction.LOUPS_GAROUS] == 0:
            return GameStatus.VICTOIRE_VILLAGE

        if counts[Faction.LOUPS_GAROUS] >= counts[Faction.VILLAGE]:
            return GameStatus.VICTOIRE_LOUPS

        return None

    def to_dict(self, player_perspective: Optional[str] = None) -> dict:
        """Serialize game state, optionally from a player's perspective"""
        human_player = None
        if player_perspective:
            human_player = self.get_player(player_perspective)

        players_data = []
        for p in self.players:
            reveal = False
            if not p.is_alive:
                reveal = True
            elif human_player and p.name == human_player.name:
                reveal = True
            elif human_player and human_player.role == Role.LOUP_GAROU and p.role == Role.LOUP_GAROU:
                reveal = True
            players_data.append(p.to_dict(reveal_role=reveal))

        return {
            "game_id": self.game_id,
            "phase": self.phase.value,
            "day_number": self.day_number,
            "status": self.status.value,
            "players": players_data,
            "alive_count": len(self.get_alive_players()),
            "pending_action": self.pending_action,
        }
