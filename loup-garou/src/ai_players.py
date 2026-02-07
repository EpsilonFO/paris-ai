"""
Personnalités et comportements des joueurs IA
"""
from dataclasses import dataclass
from typing import Optional
import random

from .models import Player, Role, GameState, Phase


@dataclass
class AIPersonality:
    name: str
    description: str
    aggression: float  # 0-1, tendency to accuse
    suspicion: float   # 0-1, tendency to be suspicious
    eloquence: float   # 0-1, verbosity in discussions
    deception: float   # 0-1, skill at lying (for wolves)
    traits: list[str]


# Personnalités prédéfinies pour les joueurs IA
AI_PERSONALITIES = [
    AIPersonality(
        name="Marie",
        description="Institutrice à la retraite, observatrice et méthodique",
        aggression=0.3,
        suspicion=0.7,
        eloquence=0.8,
        deception=0.4,
        traits=["analytique", "patiente", "méfiante"]
    ),
    AIPersonality(
        name="Pierre",
        description="Ancien militaire, direct et pragmatique",
        aggression=0.8,
        suspicion=0.5,
        eloquence=0.4,
        deception=0.3,
        traits=["impulsif", "courageux", "franc"]
    ),
    AIPersonality(
        name="Sophie",
        description="Étudiante en psychologie, manipulatrice subtile",
        aggression=0.4,
        suspicion=0.6,
        eloquence=0.9,
        deception=0.8,
        traits=["charmante", "intelligente", "rusée"]
    ),
    AIPersonality(
        name="Jean",
        description="Boulanger du village, jovial mais naïf",
        aggression=0.2,
        suspicion=0.3,
        eloquence=0.6,
        deception=0.2,
        traits=["sympathique", "confiant", "honnête"]
    ),
    AIPersonality(
        name="Élise",
        description="Médecin légiste, froide et logique",
        aggression=0.5,
        suspicion=0.8,
        eloquence=0.7,
        deception=0.5,
        traits=["rationnelle", "détachée", "précise"]
    ),
    AIPersonality(
        name="Lucas",
        description="Adolescent rebelle, imprévisible",
        aggression=0.7,
        suspicion=0.4,
        eloquence=0.5,
        deception=0.6,
        traits=["provocateur", "instinctif", "changeant"]
    ),
    AIPersonality(
        name="Margot",
        description="Libraire mystérieuse, silencieuse mais perspicace",
        aggression=0.3,
        suspicion=0.9,
        eloquence=0.5,
        deception=0.7,
        traits=["discrète", "observatrice", "énigmatique"]
    ),
    AIPersonality(
        name="Henri",
        description="Maire du village, politique et calculateur",
        aggression=0.6,
        suspicion=0.6,
        eloquence=0.9,
        deception=0.8,
        traits=["diplomate", "influent", "opportuniste"]
    ),
]


