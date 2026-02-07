"""
API FastAPI pour le jeu du Loup-Garou
Avec agents IA Anthropic Claude
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from .game_engine import engine
from .models import Role
from .ai_players import set_anthropic_api_key

app = FastAPI(
    title="Loup-Garou Game API",
    description="API pour jouer au Loup-Garou avec des agents IA Anthropic Claude",
    version="2.0.0"
)

# CORS pour permettre les appels depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Modèles Pydantic ---

class SetApiKeyRequest(BaseModel):
    api_key: str = Field(..., description="Clé API Anthropic")


class CreateGameRequest(BaseModel):
    player_name: str = Field(..., description="Nom du joueur humain")
    num_players: int = Field(default=6, ge=4, le=10, description="Nombre total de joueurs")
    num_wolves: int = Field(default=2, ge=1, le=3, description="Nombre de loups-garous")
    include_seer: bool = Field(default=True, description="Inclure la Voyante")
    include_witch: bool = Field(default=True, description="Inclure la Sorcière")


class PlayerActionRequest(BaseModel):
    action: str = Field(..., description="Type d'action")
    target: Optional[str] = Field(default=None, description="Cible de l'action")
    save: Optional[bool] = Field(default=False, description="Sauver la victime (Sorcière)")
    kill: Optional[str] = Field(default=None, description="Tuer un joueur (Sorcière)")


# --- Endpoints ---

@app.get("/")
async def root():
    return {"message": "Bienvenue dans l'API Loup-Garou", "version": "2.0.0"}


@app.post("/api/v1/config/anthropic")
async def set_api_key(request: SetApiKeyRequest):
    """Configure la clé API Anthropic"""
    try:
        set_anthropic_api_key(request.api_key)
        return {"success": True, "message": "Clé API Anthropic configurée"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/games")
async def create_game(request: CreateGameRequest):
    """Crée une nouvelle partie de Loup-Garou"""
    game = engine.create_game(
        human_name=request.player_name,
        num_players=request.num_players,
        num_wolves=request.num_wolves,
        include_seer=request.include_seer,
        include_witch=request.include_witch
    )

    human_player = next(p for p in game.players if p.is_human)

    response = {
        "game_id": game.game_id,
        "your_role": human_player.role.display_name,
        "your_faction": human_player.role.faction.value,
        "players": [
            {
                "name": p.name,
                "is_human": p.is_human,
                "personality": p.personality
            }
            for p in game.players
        ],
        "message": _generate_intro_message(human_player.role)
    }

    # Si le joueur est loup, révéler les alliés
    if human_player.role == Role.LOUP_GAROU:
        other_wolves = [p.name for p in game.get_wolves() if p.name != human_player.name]
        response["fellow_wolves"] = other_wolves

    return response


@app.get("/api/v1/games/{game_id}")
async def get_game_state(game_id: str):
    """Récupère l'état actuel de la partie (aligné avec le MCP)"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Partie non trouvée")

    human_player = next((p for p in game.players if p.is_human), None)

    # Si c'est la sorcière humaine pendant la nuit, pré-exécuter voyante et loups IA
    # pour qu'elle puisse voir la victime des loups
    if (human_player and human_player.role == Role.SORCIERE
            and game.phase.value == "nuit" and human_player.is_alive):
        await engine.prepare_night_for_witch(game_id)

    # Construire la réponse comme le MCP
    state = {
        "game_id": game.game_id,
        "phase": game.phase.value,
        "day_number": game.day_number,
        "status": game.status.value,
        "your_role": human_player.role.display_name if human_player else None,
        "you_are_alive": human_player.is_alive if human_player else False,
        "alive_players": [
            {"name": p.name, "is_you": p.is_human, "is_alive": p.is_alive}
            for p in game.get_alive_players()
        ],
        "dead_players": [
            {"name": p.name, "role": p.role.display_name}
            for p in game.players if not p.is_alive
        ],
        "players": [
            {
                "name": p.name,
                "is_alive": p.is_alive,
                "is_human": p.is_human,
                "role": p.role.display_name if not p.is_alive or (human_player and p.name == human_player.name) else None,
                "personality": p.personality
            }
            for p in game.players
        ],
        "alive_count": len(game.get_alive_players()),
        "pending_action": game.pending_action
    }

    # Infos spécifiques pour la sorcière
    if human_player and human_player.role == Role.SORCIERE:
        state["potions"] = {
            "life": game.witch_potions.has_life_potion,
            "death": game.witch_potions.has_death_potion
        }
        # Révéler la victime des loups pendant la nuit
        if game.phase.value == "nuit" and game.night_actions.wolf_victim:
            state["wolf_victim"] = game.night_actions.wolf_victim

    # Si le joueur est loup, révéler les alliés
    if human_player and human_player.role == Role.LOUP_GAROU:
        state["fellow_wolves"] = [
            p.name for p in game.get_wolves() if p.name != human_player.name
        ]

    return state


@app.post("/api/v1/games/{game_id}/actions")
async def process_action(game_id: str, request: PlayerActionRequest):
    """Traite une action du joueur humain"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Partie non trouvée")

    action = {
        "action": request.action,
        "target": request.target,
        "save": request.save,
        "kill": request.kill
    }

    # Utiliser la version async
    result = await engine.process_human_action_async(game_id, action)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.get("/api/v1/games/{game_id}/discussions")
async def get_discussions(game_id: str):
    """Récupère les discussions IA pour la phase de jour (comme le MCP)"""
    game = engine.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Partie non trouvée")

    if game.phase.value != "jour":
        return {"discussions": [], "message": "Les discussions ont lieu pendant le jour"}

    discussions = await engine.generate_ai_discussion_async(game_id)
    return {"discussions": discussions}


@app.get("/api/v1/games/{game_id}/summary")
async def get_game_summary(game_id: str, player_name: str):
    """Récupère un résumé du jeu pour un joueur"""
    result = engine.get_game_summary(game_id, player_name)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


def _generate_intro_message(role: Role) -> str:
    """Génère le message d'introduction selon le rôle"""
    messages = {
        Role.VILLAGEOIS: (
            "Vous êtes un simple Villageois. Vous n'avez pas de pouvoir spécial, "
            "mais votre vote est crucial pour démasquer les loups. "
            "Observez attentivement les comportements suspects !"
        ),
        Role.LOUP_GAROU: (
            "Vous êtes un Loup-Garou ! Chaque nuit, vous choisirez une victime "
            "avec vos complices. Le jour, fondez-vous parmi les villageois "
            "et détournez les soupçons. La survie de la meute dépend de vous."
        ),
        Role.VOYANTE: (
            "Vous êtes la Voyante. Chaque nuit, vous pouvez découvrir "
            "le véritable rôle d'un joueur. Utilisez ce pouvoir avec sagesse "
            "pour guider le village vers la victoire."
        ),
        Role.SORCIERE: (
            "Vous êtes la Sorcière. Vous possédez deux potions : "
            "une de vie pour sauver la victime des loups, "
            "une de mort pour éliminer un suspect. "
            "Chaque potion ne peut être utilisée qu'une seule fois."
        ),
    }
    return messages.get(role, "Bienvenue dans la partie !")


# Pour exécuter avec uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
