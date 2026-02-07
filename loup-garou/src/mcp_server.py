"""
Serveur MCP pour le jeu du Loup-Garou
Compatible avec Claude et Alpic
"""
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .game_engine import engine
from .models import Role, Phase, GameStatus

# Créer le serveur MCP
server = Server("loup-garou")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Liste tous les outils disponibles pour le jeu"""
    return [
        Tool(
            name="create_game",
            description="Crée une nouvelle partie de Loup-Garou. Retourne l'ID de partie et le rôle assigné au joueur.",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "Nom du joueur humain"
                    },
                    "num_players": {
                        "type": "integer",
                        "description": "Nombre total de joueurs (4-8)",
                        "default": 6,
                        "minimum": 4,
                        "maximum": 8
                    },
                    "num_wolves": {
                        "type": "integer",
                        "description": "Nombre de loups-garous (1-3)",
                        "default": 2,
                        "minimum": 1,
                        "maximum": 3
                    }
                },
                "required": ["player_name"]
            }
        ),
        Tool(
            name="get_game_state",
            description="Récupère l'état actuel de la partie (phase, joueurs vivants, action attendue)",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "Identifiant de la partie"
                    }
                },
                "required": ["game_id"]
            }
        ),
        Tool(
            name="wolf_attack",
            description="Action nocturne des Loups-Garous : choisir une victime à dévorer",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "Identifiant de la partie"
                    },
                    "target": {
                        "type": "string",
                        "description": "Nom du joueur à attaquer"
                    }
                },
                "required": ["game_id", "target"]
            }
        ),
        Tool(
            name="seer_observe",
            description="Action nocturne de la Voyante : observer le rôle d'un joueur",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "Identifiant de la partie"
                    },
                    "target": {
                        "type": "string",
                        "description": "Nom du joueur à observer"
                    }
                },
                "required": ["game_id", "target"]
            }
        ),
        Tool(
            name="witch_action",
            description="Action nocturne de la Sorcière : utiliser ses potions (vie pour sauver la victime, mort pour tuer)",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "Identifiant de la partie"
                    },
                    "use_life_potion": {
                        "type": "boolean",
                        "description": "Utiliser la potion de vie pour sauver la victime des loups",
                        "default": False
                    },
                    "kill_target": {
                        "type": "string",
                        "description": "Nom du joueur à empoisonner (optionnel)"
                    }
                },
                "required": ["game_id"]
            }
        ),
        Tool(
            name="skip_night",
            description="Pour les Villageois sans pouvoir : passer la nuit",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "Identifiant de la partie"
                    }
                },
                "required": ["game_id"]
            }
        ),
        Tool(
            name="get_discussions",
            description="Obtenir les discussions des joueurs IA pendant la phase de jour",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "Identifiant de la partie"
                    }
                },
                "required": ["game_id"]
            }
        ),
        Tool(
            name="vote",
            description="Voter pour éliminer un joueur pendant la phase de jour",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "string",
                        "description": "Identifiant de la partie"
                    },
                    "target": {
                        "type": "string",
                        "description": "Nom du joueur contre qui voter"
                    }
                },
                "required": ["game_id", "target"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Exécute un outil du jeu"""

    if name == "create_game":
        return await handle_create_game(arguments)
    elif name == "get_game_state":
        return await handle_get_game_state(arguments)
    elif name == "wolf_attack":
        return await handle_wolf_attack(arguments)
    elif name == "seer_observe":
        return await handle_seer_observe(arguments)
    elif name == "witch_action":
        return await handle_witch_action(arguments)
    elif name == "skip_night":
        return await handle_skip_night(arguments)
    elif name == "get_discussions":
        return await handle_get_discussions(arguments)
    elif name == "vote":
        return await handle_vote(arguments)
    else:
        return [TextContent(type="text", text=f"Outil inconnu: {name}")]