class AIBrain:
    """Génère les comportements et décisions des joueurs IA"""

    def __init__(self, player: Player, personality: AIPersonality, game_state: GameState):
        self.player = player
        self.personality = personality
        self.game_state = game_state
        self.suspicions: dict[str, float] = {}  # player_name -> suspicion_level

    def generate_night_action(self) -> Optional[dict]:
        """Génère l'action nocturne selon le rôle"""
        if not self.player.is_alive:
            return None

        if self.player.role == Role.LOUP_GAROU:
            return self._wolf_action()
        elif self.player.role == Role.VOYANTE:
            return self._seer_action()
        elif self.player.role == Role.SORCIERE:
            return self._witch_action()

        return None

    def _wolf_action(self) -> dict:
        """Choix de la victime pour un loup"""
        targets = [p for p in self.game_state.get_alive_players()
                   if p.role != Role.LOUP_GAROU]

        # Préférer les joueurs qui semblent dangereux
        weights = []
        for target in targets:
            weight = 1.0
            # Les loups veulent éliminer les rôles spéciaux
            if target.role in [Role.VOYANTE, Role.SORCIERE]:
                weight += 2.0
            # Éviter ceux qui les suspectent (si connu)
            if target.name in self.suspicions:
                weight += self.suspicions[target.name]
            weights.append(weight)

        victim = random.choices(targets, weights=weights, k=1)[0]
        return {
            "action": "wolf_vote",
            "target": victim.name,
            "reasoning": f"{self.personality.name} pense que {victim.name} est une menace."
        }

    def _seer_action(self) -> dict:
        """Choix de la cible pour la voyante"""
        # Ne pas vérifier les joueurs déjà révélés ou soi-même
        targets = [p for p in self.game_state.get_alive_players()
                   if p.name != self.player.name]

        # Préférer les joueurs suspects
        weights = []
        for target in targets:
            weight = 1.0 + self.personality.suspicion
            if target.name in self.suspicions:
                weight += self.suspicions[target.name]
            weights.append(weight)

        target = random.choices(targets, weights=weights, k=1)[0]
        return {
            "action": "seer_check",
            "target": target.name,
            "reasoning": f"{self.personality.name} veut vérifier {target.name}."
        }

    def _witch_action(self) -> dict:
        """Décisions de la sorcière"""
        actions = {"action": "witch_choice", "save": False, "kill": None}

        # Décider de sauver
        if self.game_state.witch_potions.has_life_potion:
            victim = self.game_state.night_actions.wolf_victim
            if victim:
                # Sauver si la victime n'est pas suspecte
                save_chance = 0.7 - self.suspicions.get(victim, 0)
                if random.random() < save_chance:
                    actions["save"] = True
                    actions["save_reasoning"] = f"Sauve {victim}"

        # Décider de tuer
        if self.game_state.witch_potions.has_death_potion and not actions["save"]:
            # Tuer si très suspect de quelqu'un
            suspects = [(name, level) for name, level in self.suspicions.items()
                        if level > 0.7]
            if suspects and random.random() < self.personality.aggression:
                target = max(suspects, key=lambda x: x[1])[0]
                actions["kill"] = target
                actions["kill_reasoning"] = f"Élimine {target} par suspicion"

        return actions

    def generate_discussion(self, context: list[dict]) -> str:
        """Génère une contribution à la discussion de jour"""
        is_wolf = self.player.role == Role.LOUP_GAROU

        # Construire le message selon la personnalité
        messages = []

        if is_wolf:
            # Stratégie de loup: dévier les suspicions
            messages.extend(self._wolf_discussion_strategy())
        else:
            # Stratégie villageois: exprimer ses suspicions
            messages.extend(self._villager_discussion_strategy())

        # Ajouter du flavour selon la personnalité
        return self._format_message(messages)

    def _wolf_discussion_strategy(self) -> list[str]:
        """Stratégie de discussion pour un loup"""
        strategies = []

        if self.personality.deception > 0.6:
            # Loup manipulateur: accuser les autres
            non_wolves = [p for p in self.game_state.get_alive_players()
                          if p.role != Role.LOUP_GAROU and p.name != self.player.name]
            if non_wolves:
                target = random.choice(non_wolves)
                strategies.append(f"Je trouve {target.name} très silencieux...")
        else:
            # Loup discret: rester vague
            strategies.append("Je ne suis pas sûr, observons encore.")

        return strategies

    def _villager_discussion_strategy(self) -> list[str]:
        """Stratégie de discussion pour un villageois"""
        strategies = []

        if self.personality.suspicion > 0.6:
            # Exprimer ses doutes
            alive = self.game_state.get_alive_players()
            others = [p for p in alive if p.name != self.player.name]
            if others:
                suspect = random.choice(others)
                strategies.append(f"J'ai des doutes sur {suspect.name}.")

        if self.personality.aggression > 0.6:
            strategies.append("Il faut voter maintenant !")

        if not strategies:
            strategies.append("Je réfléchis encore...")

        return strategies

    def _format_message(self, messages: list[str]) -> str:
        """Formate le message selon l'éloquence"""
        base = " ".join(messages)

        # Ajouter des éléments de personnalité
        traits_flavor = {
            "analytique": "D'un point de vue logique, ",
            "impulsif": "Je le sens, ",
            "charmante": "Mes chers amis, ",
            "sympathique": "Bon, ",
            "rationnelle": "Les faits montrent que ",
            "provocateur": "Eh bien, ",
            "discrète": "...",
            "diplomate": "Si je puis me permettre, ",
        }

        for trait in self.personality.traits:
            if trait in traits_flavor and random.random() < 0.3:
                base = traits_flavor[trait] + base.lower()
                break

        return base

    def generate_vote(self) -> dict:
        """Génère le vote du jour"""
        candidates = [p for p in self.game_state.get_alive_players()
                      if p.name != self.player.name]

        if not candidates:
            return {"vote": None, "reasoning": "Personne à voter"}

        is_wolf = self.player.role == Role.LOUP_GAROU

        if is_wolf:
            # Voter contre un non-loup
            non_wolves = [p for p in candidates if p.role != Role.LOUP_GAROU]
            if non_wolves:
                # Préférer les rôles spéciaux
                specials = [p for p in non_wolves if p.role in [Role.VOYANTE, Role.SORCIERE]]
                pool = specials if specials else non_wolves
                target = random.choice(pool)
            else:
                target = random.choice(candidates)
        else:
            # Voter selon les suspicions
            weights = []
            for c in candidates:
                weight = 0.5 + self.suspicions.get(c.name, 0.5)
                weights.append(weight)

            target = random.choices(candidates, weights=weights, k=1)[0]

        return {
            "vote": target.name,
            "reasoning": f"{self.personality.name} vote contre {target.name}"
        }

    def update_suspicions(self, event: dict):
        """Met à jour les suspicions basées sur un événement"""
        event_type = event.get("type")

        if event_type == "death":
            victim = event.get("victim")
            if victim in self.suspicions:
                del self.suspicions[victim]

        elif event_type == "accusation":
            accuser = event.get("accuser")
            target = event.get("target")
            # Les accusations peuvent sembler suspectes
            if random.random() < self.personality.suspicion:
                self.suspicions[accuser] = self.suspicions.get(accuser, 0.5) + 0.1

        elif event_type == "defense":
            defender = event.get("defender")
            defended = event.get("defended")
            # Défendre quelqu'un peut créer une association
            if random.random() < self.personality.suspicion:
                if defended in self.suspicions:
                    self.suspicions[defender] = self.suspicions.get(defender, 0.5) + 0.05


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