async def handle_create_game(args: dict) -> list[TextContent]:
    """Crée une nouvelle partie"""
    player_name = args.get("player_name", "Joueur")
    num_players = args.get("num_players", 6)
    num_wolves = args.get("num_wolves", 2)

    game = engine.create_game(
        human_name=player_name,
        num_players=num_players,
        num_wolves=num_wolves,
        include_seer=True,
        include_witch=True
    )

    human = next(p for p in game.players if p.is_human)

    response = {
        "game_id": game.game_id,
        "your_role": human.role.display_name,
        "your_faction": "Loups-Garous" if human.role == Role.LOUP_GAROU else "Village",
        "players": [
            {"name": p.name, "personality": p.personality}
            for p in game.players if not p.is_human
        ],
        "phase": game.phase.value,
        "message": _get_role_intro(human.role)
    }

    if human.role == Role.LOUP_GAROU:
        response["fellow_wolves"] = [
            p.name for p in game.get_wolves() if p.name != human.name
        ]

    return [TextContent(type="text", text=json.dumps(response, ensure_ascii=False, indent=2))]


async def handle_get_game_state(args: dict) -> list[TextContent]:
    """Récupère l'état du jeu"""
    game_id = args.get("game_id")
    game = engine.get_game(game_id)

    if not game:
        return [TextContent(type="text", text=json.dumps({"error": "Partie non trouvée"}))]

    human = next((p for p in game.players if p.is_human), None)

    state = {
        "game_id": game.game_id,
        "phase": game.phase.value,
        "day_number": game.day_number,
        "status": game.status.value,
        "your_role": human.role.display_name if human else None,
        "you_are_alive": human.is_alive if human else False,
        "alive_players": [
            {"name": p.name, "is_you": p.is_human}
            for p in game.get_alive_players()
        ],
        "dead_players": [
            {"name": p.name, "role": p.role.display_name}
            for p in game.players if not p.is_alive
        ],
        "pending_action": game.pending_action
    }

    if human and human.role == Role.SORCIERE:
        state["potions"] = {
            "life": game.witch_potions.has_life_potion,
            "death": game.witch_potions.has_death_potion
        }

    return [TextContent(type="text", text=json.dumps(state, ensure_ascii=False, indent=2))]


async def handle_wolf_attack(args: dict) -> list[TextContent]:
    """Attaque des loups"""
    game_id = args.get("game_id")
    target = args.get("target")

    result = engine.process_human_action(game_id, {
        "action": "wolf_vote",
        "target": target
    })

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def handle_seer_observe(args: dict) -> list[TextContent]:
    """Observation de la voyante"""
    game_id = args.get("game_id")
    target = args.get("target")

    result = engine.process_human_action(game_id, {
        "action": "seer_check",
        "target": target
    })

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def handle_witch_action(args: dict) -> list[TextContent]:
    """Action de la sorcière"""
    game_id = args.get("game_id")
    use_life = args.get("use_life_potion", False)
    kill_target = args.get("kill_target")

    result = engine.process_human_action(game_id, {
        "action": "witch_choice",
        "save": use_life,
        "kill": kill_target
    })

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def handle_skip_night(args: dict) -> list[TextContent]:
    """Passer la nuit (villageois)"""
    game_id = args.get("game_id")

    result = engine.process_human_action(game_id, {
        "action": "wait_night"
    })

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def handle_get_discussions(args: dict) -> list[TextContent]:
    """Récupère les discussions IA"""
    game_id = args.get("game_id")

    discussions = engine.generate_ai_discussion(game_id)

    return [TextContent(type="text", text=json.dumps({
        "discussions": discussions
    }, ensure_ascii=False, indent=2))]


async def handle_vote(args: dict) -> list[TextContent]:
    """Vote du jour"""
    game_id = args.get("game_id")
    target = args.get("target")

    result = engine.process_human_action(game_id, {
        "action": "day_vote",
        "target": target
    })

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _get_role_intro(role: Role) -> str:
    """Message d'introduction selon le rôle"""
    intros = {
        Role.VILLAGEOIS: "Vous êtes un Villageois. Pas de pouvoir spécial, mais votre vote compte !",
        Role.LOUP_GAROU: "Vous êtes un Loup-Garou ! Dévorez les villageois la nuit, cachez-vous le jour.",
        Role.VOYANTE: "Vous êtes la Voyante. Chaque nuit, découvrez le rôle d'un joueur.",
        Role.SORCIERE: "Vous êtes la Sorcière. Vous avez une potion de vie et une potion de mort.",
    }
    return intros.get(role, "Bienvenue !")


async def main():
    """Point d'entrée du serveur MCP"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
